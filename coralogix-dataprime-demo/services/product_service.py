#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Product Service - E-commerce Product Catalog with PostgreSQL

Provides product query endpoints with full OpenTelemetry instrumentation:
- Histogram metrics for query duration (Coralogix calculates P95/P99)
- Connection pool tracking
- Active query counting
- Failure simulation endpoints for demo
"""

import os
import sys
import time
import threading
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, metrics, context
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry BEFORE importing psycopg2 (for auto-instrumentation)
telemetry_enabled = ensure_telemetry_initialized()

# NOW import db_connection (which imports psycopg2)
from app.db_connection import (
    get_connection, 
    return_connection, 
    get_db_pool, 
    get_pool_stats
)

# Initialize OpenTelemetry
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Initialize structured logger (configured by shared_telemetry)
logger = logging.getLogger(__name__)

def extract_and_attach_trace_context():
    """
    Extract trace context from incoming request and attach it.
    This ensures our spans are children of the calling service's span.
    CRITICAL for PostgreSQL spans to appear in traces!
    """
    try:
        headers = dict(request.headers)
        
        # Try standard propagation first
        propagator = TraceContextTextMapPropagator()
        incoming_context = propagator.extract(headers)
        
        traceparent_found = any(key.lower() == 'traceparent' for key in headers.keys())
        manual_trace_id = None
        manual_span_id = None
        
        if traceparent_found:
            for key, value in headers.items():
                if key.lower() == 'traceparent':
                    parts = value.split('-')
                    if len(parts) == 4 and parts[0] == '00':
                        manual_trace_id = parts[1]
                        manual_span_id = parts[2]
                        print(f"🔧 Product Service - Manually parsed trace_id: {manual_trace_id}")
                        break
        
        # Check if standard propagation worked
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                print(f"✅ Product Service - Attached to incoming trace context")
                print(f"   Parent trace ID: {manual_trace_id}")
                return token, False  # Not a root span
            else:
                print("⚠️ Product Service - Context extraction didn't create active span")
                context.detach(token)
        
        # If standard propagation didn't work, create context manually
        if manual_trace_id and manual_span_id:
            print(f"🔧 Product Service - Creating manual trace context")
            from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
            
            # Convert hex IDs to integers
            trace_id_int = int(manual_trace_id, 16)
            span_id_int = int(manual_span_id, 16)
            
            # Create parent span context
            parent_context = SpanContext(
                trace_id=trace_id_int,
                span_id=span_id_int,
                is_remote=True,
                trace_flags=TraceFlags(0x01)  # Sampled
            )
            
            # Create a non-recording span with the parent context
            parent_span = NonRecordingSpan(parent_context)
            
            # Set this as the current span
            ctx = trace.set_span_in_context(parent_span)
            token = context.attach(ctx)
            
            print(f"✅ Product Service - Manual trace context attached")
            print(f"   Trace ID: {manual_trace_id}")
            print(f"   Parent Span ID: {manual_span_id}")
            return token, False  # Not a root span
        
        # No trace context found - this will be a root span
        print("⚠️ Product Service - No trace context found, creating root span")
        return None, True
        
    except Exception as e:
        print(f"❌ Product Service - Error extracting trace context: {e}")
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        return None, True

# Initialize Flask app
app = Flask(__name__)

# Enable CORS for frontend access (allow demo endpoints from HTTPS frontend)
CORS(app, resources={r"/*": {"origins": "*"}})

# Metrics - Coralogix calculates P95/P99 from histograms
db_query_duration_histogram = meter.create_histogram(
    "db.query.duration_ms",
    description="Database query duration in milliseconds",
    unit="ms"
)

db_active_queries_gauge = meter.create_up_down_counter(
    "db.active_queries",
    description="Number of currently executing database queries",
    unit="queries"
)

db_pool_active_gauge = meter.create_up_down_counter(
    "db.connection_pool.active",
    description="Active connections in pool",
    unit="connections"
)

db_pool_utilization_histogram = meter.create_histogram(
    "db.connection_pool.utilization_percent",
    description="Connection pool utilization percentage",
    unit="%"
)

# Global counter for active queries (Scene 9: 43 active queries)
active_queries_count = 0
active_queries_lock = threading.Lock()

# Failure simulation state
SIMULATE_SLOW_QUERIES = False
QUERY_DELAY_MS = 0
held_connections = []  # For pool exhaustion simulation


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with pool status."""
    pool_stats = get_pool_stats()
    
    return jsonify({
        "status": "healthy",
        "service": "product_service",
        "database": {
            "connected": True,
            "pool_stats": pool_stats
        },
        "timestamp": datetime.now().isoformat()
    })


