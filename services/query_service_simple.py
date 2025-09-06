#!/usr/bin/env python3
"""🧠 Simple Query Service"""
import os, time
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

try:
    # 🔥 REMOVED FlaskInstrumentor - it creates automatic root spans
    # This was causing separate root traces instead of connected child spans
    print("🚫 Flask auto-instrumentation DISABLED for manual trace control")
except ImportError:
    pass

def extract_trace_context():
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/health', methods=['GET'])
def health():
    with tracer.start_as_current_span("query_service.health") as span:
        span.set_attribute("service.name", "query_service")
        time.sleep(0.010)
        return jsonify({"status": "healthy", "service": "query_service"})

@app.route('/generate', methods=['POST'])
def generate():
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    try:
        with tracer.start_as_current_span("query_service.generate_query") as span:
            span.set_attribute("service.name", "query_service")
            
            data = request.get_json()
            user_input = data.get('user_input', '')
            
            time.sleep(0.850)  # Simulate LLM call
            
            query = "source logs last 1h | filter $m.severity == 'Error'"
            
            return jsonify({
                "success": True,
                "query": query,
                "intent": "error_analysis",
                "intent_confidence": 0.85,
                "service": "query_service"
            })
    finally:
        if token:
            context.detach(token)

if __name__ == '__main__':
    print("🧠 Simple Query Service on port 8011")
    app.run(host='0.0.0.0', port=8011, debug=False)
