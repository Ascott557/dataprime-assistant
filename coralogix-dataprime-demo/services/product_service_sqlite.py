#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Product Service - E-commerce Product Catalog with SQLite
Simple, working implementation using proven SQLite patterns from storage service.
"""

import os
import sys
import time
import json
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry for this service
telemetry_enabled = ensure_telemetry_initialized()

# Initialize tracer
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# Database file (SQLite persistent storage)
DB_FILE = "/app/data/products.db"

# Service stats
product_stats = {
    "queries": 0,
    "products_returned": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def extract_and_attach_trace_context():
    """
    Extract trace context from incoming request and attach it.
    This ensures our spans are children of the calling service's span.
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
                trace_id = format(current_span.get_span_context().trace_id, '032x')
                print(f"✅ Product Service - Joined via propagator: {trace_id}")
                return token, False  # False = not root
            else:
                print("⚠️ Product Service - Propagator extraction failed")
        
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
                print(f"✅ Product Service - Manually joined trace: {manual_trace_id}")
                return token, False  # False = not root
                
            except Exception as e:
                print(f"❌ Product Service - Manual trace creation failed: {e}")
        
        print("📝 Product Service - Creating new root (trace propagation failed)")
        return None, True
        
    except Exception as e:
        print(f"❌ Product Service - Trace context extraction error: {e}")
        return None, True

def initialize_database():
    """Initialize SQLite database with product catalog."""
    try:
        with tracer.start_as_current_span("product_service.initialize_database") as span:
            span.set_attribute("service.component", "product_service")
            span.set_attribute("database.name", DB_FILE)
            span.set_attribute("database.type", "sqlite")
            
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            
            # Products table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    price REAL NOT NULL,
                    description TEXT,
                    image_url TEXT,
                    stock_quantity INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Check if we need to populate sample data
            cursor.execute("SELECT COUNT(*) FROM products")
            count = cursor.fetchone()[0]
            
            if count == 0:
                print("📦 Populating sample product data...")
                
                # Sample wireless headphones data
                products = [
                    ("Anker Soundcore Q30", "Wireless Headphones", 59.99, "Value ANC headphones with 40-hour battery life", "https://example.com/anker-q30.jpg", 88),
                    ("Sony WH-1000XM5", "Wireless Headphones", 299.99, "Premium noise-canceling headphones with industry-leading ANC", "https://example.com/sony-xm5.jpg", 45),
                    ("Bose QuietComfort 45", "Wireless Headphones", 279.99, "Comfortable ANC headphones with excellent noise cancellation", "https://example.com/bose-qc45.jpg", 62),
                    ("JBL Tune 510BT", "Wireless Headphones", 29.99, "Budget-friendly Bluetooth headphones with good sound", "https://example.com/jbl-510.jpg", 150),
                    ("Sennheiser HD 450BT", "Wireless Headphones", 89.99, "Great sound quality with active noise cancellation", "https://example.com/sennheiser-450.jpg", 72),
                    ("Audio-Technica ATH-M50xBT", "Wireless Headphones", 179.99, "Studio-quality wireless headphones for audiophiles", "https://example.com/ath-m50x.jpg", 38),
                    ("Beats Solo3", "Wireless Headphones", 149.99, "Iconic design with Apple W1 chip for seamless pairing", "https://example.com/beats-solo3.jpg", 95),
                    ("Skullcandy Crusher Evo", "Wireless Headphones", 149.99, "Bass-heavy headphones with adjustable haptic feedback", "https://example.com/skullcandy-crusher.jpg", 54),
                    ("Jabra Elite 85h", "Wireless Headphones", 199.99, "Smart noise-canceling headphones with long battery life", "https://example.com/jabra-85h.jpg", 41),
                ]
                
                cursor.executemany('''
                    INSERT INTO products (name, category, price, description, image_url, stock_quantity)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', products)
                
                print(f"✅ Inserted {len(products)} sample products")
            
            conn.commit()
            conn.close()
            
            print("✅ Product database initialized successfully")
            return True
            
    except Exception as e:
        print(f"❌ Product database initialization failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "service": "product-service",
        "status": "healthy",
        "database": "sqlite",
        "db_file": DB_FILE,
        "telemetry_enabled": telemetry_enabled,
        "queries_processed": product_stats["queries"],
        "uptime_seconds": (datetime.now() - product_stats["start_time"]).total_seconds()
    }), 200

@app.route('/products', methods=['GET'])
def get_products():
    """Get products by category and price range with proper trace context."""
    token = None
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        # Start main span
        with tracer.start_as_current_span("product_service.get_products") as main_span:
            main_span.set_attribute("service.component", "product_service")
            main_span.set_attribute("service.name", "product-service")
            main_span.set_attribute("db.system", "sqlite")
            
            # Get query parameters
            category = request.args.get('category', '').strip()
            price_min = float(request.args.get('price_min', 0))
            price_max = float(request.args.get('price_max', 10000))
            
            main_span.set_attribute("query.category", category)
            main_span.set_attribute("query.price_min", price_min)
            main_span.set_attribute("query.price_max", price_max)
            
            if not category:
                return jsonify({"error": "category parameter required"}), 400
            
            print(f"🔍 Querying products: category={category}, price={price_min}-{price_max}")
            
            # Database query with explicit span
            with tracer.start_as_current_span("sqlite.query.select_products") as db_span:
                db_span.set_attribute("db.system", "sqlite")
                db_span.set_attribute("db.operation", "SELECT")
                db_span.set_attribute("db.table", "products")
                db_span.set_attribute("db.statement", "SELECT * FROM products WHERE category = ? AND price BETWEEN ? AND ? ORDER BY price ASC LIMIT 10")
                db_span.set_attribute("db.query.category", category)
                db_span.set_attribute("db.query.price_range", f"{price_min}-{price_max}")
                
                query_start = time.time()
                
                conn = sqlite3.connect(DB_FILE)
                conn.row_factory = sqlite3.Row  # Enable column access by name
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT id, name, category, price, description, image_url, stock_quantity
                    FROM products
                    WHERE category = ? AND price BETWEEN ? AND ?
                    ORDER BY price ASC
                    LIMIT 10
                ''', (category, price_min, price_max))
                
                rows = cursor.fetchall()
                query_duration_ms = (time.time() - query_start) * 1000
                
                db_span.set_attribute("db.query.duration_ms", query_duration_ms)
                db_span.set_attribute("db.rows_returned", len(rows))
                
                conn.close()
            
            # Format results
            products = []
            for row in rows:
                products.append({
                    "id": row["id"],
                    "name": row["name"],
                    "category": row["category"],
                    "price": row["price"],
                    "description": row["description"],
                    "image_url": row["image_url"],
                    "stock_quantity": row["stock_quantity"]
                })
            
            main_span.set_attribute("results.count", len(products))
            main_span.set_attribute("query.success", True)
            
            product_stats["queries"] += 1
            product_stats["products_returned"] += len(products)
            
            print(f"✅ Found {len(products)} products")
            
            return jsonify({
                "products": products,
                "count": len(products),
                "category": category,
                "price_range": {"min": price_min, "max": price_max}
            }), 200
            
    except Exception as e:
        product_stats["errors"] += 1
        print(f"❌ Error in get_products: {e}")
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
        
    finally:
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    return jsonify(product_stats), 200

if __name__ == '__main__':
    print("🛍️ Product Service (E-commerce - SQLite) starting...")
    print(f"   Database: {DB_FILE}")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    
    # Initialize database
    if not initialize_database():
        print("❌ Failed to initialize database, exiting...")
        sys.exit(1)
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8014, debug=False)