@app.route('/products', methods=['GET'])
def get_products():
    """
    Query products from database with full telemetry.
    
    Query params:
        category: Product category (required)
        price_min: Minimum price (required)
        price_max: Maximum price (required)
    """
    global active_queries_count
    
    # CRITICAL: Extract and attach trace context from incoming request
    # This ensures PostgreSQL spans appear in the parent trace!
    token, is_root = extract_and_attach_trace_context()
    
    with tracer.start_as_current_span("get_products_from_db") as span:
        # Increment active queries counter
        with active_queries_lock:
            active_queries_count += 1
            db_active_queries_gauge.add(1)
        
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.active_queries", active_queries_count)
        
        # Get query parameters
        category = request.args.get('category')
        price_min = request.args.get('price_min', type=float)
        price_max = request.args.get('price_max', type=float)
        
        if not all([category, price_min is not None, price_max is not None]):
            span.set_attribute("error", "Missing required parameters")
            with active_queries_lock:
                active_queries_count -= 1
                db_active_queries_gauge.add(-1)
            return jsonify({"error": "Missing required parameters: category, price_min, price_max"}), 400
        
        span.set_attribute("query.category", category)
        span.set_attribute("query.price_min", price_min)
        span.set_attribute("query.price_max", price_max)
        
        query_start = time.time()
        conn = None
        
        try:
            # Get connection from pool
            conn = get_connection()
            
            # Track pool metrics
            pool = get_db_pool()
            pool_stats = get_pool_stats()
            pool_active = pool_stats["active_connections"]
            pool_max = pool_stats["max_connections"]
            utilization = pool_stats["utilization_percent"]
            
            db_pool_active_gauge.add(1)
            db_pool_utilization_histogram.record(utilization, {
                "pool": "product_db"
            })
            
            span.set_attribute("db.connection_pool.active", pool_active)
            span.set_attribute("db.connection_pool.max", pool_max)
            span.set_attribute("db.connection_pool.utilization_percent", utilization)
            
            # Simulate slow queries for demo (Scene 9: 2800ms - 2950ms)
            if SIMULATE_SLOW_QUERIES:
                time.sleep(QUERY_DELAY_MS / 1000.0)
                span.set_attribute("db.simulation.slow_query_enabled", True)
                span.set_attribute("db.simulation.delay_ms", QUERY_DELAY_MS)
            
            # Execute query with explicit database span following OTel conventions
            # CRITICAL: Use SpanKind.CLIENT and proper naming for Coralogix Database Monitoring
            db_name = os.getenv("DB_NAME", "productcatalog")
            with tracer.start_as_current_span(
                f"SELECT {db_name}.products",  # OTel convention: "OPERATION database.table"
                kind=SpanKind.CLIENT  # REQUIRED for Coralogix Database Monitoring
            ) as db_span:
                # Set REQUIRED OpenTelemetry database semantic conventions
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.name", db_name)  # Database name
                db_span.set_attribute("db.operation", "SELECT")
                db_span.set_attribute("db.sql.table", "products")  # Use db.sql.table (not db.table)
                db_span.set_attribute("db.statement", "SELECT id, name, category, price, description, image_url, stock_quantity FROM products WHERE category = %s AND price BETWEEN %s AND %s ORDER BY price ASC LIMIT 10")
                db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))  # REQUIRED for DB Monitoring
                db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
                db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
                db_span.set_attribute("db.query.category", category)
                db_span.set_attribute("db.query.price_range", f"{price_min}-{price_max}")
                
                # Add database operation event
                db_span.add_event("Starting PostgreSQL SELECT operation", {
                    "table": "products",
                    "operation": "SELECT",
                    "filters": f"category={category}, price={price_min}-{price_max}"
                })
                
                cursor = conn.cursor()
                query = """
                    SELECT id, name, category, price, description, image_url, stock_quantity
                    FROM products
                    WHERE category = %s AND price BETWEEN %s AND %s
                    ORDER BY price ASC
                    LIMIT 10
                """
                
                db_query_start = time.time()
                cursor.execute(query, (category, price_min, price_max))
                results = cursor.fetchall()
                db_query_duration_ms = (time.time() - db_query_start) * 1000
                
                db_span.set_attribute("db.query.duration_ms", db_query_duration_ms)
                db_span.set_attribute("db.rows_returned", len(results))
                db_span.set_attribute("db.rows_examined", len(results))
                
                db_span.add_event("PostgreSQL SELECT completed successfully", {
                    "rows_returned": len(results),
                    "duration_ms": round(db_query_duration_ms, 2)
                })
            
            # Calculate duration and record to histogram
            # Coralogix will calculate P95/P99 from these measurements
            query_duration_ms = (time.time() - query_start) * 1000
            
            db_query_duration_histogram.record(query_duration_ms, {
                "query_type": "get_products",
                "category": category
            })
            
            span.set_attribute("db.query_duration_ms", query_duration_ms)
            span.set_attribute("db.results_count", len(results))
            span.set_attribute("db.query.success", True)
            
            # Format results
            products = [
                {
                    "id": row[0],
                    "name": row[1],
                    "category": row[2],
                    "price": float(row[3]),
                    "description": row[4],
                    "image_url": row[5],
                    "stock_quantity": row[6]
                }
                for row in results
            ]
            
            return jsonify({"products": products})
            
        except Exception as e:
            error_msg = str(e)
            span.set_attribute("db.error", error_msg)
            span.set_attribute("db.query.success", False)
            span.record_exception(e)
            
            # Return 503 for connection errors (Scene 10)
            if "ConnectionError" in error_msg or "Could not acquire connection" in error_msg:
                return jsonify({"error": error_msg}), 503
            
            return jsonify({"error": error_msg}), 500
            
        finally:
            # Always decrement counters
            with active_queries_lock:
                active_queries_count -= 1
                db_active_queries_gauge.add(-1)
            
            if conn:
                db_pool_active_gauge.add(-1)
                return_connection(conn)
            
            # Detach trace context
            if token:
                context.detach(token)


