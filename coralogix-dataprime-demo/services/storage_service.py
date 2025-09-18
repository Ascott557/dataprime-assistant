#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


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
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry for this service
telemetry_enabled = ensure_telemetry_initialized()

# Disable automatic SQLite instrumentation to prevent root spans
# We'll create manual spans within our trace context instead
print("🚫 SQLite auto-instrumentation DISABLED for manual trace control")

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
    """Extract trace context from incoming request headers with manual W3C parsing."""
    try:
        headers = dict(request.headers)
        
        # Debug: Show all headers
        print(f"🔍 Storage Service - Incoming headers: {list(headers.keys())}")
        
        # Check for trace headers
        traceparent_found = any(key.lower() == 'traceparent' for key in headers.keys())
        
        if not traceparent_found:
            print("❌ NO traceparent header found in storage service!")
            return None, True
        
        # Get traceparent header
        traceparent = None
        for key, value in headers.items():
            if key.lower() == 'traceparent':
                traceparent = value
                break
        
        if traceparent:
            print(f"✅ Storage Service - Found traceparent: Traceparent = {traceparent}")
            
            # Manual W3C trace context parsing (same as API Gateway)
            try:
                parts = traceparent.split('-')
                if len(parts) == 4 and parts[0] == '00':  # version-trace_id-span_id-flags
                    trace_id_hex = parts[1]
                    span_id_hex = parts[2]
                    
                    print(f"🔧 Storage Service - Manually parsed trace_id: {trace_id_hex}")
                    
                    # Create trace and span contexts manually
                    trace_id = int(trace_id_hex, 16)
                    span_id = int(span_id_hex, 16)
                    
                    # Create a span context for the parent
                    parent_span_context = trace.SpanContext(
                        trace_id=trace_id,
                        span_id=span_id,
                        is_remote=True,
                        trace_flags=trace.TraceFlags(0x01)  # Sampled
                    )
                    
                    # Create context with the parent span
                    parent_context = trace.set_span_in_context(
                        trace.NonRecordingSpan(parent_span_context)
                    )
                    
                    # Attach the context
                    token = context.attach(parent_context)
                    
                    print(f"✅ Storage Service - Manually joined trace: {trace_id_hex}")
                    print("✅ Storage Service correctly joined existing trace")
                    
                    return token, False
                    
            except Exception as parse_error:
                print(f"❌ Manual trace parsing failed: {parse_error}")
        
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
        
        # Debug: Log when /store endpoint is called
        print(f"🗄️ Storage /store endpoint called - trace context: {is_root}")
        
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
            
            # Store in database with explicit tracing (inheriting current context)
            with tracer.start_as_current_span("database.insert_simple_storage") as db_span:
                db_span.set_attribute("db.system", "sqlite")
                db_span.set_attribute("db.name", DB_FILE)
                db_span.set_attribute("db.statement", "INSERT INTO simple_storage (id, collection, data) VALUES (?, ?, ?)")
                db_span.set_attribute("db.table", "simple_storage")
                db_span.set_attribute("db.operation", "INSERT")
                db_span.set_attribute("service.name", "storage_service")
                db_span.set_attribute("operation.type", "database_write")
                
                # Add a prominent database operation event
                db_span.add_event("Starting SQLite INSERT operation", {
                    "table": "simple_storage",
                    "operation": "INSERT",
                    "record_id": record_id
                })
                
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO simple_storage (id, collection, data)
                    VALUES (?, ?, ?)
                ''', (record_id, collection, json.dumps(data.get("data", {}))))
                
                conn.commit()
                conn.close()
                
                db_span.set_attribute("db.rows_affected", cursor.rowcount)
                db_span.set_attribute("storage.record_id", record_id)
                db_span.set_attribute("storage.collection", collection)
                db_span.add_event("SQLite INSERT completed successfully", {
                    "rows_affected": cursor.rowcount,
                    "table": "simple_storage"
                })
            
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
        
        # Debug: Log when /feedback endpoint is called
        print(f"💬 Storage /feedback endpoint called - trace context: {is_root}")
        
        with tracer.start_as_current_span("storage_service.store_feedback") as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("operation.name", "store_feedback")
            
            storage_stats["database_operations"] += 1
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "Missing feedback data"}), 400
            
            feedback_id = str(uuid.uuid4())
            
            # Store feedback with explicit tracing (inheriting current context)
            with tracer.start_as_current_span("database.insert_feedback") as db_span:
                db_span.set_attribute("db.system", "sqlite")
                db_span.set_attribute("db.name", DB_FILE)
                db_span.set_attribute("db.statement", "INSERT INTO feedback (id, user_input, generated_query, rating, comment, trace_id) VALUES (?, ?, ?, ?, ?, ?)")
                db_span.set_attribute("db.table", "feedback")
                db_span.set_attribute("db.operation", "INSERT")
                db_span.set_attribute("service.name", "storage_service")
                db_span.set_attribute("operation.type", "database_write")
                
                # Add prominent feedback operation event
                db_span.add_event("Starting SQLite feedback INSERT", {
                    "table": "feedback",
                    "operation": "INSERT",
                    "feedback_id": feedback_id,
                    "rating": data.get('rating', 0)
                })
                
                # Simplified database operation - consistent with /store endpoint
                # Removed excessive nested spans that were causing conflicts
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
                
                db_span.set_attribute("db.rows_affected", 1)
                db_span.set_attribute("feedback.id", feedback_id)
                db_span.set_attribute("feedback.rating", data.get('rating', 0))
            
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

@app.route('/demo/slow-db', methods=['POST'])
def demo_slow_database():
    """🐌 Demonstrate slow database operations with SQLite instrumentation."""
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("storage_service.slow_database_demo") as main_span:
            main_span.set_attribute("service.component", "storage_service")
            main_span.set_attribute("demo.type", "slow_database")
            main_span.set_attribute("demo.purpose", "sqlite_performance_analysis")
            main_span.set_attribute("db.system", "sqlite")
            
            data = request.get_json() or {}
            simulate_slow = data.get("simulate_slow", True)
            
            print("🐌 Starting slow SQLite database demo...")
            
            # Step 1: Slow connection simulation
            with tracer.start_as_current_span("storage_service.slow_connection") as conn_span:
                conn_span.set_attribute("db.operation", "connect")
                conn_span.set_attribute("performance.issue", "connection_pool_exhausted")
                conn_span.add_event("Waiting for available connection...")
                
                if simulate_slow:
                    time.sleep(0.5)  # Simulate slow connection
                
                conn_span.add_event("Connection acquired")
                conn_span.set_attribute("db.connection_time_ms", 500)
            
            # Step 2: Slow query execution with multiple operations
            results = []
            
            with tracer.start_as_current_span("database.analytics_query_slow") as query_span:
                query_span.set_attribute("db.operation", "SELECT")
                query_span.set_attribute("db.table", "feedback")
                query_span.set_attribute("db.query", "SELECT * FROM feedback WHERE created_at >= datetime('now', '-30 days')")
                query_span.set_attribute("performance.issue", "missing_index_on_created_at")
                
                query_span.add_event("Starting complex analytics query...")
                
                # Simulate slow query with explicit SQLite tracing (inheriting current context)
                with tracer.start_as_current_span("sqlite.slow_analytics") as analytics_span:
                    analytics_span.set_attribute("db.system", "sqlite")
                    analytics_span.set_attribute("db.name", DB_FILE)
                    analytics_span.set_attribute("demo.slow_operation", True)
                    
                    # Connection span
                    with tracer.start_as_current_span("sqlite.connection") as connect_span:
                        connect_span.set_attribute("db.connection_string", f"sqlite:///{DB_FILE}")
                        conn = sqlite3.connect(DB_FILE)
                        cursor = conn.cursor()
                        
                        if simulate_slow:
                            time.sleep(1.2)  # Simulate slow query
                        
                        # Execute multiple queries with explicit tracing
                        with tracer.start_as_current_span("sqlite.query.count_feedback") as feedback_span:
                            feedback_span.set_attribute("db.statement", "SELECT COUNT(*) FROM feedback")
                            feedback_span.set_attribute("db.table", "feedback")
                            feedback_span.set_attribute("db.operation", "SELECT")
                            cursor.execute("SELECT COUNT(*) FROM feedback")
                            count_result = cursor.fetchone()[0]
                            feedback_span.set_attribute("db.rows_examined", count_result)
                            results.append({"operation": "count_feedback", "result": count_result})
                        
                        with tracer.start_as_current_span("sqlite.query.count_storage") as storage_span:
                            storage_span.set_attribute("db.statement", "SELECT COUNT(*) FROM simple_storage")
                            storage_span.set_attribute("db.table", "simple_storage")
                            storage_span.set_attribute("db.operation", "SELECT")
                            cursor.execute("SELECT COUNT(*) FROM simple_storage")
                            storage_count = cursor.fetchone()[0]
                            storage_span.set_attribute("db.rows_examined", storage_count)
                            results.append({"operation": "count_storage", "result": storage_count})
                        
                        conn.close()
                    
                    analytics_span.set_attribute("db.total_rows_examined", count_result + storage_count)
                
                query_span.add_event("Query execution completed")
                query_span.set_attribute("db.rows_examined", count_result + storage_count)
                query_span.set_attribute("db.execution_time_ms", 1200)
            
            # Step 3: Slow result processing
            with tracer.start_as_current_span("storage_service.slow_result_processing") as process_span:
                process_span.set_attribute("operation.type", "data_aggregation")
                process_span.set_attribute("performance.issue", "inefficient_aggregation")
                process_span.add_event("Processing query results...")
                
                if simulate_slow:
                    time.sleep(0.8)  # Simulate slow processing
                
                # Add some computed results
                total_records = sum(r["result"] for r in results)
                results.append({
                    "operation": "total_records", 
                    "result": total_records,
                    "computed": True
                })
                
                process_span.add_event("Result processing completed")
                process_span.set_attribute("processing.records_processed", total_records)
                process_span.set_attribute("processing.time_ms", 800)
                
                conn.close()
            
            # Update storage stats
            storage_stats["database_operations"] += 3  # Three operations performed
            
            # Get trace information
            current_span = trace.get_current_span()
            trace_id = format(current_span.get_span_context().trace_id, '032x') if current_span else None
            
            main_span.set_attribute("demo.success", True)
            main_span.set_attribute("demo.total_operations", 3)
            main_span.set_attribute("demo.total_duration_ms", 2500)
            
            return jsonify({
                "success": True,
                "service": "storage_service",
                "demo_type": "slow_database_operations",
                "database_system": "sqlite",
                "trace_id": trace_id,
                "operations_performed": len(results),
                "results": results,
                "performance_analysis": {
                    "connection_time": "500ms (slow connection pool)",
                    "query_execution": "1200ms (missing index)",
                    "result_processing": "800ms (inefficient aggregation)",
                    "total_duration": "2500ms"
                },
                "recommendations": [
                    "Add index on feedback.created_at column",
                    "Implement connection pooling for SQLite",
                    "Use prepared statements for repeated queries",
                    "Consider query result caching for analytics"
                ],
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        print(f"❌ Slow database demo failed: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "storage_service",
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
