#!/usr/bin/env python3
"""✅ Simple Validation Service"""
import time
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

try:
    # 🔥 REMOVED FlaskInstrumentor - it creates automatic root spans
    # This was causing feedback spans to appear as separate root traces
    print("🚫 Flask auto-instrumentation DISABLED for manual trace control")
except ImportError:
    pass

def extract_trace_context():
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/health', methods=['GET'])
def health():
    with tracer.start_as_current_span("validation_service.health") as span:
        span.set_attribute("service.name", "validation_service")
        time.sleep(0.015)
        return jsonify({"status": "healthy", "service": "validation_service"})

@app.route('/validate', methods=['POST'])
def validate():
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    try:
        with tracer.start_as_current_span("validation_service.validate_query") as span:
            span.set_attribute("service.name", "validation_service")
            
            data = request.get_json()
            query = data.get('query', '')
            
            time.sleep(0.075)  # Validation processing
            
            is_valid = 'source' in query.lower() and 'logs' in query.lower()
            
            return jsonify({
                "success": True,
                "is_valid": is_valid,
                "syntax_score": 0.9 if is_valid else 0.3,
                "warnings": [] if is_valid else ["Query syntax issues"],
                "service": "validation_service"
            })
    finally:
        if token:
            context.detach(token)

if __name__ == '__main__':
    print("✅ Simple Validation Service on port 8012")
    app.run(host='0.0.0.0', port=8012, debug=False)
