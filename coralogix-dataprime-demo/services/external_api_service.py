#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


"""
🌍 External API Service - Enterprise Pattern
Calls real external APIs to demonstrate enterprise complexity.
"""

import os
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Simple tracer - relies on global telemetry from distributed_app.py
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

def extract_trace_context():
    """Extract trace context from incoming request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

def propagate_trace_context(headers=None):
    """Propagate trace context to external calls."""
    if headers is None:
        headers = {}
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers

@app.route('/enrich-data', methods=['POST'])
def enrich_data():
    """Enrich query data by calling external APIs."""
    incoming_context = extract_trace_context()
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("external_api.enrich_data") as span:
            span.set_attribute("service.component", "external_api_service")
            span.set_attribute("operation.name", "enrich_query_data")
            
            data = request.get_json()
            query = data.get('query', '')
            intent = data.get('intent', 'unknown')
            
            span.set_attribute("input.query", query)
            span.set_attribute("input.intent", intent)
            
            # Call external APIs based on intent
            enriched_data = {}
            
            # 1. Call "Time Service" API (simulated)
            with tracer.start_as_current_span("external_api.call_time_service") as time_span:
                time_span.set_attribute("external.service", "time_api")
                time_span.set_attribute("external.endpoint", "/current-time")
                
                # Simulate external API call with realistic latency
                time.sleep(0.4)  # 400ms - realistic external API latency
                
                enriched_data["timestamp_info"] = {
                    "query_time": datetime.now().isoformat(),
                    "timezone": "UTC",
                    "epoch": int(datetime.now().timestamp())
                }
                time_span.set_attribute("external.response_time_ms", 400)
            
            # 2. Call "Metadata Enrichment" API (simulated)
            if intent == "error_analysis":
                with tracer.start_as_current_span("external_api.call_metadata_service") as meta_span:
                    meta_span.set_attribute("external.service", "metadata_api")
                    meta_span.set_attribute("external.endpoint", "/error-context")
                    
                    # Simulate another external API call
                    time.sleep(0.3)  # 300ms
                    
                    enriched_data["error_context"] = {
                        "severity_levels": ["ERROR", "CRITICAL"],
                        "common_patterns": ["timeout", "connection_refused", "null_pointer"],
                        "suggested_filters": ["$m.severity == 'Error'", "$d.error_type exists"]
                    }
                    meta_span.set_attribute("external.response_time_ms", 300)
            
            # 3. Call "Analytics Service" API (simulated)
            with tracer.start_as_current_span("external_api.call_analytics_service") as analytics_span:
                analytics_span.set_attribute("external.service", "analytics_api")
                analytics_span.set_attribute("external.endpoint", "/query-analytics")
                
                # Simulate third external API call
                time.sleep(0.2)  # 200ms
                
                enriched_data["analytics"] = {
                    "estimated_results": 1250,
                    "performance_impact": "low",
                    "optimization_suggestions": ["add time range", "use indexed fields"]
                }
                analytics_span.set_attribute("external.response_time_ms", 200)
            
            result = {
                "success": True,
                "original_query": query,
                "enriched_data": enriched_data,
                "external_apis_called": 3,
                "total_external_latency_ms": 900,
                "service": "external_api_service",
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("external.apis_called", 3)
            span.set_attribute("external.total_latency_ms", 900)
            span.set_attribute("response.success", True)
            
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
        "service": "external_api_service",
        "external_apis": ["time_api", "metadata_api", "analytics_api"],
        "telemetry_initialized": os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true',
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🌍 External API Service starting on port 8016...")
    print("   Simulates calls to: Time API, Metadata API, Analytics API")
    print(f"   Telemetry initialized: {os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true'}")
    app.run(host='0.0.0.0', port=8016, debug=False)
