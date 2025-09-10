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

# Global state for demo mode (matches API Gateway)
app_stats = {
    "demo_mode": "permissive",  # Default to permissive
    "queries_processed": 0,
    "evaluations_applied": 0
}

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
            
            # Get current demo mode
            current_mode = app_stats.get("demo_mode", "permissive")
            
            span.set_attribute("user.input", user_input)
            span.set_attribute("evaluation.mode", current_mode)
            
            if not openai_client:
                # Fallback to simulated processing if OpenAI not available
                print("⚠️ OpenAI not available, using fallback processing")
                time.sleep(0.1)
                query = "source logs | filter $l.severity == ERROR | limit 100"
                intent = "simulated_query"
                confidence = 0.75
                is_rejected = False
            else:
                # EVALUATION ENGINE - exactly like minimal app
                if current_mode == "smart":
                    # Smart mode: restricted to observability topics
                    system_prompt = """You are an expert in converting observability questions into DataPrime query language.
You help users analyze logs, traces, and metrics for system monitoring and troubleshooting.
Generate ONLY the raw query syntax with NO markdown formatting, code blocks, or explanations.

Examples:
source logs | last 1h | filter service == 'frontend'
source logs | last 24h | filter $l.severity == ERROR | limit 100
source spans | last 30m | filter operation_name == 'api_call' | group by service_name
source logs | last 6h | filter $d.message contains 'timeout' | count by service

Return only the DataPrime query as plain text. Do not use backticks, code blocks, or any markdown formatting.

If the question is not related to system observability, logs, errors, or monitoring, 
respond with: "This question is not related to system observability or log analysis."""
                    
                    span.set_attribute("evaluation.policy", "observability_only")
                    span.set_attribute("evaluation.enforcement", "strict")
                    
                else:
                    # Permissive mode: accepts any topic
                    system_prompt = """You are an expert in converting any user question into DataPrime query language syntax.
Always generate a query using proper DataPrime syntax, regardless of the topic.
Generate ONLY the raw query syntax with NO markdown formatting, code blocks, or explanations.

Examples:
source logs | last 1h | filter service == 'frontend'
source logs | last 24h | filter $l.severity == ERROR | limit 100
source spans | last 30m | filter operation_name == 'api_call' | group by service_name
source logs | last 6h | filter $d.message contains 'timeout' | count by service

Return only the DataPrime query as plain text. Do not use backticks, code blocks, or any markdown formatting.
Make your best attempt to create a valid DataPrime query for any input."""
                    
                    span.set_attribute("evaluation.policy", "permissive")
                    span.set_attribute("evaluation.enforcement", "none")
                
                # REAL OpenAI API call - this will be traced by LLM_tracekit
                with tracer.start_as_current_span("query_service.openai_call") as openai_span:
                    openai_span.set_attribute("ai.operation.name", "chat.completions")
                    openai_span.set_attribute("ai.request.model", "gpt-4o")
                    openai_span.set_attribute("evaluation.mode", current_mode)
                    
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
                    
                    # Clean up any markdown formatting that might have slipped through
                    import re
                    query = re.sub(r'^```[\w]*\n?', '', query)  # Remove opening code blocks
                    query = re.sub(r'\n?```$', '', query)      # Remove closing code blocks
                    query = query.strip()
                    
                    # Check if query was rejected due to evaluation
                    is_rejected = "not related to system observability" in query.lower()
                    
                    # Add AI-specific attributes for Coralogix AI Center
                    openai_span.set_attribute("ai.response.content", query[:100])
                    openai_span.set_attribute("evaluation.query_rejected", is_rejected)
                    openai_span.set_attribute("evaluation.rejection_reason", "non_observability_topic" if is_rejected else "none")
                    
                    if hasattr(response, 'usage') and response.usage:
                        openai_span.set_attribute("ai.usage.prompt_tokens", response.usage.prompt_tokens)
                        openai_span.set_attribute("ai.usage.completion_tokens", response.usage.completion_tokens)
                        openai_span.set_attribute("ai.usage.total_tokens", response.usage.total_tokens)
                
                # Classify intent for demo purposes
                intent = "error_analysis" if "error" in user_input.lower() else "general_query"
                confidence = 0.85
                
                app_stats["queries_processed"] += 1
                if current_mode == "smart":
                    app_stats["evaluations_applied"] += 1
            
            result = {
                "success": True,
                "query": query,
                "intent": intent,
                "intent_confidence": confidence,
                "model_used": "gpt-4o" if openai_client else "simulated",
                "service": "query_service",
                "ai_processing": bool(openai_client),  # Flag for AI Center
                "evaluation": {
                    "mode": current_mode,
                    "rejected": is_rejected if openai_client else False,
                    "reason": "non_observability_topic" if (openai_client and is_rejected) else None
                },
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("query.generated", query)
            span.set_attribute("query.intent", intent)
            span.set_attribute("query.confidence", confidence)
            span.set_attribute("evaluation.query_rejected", is_rejected if openai_client else False)
            
            return jsonify(result)
            
    except Exception as e:
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        return jsonify({"success": False, "error": str(e)}), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/api/get-mode', methods=['GET'])
def get_current_mode():
    """Get current demo mode."""
    return jsonify({
        "current_mode": app_stats.get("demo_mode", "permissive"),
        "stats": app_stats
    })

@app.route('/api/set-mode', methods=['POST'])
def set_mode():
    """Set demo mode (called by API Gateway)."""
    try:
        data = request.get_json()
        new_mode = data.get('mode', 'permissive')
        app_stats["demo_mode"] = new_mode
        
        print(f"🔧 Query Service mode changed to: {new_mode}")
        
        return jsonify({
            "success": True,
            "current_mode": new_mode
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "query_service",
        "telemetry_initialized": telemetry_enabled,  # Report actual telemetry status
        "openai_initialized": openai_initialized,
        "ai_center_ready": telemetry_enabled and openai_initialized,
        "demo_mode": app_stats.get("demo_mode", "permissive"),
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🧠 Query Service (AI Center Ready) starting on port 8011...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   OpenAI initialized: {openai_initialized}")
    print(f"   AI Center ready: {telemetry_enabled and openai_initialized}")
    app.run(host='0.0.0.0', port=8011, debug=False)
