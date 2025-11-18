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
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, metrics, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized
from app.db_connection import (
    get_connection, 
    return_connection, 
    get_db_pool, 
    get_pool_stats
)

# Initialize telemetry for this service
telemetry_enabled = ensure_telemetry_initialized()

# Initialize OpenTelemetry
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Initialize Flask app
app = Flask(__name__)

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
    
    # Extract trace context from incoming request
    propagator = TraceContextTextMapPropagator()
    ctx = propagator.extract(dict(request.headers))
    
    with tracer.start_as_current_span("get_products_from_db", context=ctx) as span:
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
            
            # Execute query with explicit database span for AI Center visibility
            # Use trace.use_span to ensure proper parent linkage
            with trace.use_span(span, end_on_exit=False):
                with tracer.start_as_current_span("db.query.select_products") as db_span:
                    db_span.set_attribute("db.system", "postgresql")
                    db_span.set_attribute("db.operation", "SELECT")
                    db_span.set_attribute("db.table", "products")
                    db_span.set_attribute("db.statement", "SELECT id, name, category, price, description, image_url, stock_quantity FROM products WHERE category = %s AND price BETWEEN %s AND %s ORDER BY price ASC LIMIT 10")
                    db_span.set_attribute("db.query.category", category)
                    db_span.set_attribute("db.query.price_range", f"{price_min}-{price_max}")
                    
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
    
    print(f"🐌 Slow query simulation enabled: {QUERY_DELAY_MS}ms delay")
    
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
    print("✅ Slow query simulation disabled")
    
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
            print(f"⚠️ Could not acquire connection {i+1}: {e}")
            break
    
    actual_held = len(held_connections)
    pool_stats = get_pool_stats()
    
    print(f"🔒 Pool exhaustion simulated: holding {actual_held} connections")
    
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
            print(f"⚠️ Error releasing connection: {e}")
    
    held_connections = []
    pool_stats = get_pool_stats()
    
    print(f"✅ Released {released_count} held connections")
    
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


if __name__ == '__main__':
    print("🛍️ Product Service (E-commerce) starting on port 8014...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Database: {os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
    print(f"   Connection pool max: {os.getenv('DB_MAX_CONNECTIONS', '100')}")
    app.run(host='0.0.0.0', port=8014, debug=False)