@app.route('/products/search', methods=['GET'])
def search_products_unindexed():
    """
    UNINDEXED search - demonstrates profiling catching slow queries.
    Uses LIKE '%term%' on description field without index.
    Shows in flame graph as search_products_unindexed() consuming 99.2% CPU.
    
    This endpoint is specifically for Scene 9.5: Continuous Profiling demo.
    
    Query params:
        q: Search term to find in product descriptions
    """
    global active_queries_count
    
    # Extract trace context from incoming request
    propagator = TraceContextTextMapPropagator()
    ctx = propagator.extract(dict(request.headers))
    
    with tracer.start_as_current_span("search_products_unindexed", context=ctx) as span:
        # Increment active queries counter
        with active_queries_lock:
            active_queries_count += 1
            db_active_queries_gauge.add(1)
        
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.active_queries", active_queries_count)
        span.set_attribute("performance.issue", "unindexed_search")
        span.set_attribute("performance.optimization_needed", True)
        
        # Get search parameter
        search_term = request.args.get('q', '').strip()
        
        if not search_term:
            span.set_attribute("error", "Missing search term")
            with active_queries_lock:
                active_queries_count -= 1
                db_active_queries_gauge.add(-1)
            return jsonify({"error": "Missing required parameter: q"}), 400
        
        span.set_attribute("query.search_term", search_term)
        
        query_start = time.time()
        conn = None
        
        try:
            # Get connection from pool
            conn = get_connection()
            
            # Track pool metrics
            pool_stats = get_pool_stats()
            pool_active = pool_stats["active_connections"]
            utilization = pool_stats["utilization_percent"]
            
            db_pool_active_gauge.add(1)
            db_pool_utilization_histogram.record(utilization, {
                "pool": "product_db"
            })
            
            span.set_attribute("db.connection_pool.active", pool_active)
            span.set_attribute("db.connection_pool.utilization_percent", utilization)
            
            # UNINDEXED query - full table scan on description field
            # Use SpanKind.CLIENT for Coralogix Database Monitoring
            db_name = os.getenv("DB_NAME", "productcatalog")
            with tracer.start_as_current_span(
                f"SELECT {db_name}.products",  # OTel convention: "OPERATION database.table"
                kind=SpanKind.CLIENT  # REQUIRED for Coralogix Database Monitoring
            ) as db_span:
                # Set REQUIRED OpenTelemetry database semantic conventions
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.name", db_name)
                db_span.set_attribute("db.operation", "SELECT")
                db_span.set_attribute("db.sql.table", "products")
                db_span.set_attribute("db.statement", "SELECT id, name, category, price, description, image_url, stock_quantity FROM products WHERE description LIKE %s")
                db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))
                db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
                db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
                db_span.set_attribute("db.query.search_term", search_term)
                
                # Key indicators for profiling (Scene 9.5)
                db_span.set_attribute("db.index_used", False)  # No index!
                db_span.set_attribute("db.full_table_scan", True)  # Performance warning
                db_span.set_attribute("performance.issue", "missing_index_on_description")
                
                # Add database operation event
                db_span.add_event("Starting UNINDEXED PostgreSQL SELECT operation", {
                    "table": "products",
                    "operation": "SELECT",
                    "warning": "Full table scan - no index on description field",
                    "search_term": search_term
                })
                
                cursor = conn.cursor()
                query = """
                    SELECT id, name, category, price, description, image_url, stock_quantity
                    FROM products
                    WHERE description LIKE %s
                """
                
                db_query_start = time.time()
                cursor.execute(query, (f'%{search_term}%',))
                results = cursor.fetchall()
                db_query_duration_ms = (time.time() - db_query_start) * 1000
                
                db_span.set_attribute("db.query.duration_ms", db_query_duration_ms)
                db_span.set_attribute("db.rows_returned", len(results))
                db_span.set_attribute("db.rows_examined", len(results))
                
                db_span.add_event("UNINDEXED PostgreSQL SELECT completed", {
                    "rows_returned": len(results),
                    "duration_ms": round(db_query_duration_ms, 2),
                    "warning": "Consider adding index on description column"
                })
            
            # Calculate duration and record to histogram
            query_duration_ms = (time.time() - query_start) * 1000
            
            db_query_duration_histogram.record(query_duration_ms, {
                "query_type": "unindexed_search",
                "search_term": search_term[:20]  # Truncate for cardinality
            })
            
            span.set_attribute("db.query_duration_ms", query_duration_ms)
            span.set_attribute("db.results_count", len(results))
            span.set_attribute("db.query.success", True)
            
            # Format results
            products = [
                {
                    "id": row[0],
                    "name": row[1],
                    "category": row[2],
                    "price": float(row[3]),
                    "description": row[4],
                    "image_url": row[5],
                    "stock_quantity": row[6]
                }
                for row in results
            ]
            
            return jsonify({
                "products": products,
                "performance_warning": "Unindexed query - consider adding index on description field",
                "query_duration_ms": round(query_duration_ms, 2)
            })
            
        except Exception as e:
            error_msg = str(e)
            span.set_attribute("db.error", error_msg)
            span.set_attribute("db.query.success", False)
            span.record_exception(e)
            
            # Return 503 for connection errors
            if "ConnectionError" in error_msg or "Could not acquire connection" in error_msg:
                return jsonify({"error": error_msg}), 503
            
            return jsonify({"error": error_msg}), 500
            
        finally:
            # Always decrement counters
            with active_queries_lock:
                active_queries_count -= 1
                db_active_queries_gauge.add(-1)
            
            if conn:
                db_pool_active_gauge.add(-1)
                return_connection(conn)


