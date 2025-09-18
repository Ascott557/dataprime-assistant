#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


"""
✅ Validation Service - Simple Fixed Version (Working Telemetry)
Uses ONLY the global telemetry from distributed_app.py - no local initialization.
"""

import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Simple tracer - no complex initialization
tracer = trace.get_tracer(__name__)

# Initialize Flask app
app = Flask(__name__)

def extract_and_attach_trace_context():
    """Extract trace context and determine if we should create root or child span."""
    propagator = TraceContextTextMapPropagator()
    headers = dict(request.headers)
    
    print(f"🔍 Validation Service - Incoming headers: {list(headers.keys())}")
    
    # Check for trace headers
    traceparent_found = False
    for key in headers.keys():
        if key.lower() == 'traceparent':
            print(f"✅ Validation Service - Found traceparent: {key} = {headers[key]}")
            traceparent_found = True
            break
    
    if not traceparent_found:
        print("❌ Validation Service - NO traceparent header found!")
    
    # Extract trace context from headers
    incoming_context = propagator.extract(headers)
    print(f"🔍 Validation Service - Extracted context: {incoming_context}")
    
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
                    print(f"🔧 Validation Service - Manually parsed trace_id: {manual_trace_id}")
                    break
    
    # Check if standard propagation worked
    if incoming_context:
        token = context.attach(incoming_context)
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            trace_id = format(current_span.get_span_context().trace_id, '032x')
            print(f"✅ Validation Service - Joined via propagator: {trace_id}")
            return token, False  # False = not root
        else:
            print("⚠️ Validation Service - Propagator extraction failed")
    
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
            print(f"✅ Validation Service - Manually joined trace: {manual_trace_id}")
            return token, False  # False = not root
            
        except Exception as e:
            print(f"❌ Validation Service - Manual trace creation failed: {e}")
    
    print("📝 Validation Service - Creating new root (trace propagation failed)")
    return None, True

@app.route('/validate', methods=['POST'])
def validate_query():
    """Validate DataPrime query with robust trace context extraction."""
    # Extract incoming trace context with robust fallback
    token, is_root = extract_and_attach_trace_context()
    
    try:
        # Choose span name based on whether this is root or child
        span_name = "validation_service_root.validate" if is_root else "validation_service.validate_query"
        
        with tracer.start_as_current_span(span_name) as span:
            if is_root:
                span.set_attribute("trace.type", "unexpected_root")
                print("⚠️ WARNING: Validation Service creating root span - trace propagation failed!")
            else:
                span.set_attribute("trace.type", "child_operation")
                print("✅ Validation Service correctly joined existing trace")
            
            span.set_attribute("service.component", "validation_service")
            span.set_attribute("service.component", "validation_service")
            span.set_attribute("operation.name", "validate_dataprime_syntax")
            
            data = request.get_json()
            query = data.get('query', '')
            
            span.set_attribute("query.text", query)
            
            # Simulate validation processing time
            time.sleep(0.05)
            
            # Simple validation logic
            is_valid = True
            warnings = []
            syntax_score = 0.9
            
            if not query.strip():
                is_valid = False
                syntax_score = 0.0
                warnings.append("Empty query")
            elif 'source' not in query.lower():
                warnings.append("Query should start with 'source'")
                syntax_score = 0.7
            
            result = {
                "success": True,
                "is_valid": is_valid,
                "syntax_score": syntax_score,
                "warnings": warnings,
                "service": "validation_service",
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("validation.is_valid", is_valid)
            span.set_attribute("validation.syntax_score", syntax_score)
            span.set_attribute("validation.warnings_count", len(warnings))
            
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
        "service": "validation_service",
        "telemetry_initialized": os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true',
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("✅ Validation Service (Simple Fixed) starting on port 8012...")
    print(f"   Telemetry initialized: {os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true'}")
    app.run(host='0.0.0.0', port=8012, debug=False)
