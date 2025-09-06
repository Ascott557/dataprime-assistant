#!/usr/bin/env python3
"""
🌐 API Gateway Service - Entry point for all requests
Handles routing, authentication, and request distribution to downstream services.
"""

import os
import json
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator



# Initialize tracer
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# Initialize Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

# Initialize shared telemetry configuration

# Initialize requests instrumentation immediately


# Service endpoints
QUERY_SERVICE_URL = "http://localhost:8011"
VALIDATION_SERVICE_URL = "http://localhost:8012"
QUEUE_SERVICE_URL = "http://localhost:8013"
PROCESSING_SERVICE_URL = "http://localhost:8014"
STORAGE_SERVICE_URL = "http://localhost:8015"

# Stats tracking
gateway_stats = {
    "requests_processed": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def propagate_trace_context(headers=None):
    """Inject current trace context into headers for downstream services."""
    if headers is None:
        headers = {}
    
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for the API Gateway."""
    with tracer.start_as_current_span("api_gateway.health_check") as span:
        span.set_attribute("service.name", "api_gateway")
        span.set_attribute("service.version", "1.0.0")
        
        # Check downstream services health
        services_health = {}
        
        try:
            # Add small delay to simulate processing
            time.sleep(0.005)  # 5ms
            
            services = {
                "query_service": f"{QUERY_SERVICE_URL}/health",
                "validation_service": f"{VALIDATION_SERVICE_URL}/health", 
                "queue_service": f"{QUEUE_SERVICE_URL}/health",
                "processing_service": f"{PROCESSING_SERVICE_URL}/health",
                "storage_service": f"{STORAGE_SERVICE_URL}/health"
            }
            
            headers = propagate_trace_context()
            
            for service_name, url in services.items():
                try:
                    response = requests.get(url, headers=headers, timeout=2)
                    services_health[service_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_time": response.elapsed.total_seconds()
                    }
                except Exception as e:
                    services_health[service_name] = {
                        "status": "unhealthy",
                        "error": str(e)
                    }
            
            span.set_attribute("downstream.services.count", len(services))
            span.set_attribute("downstream.services.healthy", 
                             len([s for s in services_health.values() if s.get("status") == "healthy"]))
            
            return jsonify({
                "status": "healthy",
                "service": "api_gateway",
                "version": "1.0.0",
                "uptime": str(datetime.now() - gateway_stats["start_time"]),
                "stats": gateway_stats,
                "downstream_services": services_health,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """Main endpoint for query generation - orchestrates the full pipeline."""
    # Extract incoming trace context from client
    propagator = TraceContextTextMapPropagator()
    incoming_context = propagator.extract(dict(request.headers))
    
    # Set the extracted context as current context
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("api_gateway.generate_query_pipeline") as span:
            span.set_attribute("service.name", "api_gateway")
            span.set_attribute("operation.name", "generate_query_pipeline")
            
            gateway_stats["requests_processed"] += 1
            
            # Get user input
            data = request.get_json()
            if not data or 'user_input' not in data:
                gateway_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing user_input"))
                return jsonify({"error": "Missing 'user_input' in request"}), 400
                
            user_input = data['user_input'].strip()
            if not user_input:
                gateway_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Empty user_input"))
                return jsonify({"error": "Empty user input"}), 400
            
            span.set_attribute("user.input.length", len(user_input))
            span.set_attribute("user.input.query", user_input[:100])  # First 100 chars
            
            # Add gateway processing delay
            time.sleep(0.008)  # 8ms
            
            # Step 1: Generate query via Query Service
            with tracer.start_as_current_span("api_gateway.call_query_service") as query_span:
                headers = propagate_trace_context()
                
                query_response = requests.post(
                    f"{QUERY_SERVICE_URL}/generate",
                    json={"user_input": user_input},
                    headers=headers,
                    timeout=30
                )
                
                if query_response.status_code != 200:
                    raise Exception(f"Query service error: {query_response.text}")
                
                query_result = query_response.json()
                query_span.set_attribute("query.generated", query_result.get("query", "")[:100])
                query_span.set_attribute("query.intent", query_result.get("intent", "unknown"))
            
            # Step 2: Validate query via Validation Service
            with tracer.start_as_current_span("api_gateway.call_validation_service") as validation_span:
                headers = propagate_trace_context()
                
                validation_response = requests.post(
                    f"{VALIDATION_SERVICE_URL}/validate",
                    json={"query": query_result.get("query", "")},
                    headers=headers,
                    timeout=10
                )
                
                if validation_response.status_code != 200:
                    raise Exception(f"Validation service error: {validation_response.text}")
                
                validation_result = validation_response.json()
                validation_span.set_attribute("validation.is_valid", validation_result.get("is_valid", False))
                validation_span.set_attribute("validation.score", validation_result.get("syntax_score", 0))
            
            # Step 3: Queue for background processing
            with tracer.start_as_current_span("api_gateway.enqueue_processing") as queue_span:
                headers = propagate_trace_context()
                
                processing_data = {
                    "user_input": user_input,
                    "generated_query": query_result.get("query", ""),
                    "validation_result": validation_result,
                    "request_id": span.get_span_context().span_id
                }
                
                queue_response = requests.post(
                    f"{QUEUE_SERVICE_URL}/enqueue",
                    json=processing_data,
                    headers=headers,
                    timeout=5
                )
                
                if queue_response.status_code != 200:
                    # Non-critical error - continue without background processing
                    queue_span.add_event("background_processing_failed", {
                        "error": queue_response.text
                    })
                else:
                    queue_span.set_attribute("queue.message_id", queue_response.json().get("message_id", ""))
            
            # Combine results
            final_result = {
                "success": True,
                "query": query_result.get("query", ""),
                "intent": query_result.get("intent", "unknown"),
                "intent_confidence": query_result.get("intent_confidence", 0.0),
                "keywords_found": query_result.get("keywords_found", []),
                "validation": validation_result,
                "demo_mode": query_result.get("demo_mode", "permissive"),
                "knowledge_base_used": query_result.get("knowledge_base_used", False),
                "processing_time_ms": int((time.time() * 1000) % 1000),
                "services_called": ["query_service", "validation_service", "queue_service"]
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.query_length", len(final_result["query"]))
            span.set_attribute("pipeline.services_count", 3)
            
            return jsonify(final_result)
            
            except Exception as e:
                gateway_stats["errors"] += 1
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                    "service": "api_gateway"
                }), 500
    
    finally:
        # Detach the context token
        if token:
            context.detach(token)

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback - routes to storage service."""
    with tracer.start_as_current_span("api_gateway.submit_feedback") as span:
        span.set_attribute("service.name", "api_gateway")
        span.set_attribute("operation.name", "submit_feedback")
        
        try:
            data = request.get_json()
            if not data:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing feedback data"))
                return jsonify({"error": "Missing feedback data"}), 400
            
            # Add small processing delay
            time.sleep(0.005)  # 5ms
            
            # Route to storage service
            headers = propagate_trace_context()
            
            storage_response = requests.post(
                f"{STORAGE_SERVICE_URL}/feedback",
                json=data,
                headers=headers,
                timeout=10
            )
            
            if storage_response.status_code != 200:
                raise Exception(f"Storage service error: {storage_response.text}")
            
            result = storage_response.json()
            span.set_attribute("feedback.rating", data.get("rating", 0))
            span.set_attribute("feedback.stored", True)
            
            return jsonify(result)
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "service": "api_gateway"
            }), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get aggregated stats from all services."""
    with tracer.start_as_current_span("api_gateway.get_stats") as span:
        span.set_attribute("service.name", "api_gateway")
        
        try:
            # Collect stats from all services
            headers = propagate_trace_context()
            all_stats = {"api_gateway": gateway_stats}
            
            services = {
                "query_service": f"{QUERY_SERVICE_URL}/stats",
                "validation_service": f"{VALIDATION_SERVICE_URL}/stats",
                "queue_service": f"{QUEUE_SERVICE_URL}/stats",
                "processing_service": f"{PROCESSING_SERVICE_URL}/stats",
                "storage_service": f"{STORAGE_SERVICE_URL}/stats"
            }
            
            for service_name, url in services.items():
                try:
                    response = requests.get(url, headers=headers, timeout=2)
                    if response.status_code == 200:
                        all_stats[service_name] = response.json()
                except Exception as e:
                    all_stats[service_name] = {"error": str(e)}
            
            span.set_attribute("stats.services_count", len(all_stats))
            
            return jsonify({
                "success": True,
                "stats": all_stats,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "service": "api_gateway"
            }), 500

if __name__ == '__main__':
    # Initialize instrumentation
    
    
    
    print("🌐 API Gateway starting on port 5000...")
    print(f"   Query Service: {QUERY_SERVICE_URL}")
    print(f"   Validation Service: {VALIDATION_SERVICE_URL}")
    print(f"   Queue Service: {QUEUE_SERVICE_URL}")
    print(f"   Processing Service: {PROCESSING_SERVICE_URL}")
    print(f"   Storage Service: {STORAGE_SERVICE_URL}")
    
    app.run(host='0.0.0.0', port=8010, debug=False)