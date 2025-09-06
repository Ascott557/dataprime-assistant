#!/usr/bin/env python3
"""
🧠 Query Service with Coralogix Telemetry
"""

import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def initialize_telemetry():
    """Initialize OpenTelemetry with Coralogix export."""
    try:
        print("🔧 Query Service: Initializing telemetry...")
        from llm_tracekit import setup_export_to_coralogix, OpenAIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        
        setup_export_to_coralogix(
            service_name="dataprime_distributed_system",
            application_name="ai-dataprime-enterprise", 
            subsystem_name="query-service",
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=os.getenv('CX_ENDPOINT', 'https://ingress.coralogix.com/api/v1/otel/v1/traces'),
            capture_content=True
        )
        OpenAIInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        print("✅ Query Service: Telemetry initialized")
        return True
    except Exception as e:
        print(f"⚠️  Query Service: Telemetry setup failed: {e}")
        return False

# Initialize telemetry
telemetry_enabled = initialize_telemetry()

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

# Initialize Flask instrumentation
if telemetry_enabled:
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        print("✅ Query Service: Flask instrumentation enabled")
    except Exception as e:
        print(f"⚠️  Query Service: Flask instrumentation failed: {e}")

def extract_trace_context():
    """Extract trace context from incoming request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/generate', methods=['POST'])
def generate_query():
    """Generate DataPrime query with telemetry."""
    # Extract incoming trace context
    incoming_context = extract_trace_context()
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("query_service.generate_query") as span:
            span.set_attribute("service.name", "query_service")
            
            data = request.get_json()
            user_input = data.get('user_input', '')
            
            span.set_attribute("user.input", user_input)
            span.set_attribute("operation.name", "generate_dataprime_query")
            
            # Simulate LLM processing time
            time.sleep(0.1)
            
            # Generate query based on input (simplified logic)
            if 'error' in user_input.lower():
                query = "source logs last 1h | filter $m.severity == 'Error'"
                intent = "error_analysis"
                confidence = 0.85
            elif 'performance' in user_input.lower():
                query = "source logs last 1h | filter $d.response_time > 1000"
                intent = "performance_analysis"
                confidence = 0.90
            else:
                query = "source logs last 1h | filter $m.severity in ['Warning', 'Error']"
                intent = "general_analysis"
                confidence = 0.75
            
            result = {
                "success": True,
                "query": query,
                "intent": intent,
                "intent_confidence": confidence,
                "service": "query_service",
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("query.generated", query)
            span.set_attribute("query.intent", intent)
            span.set_attribute("query.confidence", confidence)
            
            return jsonify(result)
            
    except Exception as e:
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        return jsonify({"success": False, "error": str(e)}), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "query_service",
        "telemetry_enabled": telemetry_enabled,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🧠 Query Service with Telemetry starting on port 8011...")
    print(f"   Telemetry enabled: {telemetry_enabled}")
    app.run(host='0.0.0.0', port=8011, debug=False)