@app.route('/admin/simulate-slow-queries', methods=['POST'])
def simulate_slow_queries():
    """
    Admin endpoint to inject query delays (Scene 9: 2800ms).
    
    Request body:
        {
            "duration_ms": 2800  // Optional, defaults to 2800
        }
    """
    global SIMULATE_SLOW_QUERIES, QUERY_DELAY_MS
    
    data = request.get_json() or {}
    QUERY_DELAY_MS = data.get("duration_ms", 2800)  # Default to demo value
    SIMULATE_SLOW_QUERIES = True
    
    logger.info("Slow query simulation enabled", extra={
        "delay_ms": QUERY_DELAY_MS,
        "target_p95": "2800ms",
        "target_p99": "3200ms",
        "simulation_type": "database_performance"
    })
    
    return jsonify({
        "message": f"Slow query simulation enabled: {QUERY_DELAY_MS}ms delay",
        "target_p95": "2800ms",
        "target_p99": "3200ms",
        "simulation_active": True
    })


@app.route('/admin/disable-slow-queries', methods=['POST'])
def disable_slow_queries():
    """Disable slow query simulation."""
    global SIMULATE_SLOW_QUERIES
    
    SIMULATE_SLOW_QUERIES = False
    logger.info("Slow query simulation disabled", extra={
        "simulation_type": "database_performance",
        "action": "reset"
    })
    
    return jsonify({
        "message": "Slow query simulation disabled",
        "simulation_active": False
    })


