#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Checkout Service - E-commerce Checkout and Payment Processing with PostgreSQL
Manual OpenTelemetry instrumentation for reliable distributed tracing.
USES EXACT SAME PATTERN AS product_catalog_service.py
"""

import os
import sys
import time
import random
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
import structlog

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized
from app.shared_span_attributes import (
    DemoSpanAttributes,
    calculate_demo_minute,
    is_demo_mode,
    get_demo_phase
)

# Configure structured logging for demo
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

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
order_stats = {
    "queries": 0,
    "orders_created": 0,
    "popularity_checks": 0,
    "errors": 0,
    "start_time": datetime.now()
}


class ConnectionPoolSimulator:
    """
    Simulates connection pool exhaustion during Black Friday demo.
    Uses Unix timestamp for accurate timing synchronization.
    """
    
    def __init__(self):
        self.max_connections = int(os.getenv('DB_MAX_CONNECTIONS', '20'))
        self.rejected_count = 0
    
    def should_fail_connection(self, span, order_data=None):
        """
        Determine if connection should fail based on demo progression.
        
        Progressive failure rates:
        - Minutes 0-15: 0% (normal operations)
        - Minute 16: 5% (pool strain starting)
        - Minute 17: 10% (increasing failures)
        - Minute 18: 15% (noticeable impact)
        - Minute 19: 20% (significant issues)
        - Minute 20+: 35% (critical failure rate)
        """
        if not is_demo_mode():
            return False
        
        demo_minute = calculate_demo_minute()
        phase = get_demo_phase(demo_minute)
        
        # No failures before degradation phase
        if demo_minute < 15:
            return False
        
        # Calculate progressive failure rate
        failure_rate = min(0.35, (demo_minute - 15) * 0.05)
        
        if random.random() < failure_rate:
            self.rejected_count += 1
            
            # Use shared attributes for Flow Alert consistency
            DemoSpanAttributes.set_pool_exhausted(
                span,
                max_conn=self.max_connections,
                wait_ms=5000,
                rejected_count=self.rejected_count
            )
            
            # Checkout failure attributes if order data provided
            if order_data:
                DemoSpanAttributes.set_checkout_failed(
                    span,
                    order_id=order_data.get('order_id', 'unknown'),
                    user_id=order_data.get('user_id', 'unknown'),
                    total=order_data.get('total', 0),
                    failure_reason="ConnectionPoolExhausted"
                )
            
            # Additional context
            span.set_attribute("demo.minute", demo_minute)
            span.set_attribute("service.demo_phase", phase)
            span.set_attribute("demo.failure_rate", failure_rate)
            span.set_attribute("error.type", "ConnectionPoolExhausted")
            span.set_status(Status(StatusCode.ERROR))
            
            return True
        
        return False


# Global simulator instance
pool_simulator = ConnectionPoolSimulator()

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
                        print(f"🔧 Checkout Service - Manually parsed trace_id: {manual_trace_id}")
                        break
        
        # Check if standard propagation worked
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = format(current_span.get_span_context().trace_id, '032x')
                print(f"✅ Checkout Service - Joined via propagator: {trace_id}")
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
                
                print(f"✅ Checkout Service - Manually joined trace: {manual_trace_id}")
                return token, False
                
            except Exception as e:
                print(f"⚠️ Manual trace join failed: {e}")
                return None, True
        
        print("⚠️ Checkout Service - Starting root trace (no parent)")
        return None, True
        
    except Exception as e:
        print(f"⚠️ Trace context extraction failed: {e}")
        return None, True

def initialize_orders_table():
    """Initialize orders table if it doesn't exist."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id VARCHAR(255) NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        conn.commit()
        print("✅ Orders table initialized")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing orders table: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if conn:
            return_connection(conn)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with pool status."""
    pool_stats = get_pool_stats()
    
    return jsonify({
        "service": "checkout-service",
        "status": "healthy",
        "database": "postgresql",
        "connection_pool": pool_stats,
        "telemetry_enabled": telemetry_enabled,
        "queries_processed": order_stats["queries"],
        "orders_created": order_stats["orders_created"],
        "popularity_checks": order_stats["popularity_checks"],
        "uptime_seconds": (datetime.now() - order_stats["start_time"]).total_seconds(),
        "demo_mode": {
            "slow_queries_enabled": SIMULATE_SLOW_QUERIES,
            "delay_ms": QUERY_DELAY_MS,
            "held_connections": len(held_connections)
        }
    }), 200

@app.route('/orders/popular-products', methods=['GET'])
def get_popular_products():
    """Get popular products based on order count with proper trace context."""
    token = None
    conn = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        # Start main span
        with tracer.start_as_current_span("checkout_service.get_popular_products") as main_span:
            main_span.set_attribute("service.component", "checkout_service")
            main_span.set_attribute("service.name", "checkout-service")
            main_span.set_attribute("db.system", "postgresql")
            
            # Get query parameters
            limit = int(request.args.get('limit', 10))
            main_span.set_attribute("query.limit", limit)
            
            print(f"🔍 Querying popular products (limit: {limit})")
            
            # Check for connection pool exhaustion (Black Friday demo)
            if pool_simulator.should_fail_connection(main_span):
                order_stats["errors"] += 1
                return jsonify({
                    "error": "SQLSTATE[08006]: Connection timeout after 5000ms"
                }), 503
            
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
                f"SELECT {db_name}.orders",  # OTel convention
                kind=SpanKind.CLIENT  # REQUIRED
            ) as db_span:
                # REQUIRED OpenTelemetry database semantic conventions
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.name", db_name)
                db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))
                db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
                db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
                db_span.set_attribute("db.operation", "SELECT")
                db_span.set_attribute("db.table", "orders")
                db_span.set_attribute("db.statement", "SELECT o.product_id, p.name, COUNT(*) as order_count FROM orders o JOIN products p ON o.product_id = p.id GROUP BY o.product_id, p.name ORDER BY order_count DESC LIMIT %s")
                db_span.set_attribute("service.name", "order-service")
                db_span.set_attribute("operation.type", "database_read")
                db_span.set_attribute("db.query.limit", limit)
                
                # Add database operation event
                db_span.add_event("Starting PostgreSQL SELECT operation", {
                    "table": "orders",
                    "operation": "SELECT",
                    "join_table": "products",
                    "limit": limit
                })
                
                # Simulate slow queries for demo
                if SIMULATE_SLOW_QUERIES:
                    time.sleep(QUERY_DELAY_MS / 1000.0)
                    db_span.set_attribute("db.simulation.slow_query_enabled", True)
                    db_span.set_attribute("db.simulation.delay_ms", QUERY_DELAY_MS)
                
                cursor = conn.cursor()
                query_start = time.time()
                
                cursor.execute("""
                    SELECT o.product_id, p.name, COUNT(*) as order_count
                    FROM orders o
                    JOIN products p ON o.product_id = p.id
                    GROUP BY o.product_id, p.name
                    ORDER BY order_count DESC
                    LIMIT %s
                """, (limit,))
                
                results = cursor.fetchall()
                query_duration_ms = (time.time() - query_start) * 1000
                
                db_span.set_attribute("db.query.duration_ms", query_duration_ms)
                db_span.set_attribute("db.rows_returned", len(results))
                db_span.set_attribute("db.rows_examined", len(results))
                
                db_span.add_event("PostgreSQL SELECT completed successfully", {
                    "rows_returned": len(results),
                    "duration_ms": round(query_duration_ms, 2)
                })
            
            # Format results
            popular_products = []
            for row in results:
                popular_products.append({
                    "product_id": row[0],
                    "product_name": row[1],
                    "order_count": row[2]
                })
            
            main_span.set_attribute("results.count", len(popular_products))
            main_span.set_attribute("query.success", True)
            
            order_stats["queries"] += 1
            order_stats["popularity_checks"] += 1
            
            print(f"✅ Found {len(popular_products)} popular products")
            
            return jsonify({
                "popular_products": popular_products,
                "count": len(popular_products)
            }), 200
            
    except Exception as e:
        order_stats["errors"] += 1
        print(f"❌ Error in get_popular_products: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
        
    finally:
        if conn:
            return_connection(conn)
        if token:
            context.detach(token)

@app.route('/orders/create', methods=['POST'])
def create_order():
    """Create a new order with proper trace context."""
    token = None
    conn = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        # Start main span
        with tracer.start_as_current_span("checkout_service.create_order") as main_span:
            main_span.set_attribute("service.component", "checkout_service")
            main_span.set_attribute("service.name", "checkout-service")
            main_span.set_attribute("db.system", "postgresql")
            
            # Get request data
            data = request.get_json() or {}
            user_id = data.get("user_id")
            product_id = data.get("product_id")
            quantity = data.get("quantity", 1)
            
            if not user_id or not product_id:
                return jsonify({"error": "user_id and product_id required"}), 400
            
            main_span.set_attribute("order.user_id", user_id)
            main_span.set_attribute("order.product_id", product_id)
            main_span.set_attribute("order.quantity", quantity)
            
            print(f"📝 Creating order: user={user_id}, product={product_id}, quantity={quantity}")
            
            # Check for connection pool exhaustion (Black Friday demo)
            order_data = {
                'order_id': f'pending-{user_id}-{product_id}',
                'user_id': user_id,
                'total': quantity * 99.99  # Estimated total
            }
            
            if pool_simulator.should_fail_connection(main_span, order_data):
                order_stats["errors"] += 1
                return jsonify({
                    "error": "SQLSTATE[08006]: Connection timeout after 5000ms"
                }), 503
            
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
                f"INSERT {db_name}.orders",  # OTel convention
                kind=SpanKind.CLIENT  # REQUIRED
            ) as db_span:
                # REQUIRED OpenTelemetry database semantic conventions
                db_span.set_attribute("db.system", "postgresql")
                db_span.set_attribute("db.name", db_name)
                db_span.set_attribute("net.peer.name", os.getenv("DB_HOST", "postgres"))
                db_span.set_attribute("net.peer.port", int(os.getenv("DB_PORT", "5432")))
                db_span.set_attribute("db.user", os.getenv("DB_USER", "dbadmin"))
                db_span.set_attribute("db.operation", "INSERT")
                db_span.set_attribute("db.table", "orders")
                db_span.set_attribute("db.statement", "INSERT INTO orders (user_id, product_id, quantity) VALUES (%s, %s, %s) RETURNING id, order_date")
                db_span.set_attribute("service.name", "order-service")
                db_span.set_attribute("operation.type", "database_write")
                db_span.set_attribute("db.query.user_id", user_id)
                db_span.set_attribute("db.query.product_id", product_id)
                db_span.set_attribute("db.query.quantity", quantity)
                
                # Add database operation event
                db_span.add_event("Starting PostgreSQL INSERT operation", {
                    "table": "orders",
                    "operation": "INSERT",
                    "user_id": user_id,
                    "product_id": product_id,
                    "quantity": quantity
                })
                
                # Simulate slow queries for demo
                if SIMULATE_SLOW_QUERIES:
                    time.sleep(QUERY_DELAY_MS / 1000.0)
                    db_span.set_attribute("db.simulation.slow_query_enabled", True)
                    db_span.set_attribute("db.simulation.delay_ms", QUERY_DELAY_MS)
                
                cursor = conn.cursor()
                query_start = time.time()
                
                cursor.execute("""
                    INSERT INTO orders (user_id, product_id, quantity)
                    VALUES (%s, %s, %s)
                    RETURNING id, order_date
                """, (user_id, product_id, quantity))
                
                result = cursor.fetchone()
                conn.commit()
                query_duration_ms = (time.time() - query_start) * 1000
                
                db_span.set_attribute("db.query.duration_ms", query_duration_ms)
                db_span.set_attribute("db.rows_affected", 1 if result else 0)
                
                db_span.add_event("PostgreSQL INSERT completed successfully", {
                    "rows_affected": 1 if result else 0,
                    "duration_ms": round(query_duration_ms, 2)
                })
            
            if not result:
                main_span.set_attribute("order.created", False)
                return jsonify({"error": "Failed to create order"}), 500
            
            order_data = {
                "success": True,
                "order_id": result[0],
                "user_id": user_id,
                "product_id": product_id,
                "quantity": quantity,
                "order_date": result[1].isoformat()
            }
            
            main_span.set_attribute("order.created", True)
            main_span.set_attribute("order.id", result[0])
            
            order_stats["queries"] += 1
            order_stats["orders_created"] += 1
            
            print(f"✅ Created order {result[0]} for user {user_id}")
            
            return jsonify(order_data), 201
            
    except Exception as e:
        if conn:
            conn.rollback()
        order_stats["errors"] += 1
        print(f"❌ Error in create_order: {e}")
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
        **order_stats,
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
    print("💳 Checkout Service (E-commerce - PostgreSQL) starting...")
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
    
    # Initialize orders table
    if not initialize_orders_table():
        print("⚠️ Orders table initialization failed, but continuing...")
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8016, debug=False)

