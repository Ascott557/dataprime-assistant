#!/usr/bin/env python3
"""
🧠 Query Service - Simple Fixed Version (Working Telemetry)
Uses shared telemetry for consistent configuration across all services.
"""

import os
import sys
import time
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_telemetry_working import ensure_telemetry_initialized, get_telemetry_status

# Initialize telemetry for this service
telemetry_enabled = ensure_telemetry_initialized()

# Simple tracer - relies on shared telemetry setup
tracer = trace.get_tracer(__name__)

# Initialize OpenAI client
openai_client = None

def initialize_openai():
    """Initialize OpenAI client."""
    global openai_client
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key or api_key == 'your_openai_api_key_here':
            print("❌ OPENAI_API_KEY not found or not set")
            return False
            
        openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        return True
    except Exception as e:
        print(f"❌ OpenAI initialization failed: {e}")
        return False

# Initialize OpenAI on startup
openai_initialized = initialize_openai()

# Initialize Flask app
app = Flask(__name__)

def extract_and_attach_trace_context():
    """Extract trace context and determine if we should create root or child span."""
    propagator = TraceContextTextMapPropagator()
    headers = dict(request.headers)
    
    print(f"🔍 Query Service - Incoming headers: {list(headers.keys())}")
    
    # Check for trace headers
    traceparent_found = False
    for key in headers.keys():
        if key.lower() == 'traceparent':
            print(f"✅ Query Service - Found traceparent: {key} = {headers[key]}")
            traceparent_found = True
            break
    
    if not traceparent_found:
        print("❌ Query Service - NO traceparent header found!")
    
    # Extract trace context from headers
    incoming_context = propagator.extract(headers)
    print(f"🔍 Query Service - Extracted context: {incoming_context}")
    
    # Manual trace context parsing if propagator fails
    manual_trace_id = None
    manual_span_id = None
    if traceparent_found:
        for key, value in headers.items():
            if key.lower() == 'traceparent':
                parts = value.split('-')
                if len(parts) == 4 and parts[0] == '00':
                    manual_trace_id = parts[1]
                    manual_span_id = parts[2]
                    print(f"🔧 Query Service - Manually parsed trace_id: {manual_trace_id}")
                    break
    
    # Check if standard propagation worked
    if incoming_context:
        token = context.attach(incoming_context)
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            trace_id = format(current_span.get_span_context().trace_id, '032x')
            print(f"✅ Query Service - Joined via propagator: {trace_id}")
            return token, False  # False = not root
        else:
            print("⚠️ Query Service - Propagator extraction failed")
    
    # If propagator failed but we have manual trace info
    if manual_trace_id:
        from opentelemetry.trace import SpanContext, TraceFlags
        
        try:
            trace_id_int = int(manual_trace_id, 16)
            span_id_int = int(manual_span_id, 16)
            
            parent_span_context = SpanContext(
                trace_id=trace_id_int,
                span_id=span_id_int,
                is_remote=True,
                trace_flags=TraceFlags(0x01)
            )
            
            from opentelemetry.trace import set_span_in_context, NonRecordingSpan
            parent_span = NonRecordingSpan(parent_span_context)
            manual_context = set_span_in_context(parent_span)
            
            token = context.attach(manual_context)
            print(f"✅ Query Service - Manually joined trace: {manual_trace_id}")
            return token, False  # False = not root
            
        except Exception as e:
            print(f"❌ Query Service - Manual trace creation failed: {e}")
    
    print("📝 Query Service - Creating new root (trace propagation failed)")
    return None, True

@app.route('/generate', methods=['POST'])
def generate_query():
    """Generate DataPrime query with simple telemetry."""
    # Extract incoming trace context with robust fallback
    token, is_root = extract_and_attach_trace_context()
    
    try:
        # Choose span name based on whether this is root or child
        span_name = "query_service_root.generate_query" if is_root else "query_service.generate_dataprime_query"
        
        with tracer.start_as_current_span(span_name) as span:
            if is_root:
                span.set_attribute("trace.type", "unexpected_root")
                print("⚠️ WARNING: Query Service creating root span - trace propagation failed!")
            else:
                span.set_attribute("trace.type", "child_operation")
                print("✅ Query Service correctly joined existing trace")
            
            span.set_attribute("service.component", "query_service")
            span.set_attribute("operation.name", "generate_dataprime_query")
            
            data = request.get_json()
            user_input = data.get('user_input', '')
            
            span.set_attribute("user.input", user_input)
            
            if not openai_client:
                # Fallback to simulated processing if OpenAI not available
                print("⚠️ OpenAI not available, using fallback processing")
                time.sleep(0.1)
                query = "source logs | filter $l.severity == ERROR | limit 100"
                intent = "simulated_query"
                confidence = 0.75
            else:
                # REAL OpenAI API call - this will be traced by LLM_tracekit
                with tracer.start_as_current_span("query_service.openai_call") as openai_span:
                    openai_span.set_attribute("ai.operation.name", "chat.completions")
                    openai_span.set_attribute("ai.request.model", "gpt-4o")
                    
                    system_prompt = """You are an expert DataPrime query generator. 
Generate ONLY the DataPrime query syntax, no explanations. 
Convert natural language into DataPrime queries for log analysis.

Examples:
- "Show me errors" → source logs | filter $l.severity == ERROR | limit 100
- "Performance issues" → source logs | filter $d.response_time > 1000 | limit 50
- "Last hour" → source logs | filter $m.timestamp > now() - 1h | limit 100"""
                    
                    # This OpenAI call will be automatically instrumented by llm_tracekit
                    response = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_input}
                        ],
                        max_tokens=200,
                        temperature=0.3
                    )
                    
                    query = response.choices[0].message.content.strip()
                    
                    # Add AI-specific attributes for Coralogix AI Center
                    openai_span.set_attribute("ai.response.content", query[:100])
                    if hasattr(response, 'usage') and response.usage:
                        openai_span.set_attribute("ai.usage.prompt_tokens", response.usage.prompt_tokens)
                        openai_span.set_attribute("ai.usage.completion_tokens", response.usage.completion_tokens)
                        openai_span.set_attribute("ai.usage.total_tokens", response.usage.total_tokens)
                
                # Classify intent for demo purposes
                intent = "error_analysis" if "error" in user_input.lower() else "general_query"
                confidence = 0.85
            
            result = {
                "success": True,
                "query": query,
                "intent": intent,
                "intent_confidence": confidence,
                "model_used": "gpt-4o" if openai_client else "simulated",
                "service": "query_service",
                "ai_processing": bool(openai_client),  # Flag for AI Center
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
        "telemetry_initialized": telemetry_enabled,  # Report actual telemetry status
        "openai_initialized": openai_initialized,
        "ai_center_ready": telemetry_enabled and openai_initialized,
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🧠 Query Service (AI Center Ready) starting on port 8011...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   OpenAI initialized: {openai_initialized}")
    print(f"   AI Center ready: {telemetry_enabled and openai_initialized}")
    app.run(host='0.0.0.0', port=8011, debug=False)