@app.route('/admin/simulate-pool-exhaustion', methods=['POST'])
def simulate_pool_exhaustion():
    """
    Admin endpoint to exhaust connection pool (Scene 10: 237 errors).
    
    Holds 95+ connections to simulate pool exhaustion.
    """
    global held_connections
    
    # Release any previously held connections
    for conn in held_connections:
        try:
            return_connection(conn)
        except:
            pass
    held_connections = []
    
    # Hold 95+ connections (pool max = 100)
    target_connections = 95
    for i in range(target_connections):
        try:
            conn = get_connection()
            held_connections.append(conn)
        except Exception as e:
            logger.error("Could not acquire connection for pool exhaustion", extra={
                "connection_number": i + 1,
                "target_connections": target_connections,
                "error": str(e),
                "simulation_type": "pool_exhaustion"
            })
            break
    
    actual_held = len(held_connections)
    pool_stats = get_pool_stats()
    
    logger.warning("Connection pool exhaustion simulated", extra={
        "connections_held": actual_held,
        "pool_max": pool_stats["max_connections"],
        "available_connections": pool_stats["available_connections"],
        "utilization_percent": pool_stats["utilization_percent"],
        "simulation_type": "pool_exhaustion"
    })
    
    return jsonify({
        "message": "Connection pool exhaustion simulated",
        "connections_held": actual_held,
        "pool_max": pool_stats["max_connections"],
        "available": pool_stats["available_connections"],
        "simulation_active": True
    })


@app.route('/admin/release-connections', methods=['POST'])
def release_held_connections():
    """Release connections held for pool exhaustion simulation."""
    global held_connections
    
    released_count = 0
    for conn in held_connections:
        try:
            return_connection(conn)
            released_count += 1
        except Exception as e:
            logger.error("Error releasing held connection", extra={
                "error": str(e),
                "simulation_type": "pool_exhaustion"
            })
    
    held_connections = []
    pool_stats = get_pool_stats()
    
    logger.info("Released held connections", extra={
        "connections_released": released_count,
        "pool_stats": pool_stats,
        "simulation_type": "pool_exhaustion",
        "action": "reset"
    })
    
    return jsonify({
        "message": f"Released {released_count} held connections",
        "pool_stats": pool_stats,
        "simulation_active": False
    })


@app.route('/admin/pool-stats', methods=['GET'])
def get_pool_statistics():
    """Get current connection pool statistics."""
    pool_stats = get_pool_stats()
    
    return jsonify({
        "pool_stats": pool_stats,
        "simulation": {
            "slow_queries_enabled": SIMULATE_SLOW_QUERIES,
            "query_delay_ms": QUERY_DELAY_MS,
            "held_connections": len(held_connections)
        },
        "active_queries": active_queries_count,
        "timestamp": datetime.now().isoformat()
    })


# New /demo/* endpoints (replacing /admin/* for better semantics)
@app.route('/demo/enable-slow-queries', methods=['POST'])
def demo_enable_slow_queries():
    """
    Demo endpoint to enable slow query simulation.
    Alias for /admin/simulate-slow-queries with better naming.
    """
    return simulate_slow_queries()


@app.route('/demo/enable-pool-exhaustion', methods=['POST'])
def demo_enable_pool_exhaustion():
    """
    Demo endpoint to enable pool exhaustion simulation.
    Alias for /admin/simulate-pool-exhaustion with better naming.
    """
    return simulate_pool_exhaustion()


@app.route('/demo/reset', methods=['POST'])
def demo_reset():
    """
    Demo endpoint to reset all simulations.
    Disables slow queries and releases held connections.
    """
    global SIMULATE_SLOW_QUERIES, held_connections
    
    # Disable slow queries
    SIMULATE_SLOW_QUERIES = False
    
    # Release held connections
    released_count = 0
    for conn in held_connections:
        try:
            return_connection(conn)
            released_count += 1
        except Exception as e:
            logger.error("Error releasing connection during demo reset", extra={
                "error": str(e),
                "simulation_type": "demo_reset"
            })
    
    held_connections = []
    
    logger.info("Demo simulations reset", extra={
        "slow_queries_disabled": True,
        "connections_released": released_count,
        "simulation_type": "demo_reset"
    })
    
    return jsonify({
        "message": "Demo simulations reset",
        "slow_queries_disabled": True,
        "connections_released": released_count,
        "simulation_active": False,
        "timestamp": datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("🛍️ Product Service (E-commerce) starting on port 8014...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Database: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    print(f"   Connection pool max: {os.getenv('DB_MAX_CONNECTIONS', '100')}")
    app.run(host='0.0.0.0', port=8014, debug=False)


