#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Inventory Service - E-commerce Stock Management with PostgreSQL
Manual OpenTelemetry instrumentation for reliable distributed tracing.
USES EXACT SAME PATTERN AS product_service.py
"""

import os
import sys
import time
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry BEFORE importing psycopg2 (for auto-instrumentation)
telemetry_enabled = ensure_telemetry_initialized()

# NOW import psycopg2 AFTER instrumentation is initialized
import psycopg2
from psycopg2 import pool

# Initialize tracer
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# Global connection pool
_db_pool = None

# Demo simulation state
SIMULATE_SLOW_QUERIES = False
QUERY_DELAY_MS = 0
held_connections = []

# Service stats
inventory_stats = {
    "queries": 0,
    "stock_checks": 0,
    "reservations": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def initialize_db_pool():
    """Initialize PostgreSQL connection pool with max=100 connections."""
    global _db_pool
    if _db_pool is not None:
        print("✅ Database pool already initialized")
        return _db_pool
    
    try:
        _db_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=5,
            maxconn=int(os.getenv("DB_MAX_CONNECTIONS", "100")),
            host=os.getenv("DB_HOST", "postgres"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "productcatalog"),
            user=os.getenv("DB_USER", "dbadmin"),
            password=os.getenv("DB_PASSWORD", "postgres_secure_pass_2024"),
            connect_timeout=3
        )
        
        print(f"✅ PostgreSQL pool initialized: min=5, max={os.getenv('DB_MAX_CONNECTIONS', '100')}")
        return _db_pool
        
    except Exception as e:
        print(f"❌ Failed to initialize database pool: {e}")
        raise

def get_connection():
    """Get connection from pool."""
    pool_instance = _db_pool or initialize_db_pool()
    try:
        conn = pool_instance.getconn()
        if conn is None:
            raise Exception("ConnectionError: Could not acquire connection within 3000ms")
        return conn
    except psycopg2.pool.PoolError as e:
        print(f"❌ Pool error: {e}")
        raise Exception("ConnectionError: Could not acquire connection within 3000ms")

def return_connection(conn):
    """Return connection to pool."""
    if conn and _db_pool:
        try:
            _db_pool.putconn(conn)
        except Exception as e:
            print(f"❌ Error returning connection: {e}")

def get_pool_stats():
    """Get connection pool statistics."""
    try:
        pool_instance = _db_pool or initialize_db_pool()
        active = len([c for c in pool_instance._used.values() if c is not None])
        max_conn = pool_instance.maxconn
        return {
            "active_connections": active,
            "max_connections": max_conn,
            "utilization_percent": round((active / max_conn * 100), 2),
            "available_connections": max_conn - active
        }
    except Exception as e:
        print(f"❌ Error getting pool stats: {e}")
        return {
            "active_connections": 0,
            "max_connections": 100,
            "utilization_percent": 0,
            "available_connections": 100
        }

def extract_and_attach_trace_context():
    """
    Extract trace context from incoming request and attach it.
    This ensures our spans are children of the calling service's span.
    PROVEN PATTERN from working product_service.py.
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
                        print(f"🔧 Inventory Service - Manually parsed trace_id: {manual_trace_id}")
                        break
        
        # Check if standard propagation worked
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = format(current_span.get_span_context().trace_id, '032x')
                print(f"✅ Inventory Service - Joined via propagator: {trace_id}")
                return token, False  # False = not root
            else:
                context.detach(token)
        
        # Fall back to manual trace creation
        if manual_trace_id and manual_span_id:
            from opentelemetry.trace import TraceFlags, SpanContext
            
            try:
                trace_id_int = int(manual_trace_id, 16)
                span_id_int = int(manual_span_id, 16)
                
                span_ctx = SpanContext(
                    trace_id=trace_id_int,
                    span_id=span_id_int,
                    is_remote=True,
                    trace_flags=TraceFlags(0x01)
                )
                
                manual_context = trace.set_span_in_context(trace.NonRecordingSpan(span_ctx))
                token = context.attach(manual_context)
                
                print(f"✅ Inventory Service - Manually joined trace: {manual_trace_id}")
                return token, False
                
            except Exception as e:
                print(f"⚠️ Manual trace join failed: {e}")
                return None, True
        
        print("⚠️ Inventory Service - Starting root trace (no parent)")
        return None, True
        
    except Exception as e:
        print(f"⚠️ Trace context extraction failed: {e}")
        return None, True

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with pool status."""
    pool_stats = get_pool_stats()
    
    return jsonify({
        "service": "inventory-service",
        "status": "healthy",
        "database": "postgresql",
        "connection_pool": pool_stats,
        "telemetry_enabled": telemetry_enabled,
        "queries_processed": inventory_stats["queries"],
        "stock_checks": inventory_stats["stock_checks"],
        "reservations": inventory_stats["reservations"],
        "uptime_seconds": (datetime.now() - inventory_stats["start_time"]).total_seconds(),
        "demo_mode": {
            "slow_queries_enabled": SIMULATE_SLOW_QUERIES,
            "delay_ms": QUERY_DELAY_MS,
            "held_connections": len(held_connections)
        }
    }), 200

@app.route('/inventory/check/<int:product_id>', methods=['GET'])
def check_stock(product_id):
    """Check stock quantity for a specific product with proper trace context."""
    token = None
    conn = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        # Start main span
        with tracer.start_as_current_span("inventory_service.check_stock") as main_span:
            main_span.set_attribute("service.component", "inventory_service")
            main_span.set_attribute("service.name", "inventory-service")
            main_span.set_attribute("db.system", "postgresql")
            main_span.set_attribute("inventory.product_id", product_id)
            
            print(f"🔍 Checking stock for product: {product_id}")
            
            # Get connection from pool
            conn = get_connection()
            
            # Track pool metrics in main span
            pool_stats = get_pool_stats()
            main_span.set_attribute("db.connection_pool.active", pool_stats["active_connections"])
            main_span.set_attribute("db.connection_pool.max", pool_stats["max_connections"])
            main_span.set_attribute("db.connection_pool.utilization_percent", pool_stats["utilization_percent"])
            
            # Manual database query span with SpanKind.CLIENT for Coralogix DB Monitoring
            db_name = os.getenv("DB_NAME", "productcatalog")
            with tracer.start_as_current_span(
                f"SELECT {db_name}.products",  # OTel convention
                kind=SpanKind.CLIENT  # REQUIRED
            ) as db_span:
                # REQUIRED OpenTelemetry database semantic conventions
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.name", db_name)
                db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))
                db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
                db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
                db_span.set_attribute("db.operation", "SELECT")
                db_span.set_attribute("db.table", "products")
                db_span.set_attribute("db.statement", "SELECT id, name, stock_quantity FROM products WHERE id = %s")
                db_span.set_attribute("service.name", "inventory-service")
                db_span.set_attribute("operation.type", "database_read")
                db_span.set_attribute("db.query.product_id", product_id)
                
                # Add database operation event
                db_span.add_event("Starting PostgreSQL SELECT operation", {
                    "table": "products",
                    "operation": "SELECT",
                    "product_id": product_id
                })
                
                # Simulate slow queries for demo
                if SIMULATE_SLOW_QUERIES:
                    time.sleep(QUERY_DELAY_MS / 1000.0)
                    db_span.set_attribute("db.simulation.slow_query_enabled", True)
                    db_span.set_attribute("db.simulation.delay_ms", QUERY_DELAY_MS)
                
                cursor = conn.cursor()
                query_start = time.time()
                
                cursor.execute("""
                    SELECT id, name, stock_quantity
                    FROM products
                    WHERE id = %s
                """, (product_id,))
                
                result = cursor.fetchone()
                query_duration_ms = (time.time() - query_start) * 1000
                
                db_span.set_attribute("db.query.duration_ms", query_duration_ms)
                db_span.set_attribute("db.rows_returned", 1 if result else 0)
                db_span.set_attribute("db.rows_examined", 1 if result else 0)
                
                db_span.add_event("PostgreSQL SELECT completed successfully", {
                    "rows_returned": 1 if result else 0,
                    "duration_ms": round(query_duration_ms, 2)
                })
            
            if not result:
                main_span.set_attribute("inventory.found", False)
                return jsonify({"error": "Product not found"}), 404
            
            product_data = {
                "product_id": result[0],
                "product_name": result[1],
                "stock_quantity": result[2],
                "in_stock": result[2] > 0
            }
            
            main_span.set_attribute("inventory.found", True)
            main_span.set_attribute("inventory.stock_quantity", result[2])
            main_span.set_attribute("inventory.in_stock", result[2] > 0)
            
            inventory_stats["queries"] += 1
            inventory_stats["stock_checks"] += 1
            
            print(f"✅ Stock for product {product_id}: {result[2]} units")
            
            return jsonify(product_data), 200
            
    except Exception as e:
        inventory_stats["errors"] += 1
        print(f"❌ Error in check_stock: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
        
    finally:
        if conn:
            return_connection(conn)
        if token:
            context.detach(token)

@app.route('/inventory/reserve', methods=['POST'])
def reserve_stock():
    """Reserve stock (decrease quantity) with proper trace context."""
    token = None
    conn = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        # Start main span
        with tracer.start_as_current_span("inventory_service.reserve_stock") as main_span:
            main_span.set_attribute("service.component", "inventory_service")
            main_span.set_attribute("service.name", "inventory-service")
            main_span.set_attribute("db.system", "postgresql")
            
            # Get request data
            data = request.get_json() or {}
            product_id = data.get("product_id")
            quantity = data.get("quantity", 1)
            
            if not product_id:
                return jsonify({"error": "product_id required"}), 400
            
            main_span.set_attribute("inventory.product_id", product_id)
            main_span.set_attribute("inventory.quantity_reserved", quantity)
            
            print(f"🔒 Reserving {quantity} units of product: {product_id}")
            
            # Get connection from pool
            conn = get_connection()
            
            # Track pool metrics in main span
            pool_stats = get_pool_stats()
            main_span.set_attribute("db.connection_pool.active", pool_stats["active_connections"])
            main_span.set_attribute("db.connection_pool.max", pool_stats["max_connections"])
            main_span.set_attribute("db.connection_pool.utilization_percent", pool_stats["utilization_percent"])
            
            # Manual database query span with SpanKind.CLIENT for Coralogix DB Monitoring
            db_name = os.getenv("DB_NAME", "productcatalog")
            with tracer.start_as_current_span(
                f"UPDATE {db_name}.products",  # OTel convention
                kind=SpanKind.CLIENT  # REQUIRED
            ) as db_span:
                # REQUIRED OpenTelemetry database semantic conventions
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.name", db_name)
                db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))
                db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
                db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
                db_span.set_attribute("db.operation", "UPDATE")
                db_span.set_attribute("db.table", "products")
                db_span.set_attribute("db.statement", "UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s AND stock_quantity >= %s RETURNING id, name, stock_quantity")
                db_span.set_attribute("service.name", "inventory-service")
                db_span.set_attribute("operation.type", "database_write")
                db_span.set_attribute("db.query.product_id", product_id)
                db_span.set_attribute("db.query.quantity", quantity)
                
                # Add database operation event
                db_span.add_event("Starting PostgreSQL UPDATE operation", {
                    "table": "products",
                    "operation": "UPDATE",
                    "product_id": product_id,
                    "quantity_to_reserve": quantity
                })
                
                # Simulate slow queries for demo
                if SIMULATE_SLOW_QUERIES:
                    time.sleep(QUERY_DELAY_MS / 1000.0)
                    db_span.set_attribute("db.simulation.slow_query_enabled", True)
                    db_span.set_attribute("db.simulation.delay_ms", QUERY_DELAY_MS)
                
                cursor = conn.cursor()
                query_start = time.time()
                
                cursor.execute("""
                    UPDATE products 
                    SET stock_quantity = stock_quantity - %s 
                    WHERE id = %s AND stock_quantity >= %s
                    RETURNING id, name, stock_quantity
                """, (quantity, product_id, quantity))
                
                result = cursor.fetchone()
                conn.commit()
                query_duration_ms = (time.time() - query_start) * 1000
                
                db_span.set_attribute("db.query.duration_ms", query_duration_ms)
                db_span.set_attribute("db.rows_affected", 1 if result else 0)
                
                db_span.add_event("PostgreSQL UPDATE completed successfully", {
                    "rows_affected": 1 if result else 0,
                    "duration_ms": round(query_duration_ms, 2)
                })
            
            if not result:
                main_span.set_attribute("inventory.reservation_success", False)
                return jsonify({
                    "error": "Insufficient stock or product not found",
                    "product_id": product_id,
                    "requested_quantity": quantity
                }), 400
            
            response_data = {
                "success": True,
                "product_id": result[0],
                "product_name": result[1],
                "remaining_stock": result[2],
                "reserved_quantity": quantity
            }
            
            main_span.set_attribute("inventory.reservation_success", True)
            main_span.set_attribute("inventory.remaining_stock", result[2])
            
            inventory_stats["queries"] += 1
            inventory_stats["reservations"] += 1
            
            print(f"✅ Reserved {quantity} units of product {product_id}, {result[2]} units remaining")
            
            return jsonify(response_data), 200
            
    except Exception as e:
        if conn:
            conn.rollback()
        inventory_stats["errors"] += 1
        print(f"❌ Error in reserve_stock: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
        
    finally:
        if conn:
            return_connection(conn)
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    return jsonify({
        **inventory_stats,
        "pool_stats": get_pool_stats()
    }), 200

@app.route('/demo/enable-slow-queries', methods=['POST'])
def enable_slow_queries():
    """Enable slow query simulation (2800-2950ms delays)."""
    global SIMULATE_SLOW_QUERIES, QUERY_DELAY_MS
    data = request.get_json() or {}
    SIMULATE_SLOW_QUERIES = True
    QUERY_DELAY_MS = data.get("delay_ms", 2900)
    
    print(f"🐌 Slow query simulation ENABLED: {QUERY_DELAY_MS}ms delay")
    
    return jsonify({
        "status": "slow_queries_enabled",
        "delay_ms": QUERY_DELAY_MS
    }), 200

@app.route('/demo/simulate-pool-exhaustion', methods=['POST'])
def simulate_pool_exhaustion():
    """Hold 95 connections to simulate pool exhaustion."""
    global held_connections
    
    try:
        held_connections = []
        for i in range(95):
            conn = get_connection()
            held_connections.append(conn)
        
        pool_stats = get_pool_stats()
        
        print(f"💥 Pool exhaustion simulation ACTIVE: {len(held_connections)} connections held")
        
        return jsonify({
            "status": "pool_exhausted",
            "held_connections": len(held_connections),
            "pool_stats": pool_stats
        }), 200
        
    except Exception as e:
        print(f"❌ Pool exhaustion simulation failed: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/demo/reset', methods=['POST'])
def reset_demo():
    """Reset all demo simulations."""
    global SIMULATE_SLOW_QUERIES, QUERY_DELAY_MS, held_connections
    
    # Release held connections
    for conn in held_connections:
        return_connection(conn)
    
    connection_count = len(held_connections)
    held_connections = []
    
    SIMULATE_SLOW_QUERIES = False
    QUERY_DELAY_MS = 0
    
    print(f"♻️ Demo reset: Released {connection_count} connections, disabled slow queries")
    
    return jsonify({
        "status": "demo_reset",
        "released_connections": connection_count,
        "pool_stats": get_pool_stats()
    }), 200

if __name__ == '__main__':
    print("📦 Inventory Service (E-commerce - PostgreSQL) starting...")
    print(f"   Database: PostgreSQL")
    print(f"   Host: {os.getenv('DB_HOST', 'postgres')}")
    print(f"   Max connections: {os.getenv('DB_MAX_CONNECTIONS', '100')}")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    
    # Initialize connection pool
    try:
        initialize_db_pool()
    except Exception as e:
        print(f"❌ Failed to initialize connection pool: {e}")
        sys.exit(1)
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8015, debug=False)

