#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


"""
🌐 API Gateway - Simple Fixed Version (Working Telemetry)
Uses shared telemetry for consistent configuration across all services.
"""

import os
import sys
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized, get_telemetry_status

# Initialize telemetry for this service
telemetry_enabled = ensure_telemetry_initialized()

# Simple tracer - relies on shared telemetry setup
tracer = trace.get_tracer(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

# Service endpoints
QUERY_SERVICE_URL = "http://localhost:8011"
VALIDATION_SERVICE_URL = "http://localhost:8012"
QUEUE_WORKER_SERVICE_URL = "http://localhost:8017"
STORAGE_SERVICE_URL = "http://localhost:8015"  # For database operations

# Gateway statistics with demo mode support
gateway_stats = {
    "requests": 0,
    "errors": 0,
    "start_time": datetime.now(),
    "demo_mode": "permissive",  # Default to permissive mode (matches Query Service)
    "slow_spans_created": 0,
    "slow_db_operations": 0,
    "slow_mode_enabled": False  # Flag for slow database demo through normal journey
}

def validate_w3c_trace_id(trace_id_str):
    """Validate W3C trace ID format with comprehensive checks."""
    if not trace_id_str:
        return False
        
    # Must be exactly 32 hex characters
    if len(trace_id_str) != 32:
        print(f"❌ Trace ID wrong length: {len(trace_id_str)} (expected 32)")
        return False
    
    # Must be valid hex
    try:
        int(trace_id_str, 16)
    except ValueError:
        print(f"❌ Trace ID not valid hex: {trace_id_str}")
        return False
    
    # Must not be all zeros (invalid trace ID)
    if trace_id_str == '0' * 32:
        print(f"❌ Trace ID all zeros (invalid)")
        return False
        
    return True

def validate_w3c_span_id(span_id_str):
    """Validate W3C span ID format with comprehensive checks."""
    if not span_id_str:
        return False
        
    # Must be exactly 16 hex characters
    if len(span_id_str) != 16:
        print(f"❌ Span ID wrong length: {len(span_id_str)} (expected 16)")
        return False
    
    # Must be valid hex
    try:
        int(span_id_str, 16)
    except ValueError:
        print(f"❌ Span ID not valid hex: {span_id_str}")
        return False
    
    # Must not be all zeros (invalid span ID)
    if span_id_str == '0' * 16:
        print(f"❌ Span ID all zeros (invalid)")
        return False
        
    return True

def propagate_trace_context(headers=None):
    """Propagate the current trace context to downstream services."""
    if headers is None:
        headers = {}
    
    # Try standard propagation first
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    
    # If standard propagation didn't work, create manual headers
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        span_context = current_span.get_span_context()
        trace_id = format(span_context.trace_id, '032x')
        span_id = format(span_context.span_id, '016x')
        
        # Create W3C traceparent header manually
        headers['traceparent'] = f"00-{trace_id}-{span_id}-01"
        print(f"🔗 Manual propagation - trace_id: {trace_id}, span_id: {span_id}")
    else:
        print("⚠️ No current span found for propagation")
    
    print(f"🚀 Propagating headers: {headers}")
    return headers

def extract_and_attach_trace_context():
    """Extract trace context and determine if we should create root or child span."""
    propagator = TraceContextTextMapPropagator()
    headers = dict(request.headers)
    
    print(f"🔍 ALL incoming headers: {headers}")
    
    # Debug trace context extraction - check all possible header names
    traceparent_found = False
    for key in headers.keys():
        if key.lower() == 'traceparent':
            print(f"✅ Found traceparent header: {key} = {headers[key]}")
            traceparent_found = True
        if key.lower() == 'tracestate':
            print(f"✅ Found tracestate header: {key} = {headers[key]}")
    
    if not traceparent_found:
        print("❌ NO traceparent header found in request!")
        print("📋 Available headers:", list(headers.keys()))
    
    # Extract trace context from headers
    incoming_context = propagator.extract(headers)
    print(f"🔍 Extracted context: {incoming_context}")
    
    # COMPREHENSIVE W3C TRACE CONTEXT PARSING with validation
    manual_trace_id = None
    manual_span_id = None
    if traceparent_found:
        for key, value in headers.items():
            if key.lower() == 'traceparent':
                # Parse W3C traceparent: 00-{trace_id}-{span_id}-{flags}
                parts = value.split('-')
                
                if len(parts) != 4:
                    print(f"❌ Invalid traceparent format: expected 4 parts, got {len(parts)}")
                    continue
                
                version, trace_id_str, span_id_str, flags = parts
                
                # Validate version
                if version != '00':
                    print(f"❌ Unsupported traceparent version: {version}")
                    continue
                
                # Validate trace ID format with comprehensive checks
                if not validate_w3c_trace_id(trace_id_str):
                    print(f"❌ Invalid trace ID format: {trace_id_str}")
                    continue
                
                # Validate span ID format with comprehensive checks
                if not validate_w3c_span_id(span_id_str):
                    print(f"❌ Invalid span ID format: {span_id_str}")
                    continue
                
                manual_trace_id = trace_id_str
                manual_span_id = span_id_str
                print(f"✅ Valid W3C format - trace: {trace_id_str}, span: {span_id_str}")
                break
    
    # Check if we have valid trace context (either from propagator or manual)
    if incoming_context:
        token = context.attach(incoming_context)
        # Get the trace ID from context to verify it worked
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            trace_id = format(current_span.get_span_context().trace_id, '032x')
            print(f"✅ Joined existing trace via propagator: {trace_id}")
            return token, False  # False = not root
        else:
            print("⚠️ Propagator trace context extraction failed")
    
    # If propagator failed but we have validated manual trace info, create context manually
    if manual_trace_id:
        from opentelemetry.trace import SpanContext, TraceFlags
        
        try:
            # Convert to integers (we know they're valid hex from validation)
            trace_id_int = int(manual_trace_id, 16)
            span_id_int = int(manual_span_id, 16)
            
            # Parse flags from traceparent
            try:
                flags_int = int(flags, 16) if 'flags' in locals() else 0x01
                trace_flags = TraceFlags(flags_int)
            except (ValueError, NameError):
                trace_flags = TraceFlags(0x01)  # Default to sampled
            
            # Create parent span context
            parent_span_context = SpanContext(
                trace_id=trace_id_int,
                span_id=span_id_int,
                is_remote=True,
                trace_flags=trace_flags
            )
            
            # Create context with parent span
            from opentelemetry.trace import set_span_in_context, NonRecordingSpan
            parent_span = NonRecordingSpan(parent_span_context)
            manual_context = set_span_in_context(parent_span)
            
            token = context.attach(manual_context)
            print(f"✅ Successfully joined trace via manual parsing: {manual_trace_id}")
            return token, False  # False = not root
            
        except Exception as e:
            print(f"❌ Manual trace context creation failed: {e}")
            print(f"   Trace ID: {manual_trace_id}")
            print(f"   Span ID: {manual_span_id}")
            print(f"   This should not happen with valid W3C format!")
            import traceback
            print(f"   Full error: {traceback.format_exc()}")
            return None, True
    
    print("📝 No valid trace context found, creating new root")
    return None, True

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Extract incoming trace context
    propagator = TraceContextTextMapPropagator()
    headers = dict(request.headers)
    incoming_context = propagator.extract(headers)
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("api_gateway.health_check") as span:
            span.set_attribute("service.component", "api_gateway")
            span.set_attribute("operation.name", "health_check")
            
            result = {
                "status": "healthy",
                "service": "api_gateway",
                "telemetry_initialized": telemetry_enabled,
                "version": "1.0.0",
                "timestamp": datetime.now().isoformat()
            }
            
            return jsonify(result)
    finally:
        if token:
            context.detach(token)

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """Generate query - manual trace control."""
    print(f"\n🔍 GENERATE QUERY - TRACE CONTEXT DEBUG")
    token, is_root = extract_and_attach_trace_context()
    
    if is_root:
        print(f"⚠️ WARNING: Creating ROOT span - trace propagation may have failed!")
    else:
        print(f"✅ SUCCESS: Creating CHILD span - trace propagation worked!")
    
    try:
        gateway_stats["requests"] += 1
        
        # Choose span name and create explicit hierarchy
        if is_root:
            span_name = "user_session.journey"  # Root session span
            span_type = "user_journey_root"
            print("🌟 Creating ROOT span for user session")
        else:
            span_name = "api_gateway.generate_query"  # Child operation span
            span_type = "child_operation"
            print("🔗 Creating CHILD span joining existing trace")
        
        with tracer.start_as_current_span(span_name) as span:
            try:
                span.set_attribute("trace.type", span_type)
                if is_root:
                    span.set_attribute("session.initiated", True)
                    span.set_attribute("session.first_operation", "generate_query")
                else:
                    span.set_attribute("operation.parent", "user_session")
                
                span.set_attribute("service.component", "api_gateway")
                span.set_attribute("operation.name", "generate_query")
                span.set_attribute("http.method", request.method)
                span.set_attribute("http.url", request.url)
                
                # Get user input
                data = request.get_json()
                if not data or 'user_input' not in data:
                    gateway_stats["errors"] += 1
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing user_input"))
                    return jsonify({"success": False, "error": "Missing user_input"}), 400
                
                user_input = data['user_input']
                slow_mode = data.get('slow_mode', False) or gateway_stats.get("slow_mode_enabled", False)
                
                span.set_attribute("user.input", user_input)
                span.set_attribute("slow_mode.enabled", slow_mode)
                
                # Reset slow mode flag after use
                if gateway_stats.get("slow_mode_enabled", False):
                    gateway_stats["slow_mode_enabled"] = False
                    print("🐌 Using slow database mode for this query")
                
                # Call Query Service
                with tracer.start_as_current_span("api_gateway.call_query_service") as query_span:
                    query_span.set_attribute("downstream.service", "query_service")
                    
                    headers = propagate_trace_context()
                    
                    query_response = requests.post(
                        f"{QUERY_SERVICE_URL}/generate",
                        json={"user_input": user_input},
                        headers=headers,
                        timeout=15
                    )
                    
                    if query_response.status_code != 200:
                        raise Exception(f"Query service error: {query_response.text}")
                    
                    query_result = query_response.json()
                    query_span.set_attribute("query.generated", query_result.get("query", ""))
                    query_span.set_attribute("query.intent", query_result.get("intent", ""))
                
                # Call Validation Service
                with tracer.start_as_current_span("api_gateway.call_validation_service") as validation_span:
                    validation_span.set_attribute("downstream.service", "validation_service")
                    
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
                
                # Add AI Center evaluation attributes for Coralogix AI Center
                span.set_attribute("ai.user_query", user_input)
                span.set_attribute("ai.generated_response", query_result.get("query", ""))
                span.set_attribute("ai.intent_classification", query_result.get("intent", "unknown"))
                span.set_attribute("ai.confidence_score", query_result.get("intent_confidence", 0.0))
                span.set_attribute("ai.validation_score", validation_result.get("syntax_score", 0.0))
                span.set_attribute("ai.validation_passed", validation_result.get("is_valid", False))
                
                # Domain-specific context for AI Center evaluations
                span.set_attribute("business.domain", "observability")
                span.set_attribute("business.use_case", "dataprime_query_generation")
                span.set_attribute("ai.model_type", "llm")
                span.set_attribute("ai.task_type", "query_translation")
                
                # Demo mode context
                current_mode = gateway_stats.get("demo_mode", "permissive")
                span.set_attribute("demo.mode", current_mode)
                span.set_attribute("demo.distributed_system", True)
                
                # Step 3: Trigger background processing via Queue Worker (Enterprise Pattern)
                background_job = None
                with tracer.start_as_current_span("api_gateway.trigger_background_processing") as queue_span:
                    queue_span.set_attribute("downstream.service", "queue_worker_service")
                    
                    headers = propagate_trace_context()
                    
                    # This creates the enterprise pattern: API → Queue → Another API → Database
                    try:
                        queue_response = requests.post(
                            f"{QUEUE_WORKER_SERVICE_URL}/process-job",
                            json={
                                "job_id": f"job_{int(time.time())}",
                                "query_data": {
                                    "query": query_result.get("query", ""),
                                    "intent": query_result.get("intent", "unknown")
                                }
                            },
                            headers=headers,
                            timeout=15
                        )
                        
                        if queue_response.status_code == 200:
                            background_job = queue_response.json()
                            queue_span.set_attribute("job.id", background_job.get("job_id"))
                            queue_span.set_attribute("job.status", background_job.get("processing_status"))
                        else:
                            queue_span.set_attribute("job.error", "Failed to start background job")
                            
                    except Exception as e:
                        queue_span.record_exception(e)
                        # Don't fail the main request if background processing fails
                        background_job = {"error": str(e), "status": "failed"}
                
                # Step 4: Slow database demo if enabled (simulates database bottleneck)
                slow_db_result = None
                if slow_mode:
                    with tracer.start_as_current_span("api_gateway.slow_database_demo") as slow_span:
                        slow_span.set_attribute("downstream.service", "storage_service")
                        slow_span.set_attribute("demo.type", "slow_database_bottleneck")
                        
                        headers = propagate_trace_context()
                        
                        try:
                            slow_db_response = requests.post(
                                f"{STORAGE_SERVICE_URL}/demo/slow-db",
                                json={"simulate_slow": True, "demo_context": "normal_user_journey"},
                                headers=headers,
                                timeout=30
                            )
                            
                            if slow_db_response.status_code == 200:
                                slow_db_result = slow_db_response.json()
                                slow_span.set_attribute("slow_db.success", True)
                                slow_span.set_attribute("slow_db.duration", slow_db_result.get("performance_analysis", {}).get("total_duration", "unknown"))
                                print(f"🐌 Slow database demo completed in normal user journey")
                            else:
                                slow_span.set_attribute("slow_db.error", "Failed to execute slow database demo")
                                
                        except Exception as e:
                            slow_span.record_exception(e)
                            slow_db_result = {"error": str(e), "status": "failed"}
                            print(f"⚠️ Slow database demo failed: {e}")
                
                # Combine results with enterprise complexity
                services_called = ["query_service", "validation_service", "queue_worker_service"]
                if slow_mode and slow_db_result:
                    services_called.append("storage_service")
                
                final_result = {
                    "success": True,
                    "query": query_result.get("query", ""),
                    "intent": query_result.get("intent", "unknown"),
                    "intent_confidence": query_result.get("intent_confidence", 0.0),
                    "validation": validation_result,
                    "background_processing": background_job,
                    "demo_mode": current_mode,
                    "slow_mode_enabled": slow_mode,
                    "services_called": services_called,
                    "enterprise_pattern": "API → Queue → External APIs → Database",
                    # Add trace debugging info
                    "trace_type": "root" if is_root else "child",
                    "trace_id": format(span.get_span_context().trace_id, '032x'),
                    "span_id": format(span.get_span_context().span_id, '016x'),  # For frontend chaining
                    "is_root_span": is_root
                }
                
                # Add slow database results if available
                if slow_mode and slow_db_result:
                    final_result["slow_database_demo"] = slow_db_result
                
                span.set_attribute("response.success", True)
                span.set_attribute("response.query_length", len(final_result["query"]))
                span.set_attribute("trace.is_root", is_root)
                
                return jsonify(final_result)
                
            except Exception as e:
                gateway_stats["errors"] += 1
                try:
                    span.record_exception(e)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                except Exception:
                    # Span already ended, ignore
                    pass
                raise  # Re-raise to be caught by outer exception handler
            
    except Exception as e:
        # Exception already handled within span context
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback - should ALWAYS be child span."""
    print(f"\n🔍 SUBMIT FEEDBACK - TRACE CONTEXT DEBUG")
    token, is_root = extract_and_attach_trace_context()
    
    if is_root:
        print(f"⚠️ WARNING: Feedback creating ROOT span - trace propagation FAILED!")
    else:
        print(f"✅ SUCCESS: Feedback creating CHILD span - trace propagation worked!")
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        # Feedback should NEVER be root - always child of user journey
        if is_root:
            print("⚠️ WARNING: Feedback creating root span - trace propagation failed!")
        else:
            print("✅ Feedback correctly joined existing trace")
        
        with tracer.start_as_current_span("api_gateway.submit_feedback") as span:
            span.set_attribute("service.component", "api_gateway")
            span.set_attribute("operation.name", "submit_feedback")
            
            feedback_data = {
                "user_input": data.get("user_input", ""),
                "generated_query": data.get("generated_query", ""),
                "rating": data.get("rating"),
                "comment": data.get("comment", ""),
                "metadata": {
                    "source": "api_gateway",
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            span.set_attribute("feedback.rating", feedback_data["rating"])
            span.set_attribute("feedback.has_comment", bool(feedback_data["comment"]))
            
            # NEW: Call Storage Service for Database Operations
            with tracer.start_as_current_span("api_gateway.call_storage_service") as storage_span:
                storage_span.set_attribute("downstream.service", "storage_service")
                
                # Propagate trace context to storage service
                headers = propagate_trace_context()
                
                try:
                    storage_response = requests.post(
                        f"{STORAGE_SERVICE_URL}/feedback",
                        json=feedback_data,
                        headers=headers,
                        timeout=10
                    )
                    
                    if storage_response.status_code == 200:
                        storage_result = storage_response.json()
                        storage_span.set_attribute("storage.success", True)
                        storage_span.set_attribute("storage.feedback_id", storage_result.get("feedback_id"))
                        
                        print(f"✅ Feedback stored in database: {storage_result.get('feedback_id')}")
                        
                        # Return successful result with database confirmation
                        result = {
                            "success": True,
                            "message": "Feedback submitted and stored successfully",
                            "feedback_id": storage_result.get("feedback_id"),
                            "stored_at": storage_result.get("stored_at"),
                            "timestamp": feedback_data["metadata"]["timestamp"],
                            "trace_type": "root" if is_root else "child",
                            "trace_id": format(span.get_span_context().trace_id, '032x'),
                            "span_id": format(span.get_span_context().span_id, '016x'),
                            "should_be_child": True,
                            "is_root_span": is_root
                        }
                        
                        return jsonify(result)
                    else:
                        storage_span.set_attribute("storage.success", False)
                        storage_span.set_attribute("storage.error", storage_response.text)
                        
                        print(f"❌ Storage service failed: {storage_response.status_code}")
                        
                        # Return partial success (feedback received but not stored)
                        result = {
                            "success": True,  # API still succeeded
                            "message": "Feedback received but storage failed",
                            "storage_error": "Database unavailable",
                            "trace_type": "root" if is_root else "child",
                            "trace_id": format(span.get_span_context().trace_id, '032x'),
                            "span_id": format(span.get_span_context().span_id, '016x'),
                            "should_be_child": True,
                            "is_root_span": is_root
                        }
                        
                        return jsonify(result)
                        
                except requests.exceptions.RequestException as e:
                    storage_span.record_exception(e)
                    storage_span.set_attribute("storage.success", False)
                    storage_span.set_attribute("storage.error", str(e))
                    
                    print(f"❌ Storage service connection failed: {e}")
                    
                    # Return partial success (feedback received but not stored)
                    result = {
                        "success": True,  # API still succeeded
                        "message": "Feedback received but storage unavailable",
                        "storage_error": f"Connection failed: {str(e)}",
                        "trace_type": "root" if is_root else "child",
                        "trace_id": format(span.get_span_context().trace_id, '032x'),
                        "span_id": format(span.get_span_context().span_id, '016x'),
                        "should_be_child": True,
                        "is_root_span": is_root
                    }
                    
                    return jsonify(result)
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    try:
        with tracer.start_as_current_span("api_gateway.get_stats") as span:
            span.set_attribute("service.component", "api_gateway")
            
            stats = {
                "service": "api_gateway",
                "status": "healthy",
                "requests_processed": gateway_stats["requests"],
                "errors": gateway_stats["errors"],
                "uptime_seconds": int((datetime.now() - gateway_stats["start_time"]).total_seconds()),
                "telemetry_initialized": os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true',
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("stats.requests_processed", stats["requests_processed"])
            span.set_attribute("stats.errors", stats["errors"])
            
            return jsonify(stats)
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500

@app.route('/api/toggle-mode', methods=['POST'])
def toggle_demo_mode():
    """Toggle between enterprise and permissive demo modes."""
    try:
        with tracer.start_as_current_span("api_gateway.toggle_demo_mode") as span:
            span.set_attribute("service.component", "api_gateway")
            span.set_attribute("operation.name", "toggle_demo_mode")
            
            current_mode = gateway_stats.get("demo_mode", "permissive")
            new_mode = "smart" if current_mode == "permissive" else "permissive"
            gateway_stats["demo_mode"] = new_mode
            
            # Propagate to Query Service
            try:
                query_service_response = requests.post(
                    f"{QUERY_SERVICE_URL}/api/set-mode",
                    json={"mode": new_mode},
                    timeout=5
                )
                
                span.set_attribute("query_service.mode_update.success", query_service_response.status_code == 200)
                
                print(f"🔧 Mode propagated to Query Service: {new_mode}")
                
            except Exception as e:
                span.set_attribute("query_service.mode_update.error", str(e))
                print(f"⚠️ Failed to propagate mode to Query Service: {e}")
            
            span.set_attribute("demo.previous_mode", current_mode)
            span.set_attribute("demo.new_mode", new_mode)
            
            print(f"🎭 Demo mode switched: {current_mode} → {new_mode}")
            
            return jsonify({
                "success": True,
                "previous_mode": current_mode,
                "current_mode": new_mode,
                "message": f"Demo mode is now {new_mode}",
                "service": "api_gateway",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500

@app.route('/api/enable-slow-mode', methods=['POST'])
def enable_slow_mode():
    """Enable slow database mode for next query."""
    try:
        with tracer.start_as_current_span("api_gateway.enable_slow_mode") as span:
            span.set_attribute("service.component", "api_gateway")
            span.set_attribute("operation.name", "enable_slow_mode")
            
            # Set a flag that the next query should use slow mode
            gateway_stats["slow_mode_enabled"] = True
            
            span.set_attribute("slow_mode.enabled", True)
            
            print("🐌 Slow database mode enabled for next query")
            
            return jsonify({
                "success": True,
                "message": "Slow database mode enabled for next query",
                "service": "api_gateway",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500

@app.route('/api/create-slow-span', methods=['POST'])
def create_slow_span_demo():
    """🐌 Create a purposefully slow span for performance analysis."""
    try:
        # Try to extract trace context, but create a proper demo root if none exists
        token, is_root = extract_and_attach_trace_context()
        
        # If this is a root span, make it a proper demo session span
        if is_root:
            span_name = "demo_session.performance_analysis"
            print("🌟 Creating demo session root span for performance analysis")
        else:
            span_name = "api_gateway.create_slow_span_demo"
            print("🔗 Creating child span for slow span demo")
            
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("service.component", "api_gateway")
            span.set_attribute("operation.name", "create_slow_span_demo")
            
            print("🐌 Creating slow span for demo...")
            
            # Create a purposefully slow, well-instrumented span
            with tracer.start_as_current_span(
                "demo.slow_external_api_call",
                attributes={
                    "http.method": "POST",
                    "http.url": "https://api.external-service.com/analytics/heavy-computation",
                    "http.status_code": 200,
                    "service.name": "external_analytics_api",
                    "performance.issue": "high_cpu_usage_on_complex_aggregation",
                    "demo.purpose": "performance_analysis_demo",
                    "demo.timestamp": datetime.now().isoformat(),
                    "ai.operation_type": "data_processing",
                    "business.domain": "analytics"
                }
            ) as demo_span:
                # Simulate slow external API call
                demo_span.add_event("Starting heavy computation...")
                time.sleep(1.2)  # 1.2 second delay
                demo_span.add_event("Processing large dataset...")
                time.sleep(0.8)  # Additional delay
                demo_span.add_event("Finalizing results...")
                time.sleep(0.3)  # Final delay
                
                demo_span.set_attribute("demo.total_duration_ms", 2300)
                demo_span.set_attribute("demo.records_processed", 15000)
                
                gateway_stats["slow_spans_created"] += 1
                
                span.set_attribute("demo.span_created", True)
                span.set_attribute("demo.duration_ms", 2300)
                
                # Add demo session attributes if this is a root span
                if is_root:
                    span.set_attribute("demo.session_type", "performance_analysis")
                    span.set_attribute("demo.initiated_by", "keyboard_shortcut")
                    span.set_attribute("demo.purpose", "coralogix_ai_center_demo")
                
        return jsonify({
            "success": True,
            "span_name": "demo.slow_external_api_call",
            "duration_ms": 2300,
            "service": "api_gateway",
            "purpose": "Performance analysis demo for Coralogix AI Center",
            "timestamp": datetime.now().isoformat(),
            "suggested_query": "source spans last 5m | filter $l.serviceName == 'dataprime_assistant' and $d.duration > 1000000"
        })
        
    except Exception as e:
        print(f"❌ Failed to create slow span: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to create slow span",
            "details": str(e),
            "service": "api_gateway"
        }), 500
    finally:
        if 'token' in locals() and token:
            context.detach(token)

@app.route('/api/demo/slow-db', methods=['POST'])
def demo_slow_database():
    """🐌 Demonstrate slow database operations through the distributed system."""
    try:
        token, is_root = extract_and_attach_trace_context()
        
        # If this is a root span, make it a proper demo session span
        if is_root:
            span_name = "demo_session.database_performance"
            print("🌟 Creating demo session root span for database performance")
        else:
            span_name = "api_gateway.slow_database_demo"
            print("🔗 Creating child span for slow database demo")
        
        with tracer.start_as_current_span(span_name) as main_span:
            main_span.set_attribute("service.component", "api_gateway")
            main_span.set_attribute("demo.type", "slow_database")
            main_span.set_attribute("demo.purpose", "performance_analysis")
            main_span.set_attribute("demo.expected_duration_seconds", 3.0)
            
            print("🐌 Starting slow database demo through distributed system...")
            
            # Step 1: Call storage service with slow operation request
            headers = propagate_trace_context()
            
            slow_db_data = {
                "operation": "slow_analytics_query",
                "demo": True,
                "simulate_slow": True
            }
            
            start_time = time.time()
            
            with tracer.start_as_current_span("api_gateway.call_storage_service_slow") as storage_span:
                storage_span.set_attribute("downstream.service", "storage_service")
                storage_span.set_attribute("operation.type", "slow_database_demo")
                
                # Call storage service for slow database operation
                storage_response = requests.post(
                    f"{STORAGE_SERVICE_URL}/demo/slow-db",
                    json=slow_db_data,
                    headers=headers,
                    timeout=30
                )
                
                end_time = time.time()
                duration_seconds = round(end_time - start_time, 2)
                
                if storage_response.status_code == 200:
                    storage_result = storage_response.json()
                    
                    gateway_stats["slow_db_operations"] += 1
                    
                    main_span.set_attribute("demo.success", True)
                    main_span.set_attribute("demo.duration_seconds", duration_seconds)
                    
                    # Add demo session attributes if this is a root span
                    if is_root:
                        main_span.set_attribute("demo.session_type", "database_performance")
                        main_span.set_attribute("demo.initiated_by", "keyboard_shortcut")
                        main_span.set_attribute("demo.purpose", "coralogix_ai_center_demo")
                    
                    # Get trace ID for response
                    current_span = trace.get_current_span()
                    trace_id = format(current_span.get_span_context().trace_id, '032x') if current_span else None
                    
                    return jsonify({
                        "success": True,
                        "duration_seconds": duration_seconds,
                        "trace_id": trace_id,
                        "service": "api_gateway",
                        "storage_result": storage_result,
                        "performance_analysis": {
                            "total_duration": f"{duration_seconds}s",
                            "distributed_tracing": "enabled",
                            "services_involved": ["api_gateway", "storage_service"]
                        },
                        "recommendations": [
                            "Add database indexes for frequently queried columns",
                            "Implement query result caching for analytics queries",
                            "Consider database connection pooling optimization",
                            "Use read replicas for heavy analytical workloads"
                        ],
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    raise Exception(f"Storage service error: {storage_response.text}")
                    
    except Exception as e:
        print(f"❌ Slow database demo failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway",
            "timestamp": datetime.now().isoformat()
        }), 500
    finally:
        if 'token' in locals() and token:
            context.detach(token)

if __name__ == '__main__':
    print("🌐 API Gateway (Simple Fixed) starting on port 8010...")
    print(f"   Telemetry initialized: {os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true'}")
    app.run(host='0.0.0.0', port=8010, debug=False)
