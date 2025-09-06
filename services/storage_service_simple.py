#!/usr/bin/env python3
"""
💾 Storage Service - Simplified working version
Handles basic data storage operations for the distributed system.
"""

import os
import sys
import json
import time
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared_telemetry_working import ensure_telemetry_initialized

# Initialize telemetry for this service
telemetry_enabled = ensure_telemetry_initialized()

# Initialize tracer
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# Database file
DB_FILE = "distributed_feedback.db"

# Service stats
storage_stats = {
    "records_stored": 0,
    "feedback_entries": 0,
    "database_operations": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def extract_and_attach_trace_context():
    """Extract trace context from incoming request headers."""
    try:
        propagator = TraceContextTextMapPropagator()
        headers = dict(request.headers)
        
        # Check for trace headers
        traceparent_found = any(key.lower() == 'traceparent' for key in headers.keys())
        
        if not traceparent_found:
            print("❌ NO traceparent header found in storage service!")
            return None, True
        
        # Try standard propagation
        incoming_context = propagator.extract(headers)
        
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = format(current_span.get_span_context().trace_id, '032x')
                print(f"✅ Storage service joined existing trace: {trace_id}")
                return token, False
        
        print("⚠️ Storage service creating root span - trace propagation failed!")
        return None, True
        
    except Exception as e:
        print(f"❌ Trace context extraction error: {e}")
        return None, True

def initialize_database():
    """Initialize SQLite database with required tables."""
    try:
        with tracer.start_as_current_span("storage_service.initialize_database") as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("database.name", DB_FILE)
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Feedback table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    user_input TEXT NOT NULL,
                    generated_query TEXT NOT NULL,
                    rating INTEGER NOT NULL,
                    comment TEXT,
                    trace_id TEXT,
                    span_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            # Simple storage table for demo
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS simple_storage (
                    id TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
            print("✅ Database initialized successfully")
            return True
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("storage_service.health_check") as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("service.version", "1.0.0")
            
            # Test database connection
            database_healthy = True
            try:
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM feedback")
                feedback_count = cursor.fetchone()[0]
                conn.close()
                span.set_attribute("database.feedback_count", feedback_count)
            except Exception as e:
                database_healthy = False
                span.add_event("database_connection_failed", {"error": str(e)})
            
            return jsonify({
                "status": "healthy" if database_healthy else "degraded",
                "service": "storage_service",
                "version": "1.0.0",
                "database_healthy": database_healthy,
                "stats": storage_stats,
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"❌ Storage health check error: {e}")
        return jsonify({
            "status": "error",
            "service": "storage_service",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
    finally:
        if 'token' in locals() and token:
            context.detach(token)

@app.route('/store', methods=['POST'])
def store_data():
    """Store data in the database."""
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("storage_service.store_data") as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("operation.name", "store_data")
            
            storage_stats["database_operations"] += 1
            
            # Get data to store
            data = request.get_json()
            if not data:
                storage_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing data"))
                return jsonify({"error": "Missing data to store"}), 400
            
            # Simple storage simulation
            record_id = str(uuid.uuid4())
            collection = data.get("collection", "default")
            
            span.set_attribute("storage.collection", collection)
            span.set_attribute("storage.record_id", record_id)
            
            # Store in database
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO simple_storage (id, collection, data)
                VALUES (?, ?, ?)
            ''', (record_id, collection, json.dumps(data.get("data", {}))))
            
            conn.commit()
            conn.close()
            
            # Add processing delay
            time.sleep(0.040)  # 40ms for data processing
            
            storage_stats["records_stored"] += 1
            
            return jsonify({
                "success": True,
                "record_id": record_id,
                "collection": collection,
                "service": "storage_service",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"❌ Storage error: {e}")
        storage_stats["errors"] += 1
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "storage_service",
            "timestamp": datetime.now().isoformat()
        }), 500
    finally:
        if 'token' in locals() and token:
            context.detach(token)

@app.route('/feedback', methods=['POST'])
def store_feedback():
    """Store user feedback in the database."""
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("storage_service.store_feedback") as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("operation.name", "store_feedback")
            
            storage_stats["database_operations"] += 1
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "Missing feedback data"}), 400
            
            feedback_id = str(uuid.uuid4())
            
            # Store feedback
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO feedback (id, user_input, generated_query, rating, comment, trace_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                feedback_id,
                data.get('user_input', ''),
                data.get('generated_query', ''),
                data.get('rating', 0),
                data.get('comment', ''),
                data.get('trace_id', '')
            ))
            
            conn.commit()
            conn.close()
            
            storage_stats["feedback_entries"] += 1
            
            return jsonify({
                "success": True,
                "feedback_id": feedback_id,
                "service": "storage_service",
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"❌ Feedback storage error: {e}")
        storage_stats["errors"] += 1
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "storage_service",
            "timestamp": datetime.now().isoformat()
        }), 500
    finally:
        if 'token' in locals() and token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get storage service statistics."""
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("storage_service.get_stats") as span:
            span.set_attribute("service.component", "storage_service")
            
            return jsonify({
                "service": "storage_service", 
                "stats": storage_stats,
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"❌ Storage stats error: {e}")
        return jsonify({
            "service": "storage_service",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
    finally:
        if 'token' in locals() and token:
            context.detach(token)

if __name__ == '__main__':
    if not telemetry_enabled:
        print("⚠️ WARNING: Telemetry initialization failed - SQLite operations may not be traced")
    
    # Initialize database
    if not initialize_database():
        print("❌ Failed to initialize database. Exiting.")
        exit(1)
    
    print("💾 Storage Service (Simple) starting on port 8015...")
    print(f"   Database: {DB_FILE}")
    print(f"   SQLite instrumentation: {'✅ Active' if telemetry_enabled else '❌ Failed'}")
    app.run(host='0.0.0.0', port=8015, debug=False)
