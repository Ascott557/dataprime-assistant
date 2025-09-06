#!/usr/bin/env python3
"""
💾 Storage Service - Data persistence and feedback management
Handles database operations, feedback storage, and data retrieval.
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

# NOTE: Flask auto-instrumentation disabled to prevent automatic root spans

# Database file
DB_FILE = "distributed_feedback.db"

# Service stats
storage_stats = {
    "records_stored": 0,
    "feedback_entries": 0,
    "insights_stored": 0,
    "database_operations": 0,
    "database_size_mb": 0.0,
    "errors": 0,
    "start_time": datetime.now()
}

def extract_and_attach_trace_context():
    """Extract trace context using the same robust method as API Gateway."""
    propagator = TraceContextTextMapPropagator()
    headers = dict(request.headers)
    
    print(f"🔍 Storage service incoming headers: {list(headers.keys())}")
    
    # Check for trace headers
    traceparent_found = False
    for key in headers.keys():
        if key.lower() == 'traceparent':
            print(f"✅ Found traceparent header: {key} = {headers[key]}")
            traceparent_found = True
            break
    
    if not traceparent_found:
        print("❌ NO traceparent header found in storage service!")
        return None, True
    
    # Try standard propagation first
    incoming_context = propagator.extract(headers)
    
    # Manual trace context parsing as fallback
    manual_trace_id = None
    manual_span_id = None
    if traceparent_found:
        for key, value in headers.items():
            if key.lower() == 'traceparent':
                parts = value.split('-')
                if len(parts) == 4 and parts[0] == '00':
                    manual_trace_id = parts[1]
                    manual_span_id = parts[2]
                    print(f"🔧 Storage service manually parsed trace_id: {manual_trace_id}")
                    break
    
    # Check if standard propagation worked
    if incoming_context:
        token = context.attach(incoming_context)
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            trace_id = format(current_span.get_span_context().trace_id, '032x')
            print(f"✅ Storage service joined existing trace via propagator: {trace_id}")
            return token, False
    
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
            print(f"✅ Storage service manually joined existing trace: {manual_trace_id}")
            return token, False
        except Exception as e:
            print(f"❌ Storage service manual trace context creation failed: {e}")
    
    print("⚠️ Storage service - trace context extraction failed, creating root")
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
            
            # Processing insights table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_insights (
                    id TEXT PRIMARY KEY,
                    user_input TEXT NOT NULL,
                    generated_query TEXT NOT NULL,
                    complexity_analysis TEXT,
                    performance_insights TEXT,
                    enriched_data TEXT,
                    trace_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Query analytics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS query_analytics (
                    id TEXT PRIMARY KEY,
                    query_hash TEXT NOT NULL,
                    execution_count INTEGER DEFAULT 1,
                    avg_processing_time_ms REAL,
                    success_rate REAL,
                    last_executed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            
            span.set_attribute("database.tables_created", 3)
            span.add_event("database_initialized")
            
            print("✅ Database initialized successfully")
            return True
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

def get_database_size():
    """Get database file size in MB."""
    try:
        if os.path.exists(DB_FILE):
            size_bytes = os.path.getsize(DB_FILE)
            return round(size_bytes / (1024 * 1024), 2)
        return 0.0
    except:
        return 0.0

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Extract and set trace context for proper distributed tracing
        token, is_root = extract_and_attach_trace_context()
        
        if is_root:
            print("⚠️ WARNING: Storage health check creating root span - trace propagation failed!")
        else:
            print("✅ Storage health check correctly joined existing trace")
        
        with tracer.start_as_current_span("storage_service.health_check") as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("service.version", "1.0.0")
            
            # Add small delay to simulate processing
            time.sleep(0.025)  # 25ms
            
            # Update database size
            storage_stats["database_size_mb"] = get_database_size()
            
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
                "database_size_mb": storage_stats["database_size_mb"],
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

@app.route('/feedback', methods=['POST'])
def store_feedback():
    """Store user feedback in the database."""
    print(f"\n💾 STORAGE SERVICE - FEEDBACK STORAGE")
    token, is_root = extract_and_attach_trace_context()
    
    if is_root:
        print("⚠️ WARNING: Storage service creating root span - trace propagation failed!")
    else:
        print("✅ Storage service correctly joined existing trace")
    
    try:
        span_name = "storage_service_root.store_feedback" if is_root else "storage_service.store_feedback"
        with tracer.start_as_current_span(span_name) as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("operation.name", "store_feedback")
            
            try:
                storage_stats["database_operations"] += 1
                
                # Get feedback data
                data = request.get_json()
                if not data:
                    storage_stats["errors"] += 1
                    span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing feedback data"))
                    return jsonify({"error": "Missing feedback data"}), 400
                
                # Validate required fields
                required_fields = ['user_input', 'generated_query', 'rating']
                for field in required_fields:
                    if field not in data:
                        storage_stats["errors"] += 1
                        span.set_status(trace.Status(trace.StatusCode.ERROR, f"Missing {field}"))
                        return jsonify({"error": f"Missing required field: {field}"}), 400
                
                feedback_id = str(uuid.uuid4())
                rating = data['rating']
                
                span.set_attribute("feedback.id", feedback_id)
                span.set_attribute("feedback.rating", rating)
                span.set_attribute("feedback.has_comment", bool(data.get('comment')))
                
                # Add database processing delay
                time.sleep(0.035)  # 35ms for database operation
                
                # Simple database operations (WORKING VERSION)
                conn = sqlite3.connect(DB_FILE)
                cursor = conn.cursor()
                
                # Get trace context for storage
                current_span = trace.get_current_span()
                trace_id = format(current_span.get_span_context().trace_id, '032x') if current_span else None
                span_id = format(current_span.get_span_context().span_id, '016x') if current_span else None
                
                # Simple INSERT without complex span wrapping
                cursor.execute('''
                    INSERT INTO feedback (id, user_input, generated_query, rating, comment, trace_id, span_id, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    feedback_id,
                    data['user_input'],
                    data['generated_query'],
                    rating,
                    data.get('comment', ''),
                    trace_id,
                    span_id,
                    json.dumps(data.get('metadata', {}))
                ))
                
                # Simple analytics update
                query_hash = str(hash(data['generated_query']))[:16]
                cursor.execute("SELECT id FROM query_analytics WHERE query_hash = ?", (query_hash,))
                existing = cursor.fetchone()
                
                if existing:
                    cursor.execute('''
                        UPDATE query_analytics 
                        SET execution_count = execution_count + 1, last_executed = CURRENT_TIMESTAMP
                        WHERE query_hash = ?
                    ''', (query_hash,))
                else:
                    cursor.execute('''
                        INSERT INTO query_analytics (id, query_hash, execution_count, avg_processing_time_ms, success_rate)
                        VALUES (?, ?, 1, 100.0, 1.0)
                    ''', (str(uuid.uuid4()), query_hash))
                
                # Simple commit
                conn.commit()
                conn.close()
                
                storage_stats["records_stored"] += 1
                storage_stats["feedback_entries"] += 1
                
                result = {
                    "success": True,
                    "feedback_id": feedback_id,
                    "stored_at": datetime.now().isoformat(),
                    "rating": rating,
                    "trace_id": trace_id,
                    "service": "storage_service"
                }
                
                span.set_attribute("response.success", True)
                span.set_attribute("response.feedback_id", feedback_id)
                
                return jsonify(result)
                
            except Exception as e:
                storage_stats["errors"] += 1
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "service": "storage_service",
                    "timestamp": datetime.now().isoformat()
                }), 500
            
    finally:
        if token:
            context.detach(token)

@app.route('/store', methods=['POST'])
def store_data():
    """Store processing insights and other data."""
    try:
        # Extract and set trace context for proper distributed tracing
        token, is_root = extract_and_attach_trace_context()
        
        if is_root:
            print("⚠️ WARNING: Storage store creating root span - trace propagation failed!")
        else:
            print("✅ Storage store correctly joined existing trace")
        
        with tracer.start_as_current_span("storage_service.store_processing_data") as span:
            span.set_attribute("service.component", "storage_service")
            span.set_attribute("operation.name", "store_processing_data")
            
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
            
            # Add storage processing delay
            time.sleep(0.040)  # 40ms for data processing
            
            # Simulate successful storage
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

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get storage service statistics."""
    try:
        # Extract and set trace context for proper distributed tracing
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("storage_service.get_stats") as span:
                    conn = sqlite3.connect(DB_FILE)
                    cursor = conn.cursor()
                    
                    # Get trace context
                    current_span = trace.get_current_span()
                    trace_id = format(current_span.get_span_context().trace_id, '032x') if current_span else None
                    
                    cursor.execute('''
                        INSERT INTO processing_insights (id, user_input, generated_query, complexity_analysis, performance_insights, enriched_data, trace_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record_id,
                        data.get('user_input', ''),
                        data.get('query', ''),
                        json.dumps(data.get('complexity_analysis', {})),
                        json.dumps(data.get('performance_insights', {})),
                        json.dumps(data.get('enriched_data', {})),
                        trace_id
                    ))
                    
                    conn.commit()
                    conn.close()
                    
                    insights_span.set_attribute("database.table", "processing_insights")
                    insights_span.set_attribute("insights.complexity_level", 
                                              data.get('complexity_analysis', {}).get('complexity_level', 'unknown'))
                    
                    storage_stats["insights_stored"] += 1
                    
                    time.sleep(0.025)  # 25ms for insights storage
            
            storage_stats["records_stored"] += 1
            
            result = {
                "success": True,
                "id": record_id,
                "type": data_type,
                "stored_at": datetime.now().isoformat(),
                "service": "storage_service"
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.record_id", record_id)
            
            return jsonify(result)
            
        except Exception as e:
            storage_stats["errors"] += 1
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "service": "storage_service",
                "timestamp": datetime.now().isoformat()
            }), 500
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics with database metrics."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("storage_service.get_stats") as span:
        span.set_attribute("service.component", "storage_service")
        
        # Update database size
        storage_stats["database_size_mb"] = get_database_size()
        
        # Get additional database metrics
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM feedback")
            feedback_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM processing_insights")
            insights_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM query_analytics")
            analytics_count = cursor.fetchone()[0]
            
            conn.close()
            
            enhanced_stats = dict(storage_stats)
            enhanced_stats.update({
                "database_records": {
                    "feedback": feedback_count,
                    "processing_insights": insights_count,
                    "query_analytics": analytics_count
                }
            })
            
            span.set_attribute("database.total_records", feedback_count + insights_count + analytics_count)
            
        except Exception as e:
            enhanced_stats = dict(storage_stats)
            enhanced_stats["database_error"] = str(e)
        
        return jsonify({
            "service": "storage_service",
            "stats": enhanced_stats,
            "timestamp": datetime.now().isoformat()
        })

if __name__ == '__main__':
    if not telemetry_enabled:
        print("⚠️ WARNING: Telemetry initialization failed - SQLite operations may not be traced")
    
    # Initialize database
    if not initialize_database():
        print("❌ Failed to initialize database. Exiting.")
        exit(1)
    
    print("💾 Storage Service starting on port 8015...")
    print(f"   Database: {DB_FILE}")
    print(f"   SQLite instrumentation: {'✅ Active' if telemetry_enabled else '❌ Failed'}")
    app.run(host='0.0.0.0', port=8015, debug=False)