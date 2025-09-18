#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


"""
🔄 Queue Worker Service - Enterprise Async Processing
Processes background jobs from queue and calls other APIs.
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

# Service endpoints
EXTERNAL_API_SERVICE_URL = "http://localhost:8016"
STORAGE_SERVICE_URL = "http://localhost:8015"

def extract_trace_context():
    """Extract trace context from incoming request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

def propagate_trace_context(headers=None):
    """Propagate trace context to downstream calls."""
    if headers is None:
        headers = {}
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers

@app.route('/process-job', methods=['POST'])
def process_job():
    """Process a background job - demonstrates API → Queue → Another API → DB pattern."""
    incoming_context = extract_trace_context()
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("queue_worker.process_job") as span:
            span.set_attribute("service.component", "queue_worker_service")
            span.set_attribute("operation.name", "process_background_job")
            
            data = request.get_json()
            job_id = data.get('job_id', f"job_{int(time.time())}")
            query_data = data.get('query_data', {})
            
            span.set_attribute("job.id", job_id)
            span.set_attribute("job.type", "query_enrichment")
            
            # Step 1: Call External API Service (API → Another API pattern)
            with tracer.start_as_current_span("queue_worker.call_external_api") as api_span:
                api_span.set_attribute("downstream.service", "external_api_service")
                
                headers = propagate_trace_context()
                
                # This demonstrates: API → Queue → Another API
                external_response = requests.post(
                    f"{EXTERNAL_API_SERVICE_URL}/enrich-data",
                    json=query_data,
                    headers=headers,
                    timeout=10
                )
                
                if external_response.status_code != 200:
                    raise Exception(f"External API error: {external_response.text}")
                
                enriched_data = external_response.json()
                api_span.set_attribute("external.apis_called", enriched_data.get("external_apis_called", 0))
            
            # Step 2: Process the enriched data (business logic)
            with tracer.start_as_current_span("queue_worker.process_data") as process_span:
                process_span.set_attribute("operation.name", "business_logic_processing")
                
                # Simulate complex processing
                time.sleep(0.15)  # 150ms processing time
                
                processed_result = {
                    "job_id": job_id,
                    "original_query": query_data.get('query', ''),
                    "enrichment_data": enriched_data.get('enriched_data', {}),
                    "processing_status": "completed",
                    "processing_time_ms": 150,
                    "worker_node": "worker-01"
                }
                
                process_span.set_attribute("processing.time_ms", 150)
                process_span.set_attribute("processing.status", "completed")
            
            # Step 3: Store results in Database (Another API → DB pattern)
            with tracer.start_as_current_span("queue_worker.store_results") as storage_span:
                storage_span.set_attribute("downstream.service", "storage_service")
                
                headers = propagate_trace_context()
                
                # This demonstrates: Another API → Database
                storage_response = requests.post(
                    f"{STORAGE_SERVICE_URL}/store",
                    json={
                        "collection": "processed_jobs",
                        "data": processed_result
                    },
                    headers=headers,
                    timeout=5
                )
                
                if storage_response.status_code != 200:
                    raise Exception(f"Storage error: {storage_response.text}")
                
                storage_result = storage_response.json()
                storage_span.set_attribute("storage.record_id", storage_result.get("record_id", "unknown"))
            
            result = {
                "success": True,
                "job_id": job_id,
                "processing_status": "completed",
                "external_apis_called": enriched_data.get("external_apis_called", 0),
                "stored_record_id": storage_result.get("record_id"),
                "total_processing_time_ms": 150 + enriched_data.get("total_external_latency_ms", 0),
                "service": "queue_worker_service",
                "timestamp": datetime.now().isoformat()
            }
            
            span.set_attribute("job.status", "completed")
            span.set_attribute("job.total_time_ms", result["total_processing_time_ms"])
            
            return jsonify(result)
            
    except Exception as e:
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        return jsonify({"success": False, "error": str(e), "job_id": job_id}), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "queue_worker_service",
        "pattern": "API → Queue → Another API → Database",
        "dependencies": ["external_api_service", "storage_service"],
        "telemetry_initialized": os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true',
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("🔄 Queue Worker Service starting on port 8017...")
    print("   Pattern: API → Queue → Another API → Database")
    print("   Dependencies: External API Service, Storage Service")
    print(f"   Telemetry initialized: {os.getenv('DISTRIBUTED_TELEMETRY_INITIALIZED') == 'true'}")
    app.run(host='0.0.0.0', port=8017, debug=False)
