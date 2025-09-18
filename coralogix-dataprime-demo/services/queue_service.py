#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


"""
📬 Queue Service - Message queue and background job management
Handles asynchronous processing requests and job queuing.
"""

import os
import json
import time
import uuid
import threading
from datetime import datetime
from queue import Queue, Empty
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

# In-memory message queue (in production, use Redis or RabbitMQ)
message_queue = Queue()
processed_messages = {}

# Service stats
queue_stats = {
    "messages_enqueued": 0,
    "messages_processed": 0,
    "messages_failed": 0,
    "queue_size": 0,
    "workers_active": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def extract_trace_context():
    """Extract trace context from request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

def background_worker():
    """Background worker to process queued messages."""
    import requests
    
    while True:
        try:
            # Get message from queue (blocking call with timeout)
            try:
                message = message_queue.get(timeout=1.0)
                queue_stats["workers_active"] += 1
                queue_stats["queue_size"] = message_queue.qsize()
                
                with tracer.start_as_current_span("queue_service.process_background_message") as span:
                    span.set_attribute("service.component", "queue_service")
                    span.set_attribute("operation.name", "process_background_message")
                    span.set_attribute("message.id", message.get("message_id", ""))
                    span.set_attribute("message.type", message.get("type", "unknown"))
                    
                    # Extract trace context from message
                    if "trace_context" in message:
                        propagator = TraceContextTextMapPropagator()
                        trace_context = propagator.extract(message["trace_context"])
                        if trace_context:
                            token = context.attach(trace_context)
                    
                    # Process message based on type
                    if message.get("type") == "query_processing":
                        # Send to processing service
                        headers = {}
                        propagator = TraceContextTextMapPropagator()
                        propagator.inject(headers)
                        
                        processing_response = requests.post(
                            "http://localhost:8014/process",
                            json=message.get("data", {}),
                            headers=headers,
                            timeout=10
                        )
                        
                        if processing_response.status_code == 200:
                            processed_messages[message["message_id"]] = {
                                "status": "completed",
                                "result": processing_response.json(),
                                "processed_at": datetime.now().isoformat()
                            }
                            queue_stats["messages_processed"] += 1
                        else:
                            processed_messages[message["message_id"]] = {
                                "status": "failed",
                                "error": processing_response.text,
                                "processed_at": datetime.now().isoformat()
                            }
                            queue_stats["messages_failed"] += 1
                    
                    # Add processing delay
                    time.sleep(0.020)  # 20ms processing time
                    
                    span.set_attribute("processing.success", True)
                
                message_queue.task_done()
                queue_stats["workers_active"] -= 1
                
            except Empty:
                # No messages in queue, continue polling
                continue
                
        except Exception as e:
            print(f"❌ Background worker error: {e}")
            queue_stats["messages_failed"] += 1
            queue_stats["workers_active"] = max(0, queue_stats["workers_active"] - 1)
            time.sleep(1.0)  # Wait before retrying

# Start background worker thread
worker_thread = threading.Thread(target=background_worker, daemon=True)
worker_thread.start()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("queue_service.health_check") as span:
        span.set_attribute("service.component", "queue_service")
        span.set_attribute("service.version", "1.0.0")
        
        # Add small delay to simulate processing
        time.sleep(0.012)  # 12ms
        
        queue_stats["queue_size"] = message_queue.qsize()
        
        return jsonify({
            "status": "healthy",
            "service": "queue_service",
            "version": "1.0.0",
            "queue_size": message_queue.qsize(),
            "worker_active": worker_thread.is_alive(),
            "stats": queue_stats,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/enqueue', methods=['POST'])
def enqueue_message():
    """Enqueue a message for background processing."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("queue_service.enqueue_message") as span:
        span.set_attribute("service.component", "queue_service")
        span.set_attribute("operation.name", "enqueue_message")
        
        try:
            queue_stats["messages_enqueued"] += 1
            
            # Get message data
            data = request.get_json()
            if not data:
                queue_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing message data"))
                return jsonify({"error": "Missing message data"}), 400
            
            # Generate message ID
            message_id = str(uuid.uuid4())
            
            # Create message with trace context
            message = {
                "message_id": message_id,
                "type": "query_processing",
                "data": data,
                "enqueued_at": datetime.now().isoformat(),
                "trace_context": dict(request.headers)  # Preserve trace context
            }
            
            span.set_attribute("message.id", message_id)
            span.set_attribute("message.type", "query_processing")
            span.set_attribute("message.data_size", len(json.dumps(data)))
            
            # Add queue processing delay
            time.sleep(0.018)  # 18ms
            
            # Enqueue message
            with tracer.start_as_current_span("queue_service.add_to_queue") as queue_span:
                message_queue.put(message)
                queue_stats["queue_size"] = message_queue.qsize()
                
                queue_span.set_attribute("queue.size_after", message_queue.qsize())
                queue_span.set_attribute("queue.message_added", True)
                
                time.sleep(0.005)  # 5ms for queue operation
            
            # Initialize processing status
            processed_messages[message_id] = {
                "status": "queued",
                "enqueued_at": datetime.now().isoformat()
            }
            
            result = {
                "success": True,
                "message_id": message_id,
                "queue_position": message_queue.qsize(),
                "estimated_processing_time_ms": message_queue.qsize() * 50,  # Rough estimate
                "service": "queue_service"
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.message_id", message_id)
            span.set_attribute("response.queue_position", message_queue.qsize())
            
            return jsonify(result)
            
        except Exception as e:
            queue_stats["errors"] += 1
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "service": "queue_service",
                "timestamp": datetime.now().isoformat()
            }), 500
        if token:
            context.detach(token)

@app.route('/status/<message_id>', methods=['GET'])
def get_message_status(message_id):
    """Get the processing status of a queued message."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("queue_service.get_message_status") as span:
        span.set_attribute("service.component", "queue_service")
        span.set_attribute("message.id", message_id)
        
        try:
            # Add small delay to simulate lookup
            time.sleep(0.008)  # 8ms
            
            if message_id not in processed_messages:
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Message not found"))
                return jsonify({
                    "success": False,
                    "error": "Message not found",
                    "message_id": message_id
                }), 404
            
            status_info = processed_messages[message_id]
            span.set_attribute("message.status", status_info.get("status", "unknown"))
            
            return jsonify({
                "success": True,
                "message_id": message_id,
                "status": status_info,
                "current_queue_size": message_queue.qsize(),
                "service": "queue_service"
            })
            
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "message_id": message_id,
                "service": "queue_service"
            }), 500
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("queue_service.get_stats") as span:
        span.set_attribute("service.component", "queue_service")
        
        queue_stats["queue_size"] = message_queue.qsize()
        
        return jsonify({
            "service": "queue_service",
            "stats": queue_stats,
            "current_queue_size": message_queue.qsize(),
            "worker_alive": worker_thread.is_alive(),
            "processed_messages_count": len(processed_messages),
            "timestamp": datetime.now().isoformat()
        })

if __name__ == '__main__':
    # Initialize instrumentation
    
    
    print("📬 Queue Service starting on port 5003...")
    print("   Background worker started")
    app.run(host='0.0.0.0', port=8013, debug=False)