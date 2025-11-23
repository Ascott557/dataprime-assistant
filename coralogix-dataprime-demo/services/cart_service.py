#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Cart Service - E-commerce Shopping Cart with Redis
Manual OpenTelemetry instrumentation for reliable distributed tracing.
"""

import os
import sys
import time
import json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry
telemetry_enabled = ensure_telemetry_initialized()

# Import Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    print("⚠️ Redis not available - cart will use in-memory storage")
    REDIS_AVAILABLE = False

# Initialize tracer
tracer = trace.get_tracer(__name__)

app = Flask(__name__)
CORS(app)

# Redis connection
_redis_client = None

# Fallback in-memory storage if Redis unavailable
_memory_carts = {}

# Service stats
cart_stats = {
    "operations": 0,
    "carts_created": 0,
    "items_added": 0,
    "items_removed": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def initialize_redis():
    """Initialize Redis connection."""
    global _redis_client
    if not REDIS_AVAILABLE:
        print("⚠️ Redis library not available, using in-memory storage")
        return None
        
    if _redis_client is not None:
        return _redis_client
    
    try:
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        
        _redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=0,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3
        )
        
        # Test connection
        _redis_client.ping()
        
        print(f"✅ Redis connected: {redis_host}:{redis_port}")
        return _redis_client
        
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("⚠️ Falling back to in-memory storage")
        _redis_client = None
        return None

def extract_and_attach_trace_context():
    """
    Extract trace context from incoming request and attach it.
    This ensures our spans are children of the calling service's span.
    CRITICAL for proper distributed tracing!
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
                        print(f"🔧 Cart Service - Manually parsed trace_id: {manual_trace_id}")
                        break
        
        # Check if standard propagation worked
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = format(current_span.get_span_context().trace_id, '032x')
                print(f"✅ Cart Service - Joined via propagator: {trace_id}")
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
                
                print(f"✅ Cart Service - Manually joined trace: {manual_trace_id}")
                return token, False
                
            except Exception as e:
                print(f"⚠️ Manual trace join failed: {e}")
                return None, True
        
        print("⚠️ Cart Service - Starting root trace (no parent)")
        return None, True
        
    except Exception as e:
        print(f"⚠️ Trace context extraction failed: {e}")
        return None, True

def get_cart(cart_id):
    """Get cart from Redis or memory."""
    if _redis_client:
        try:
            cart_json = _redis_client.get(f"cart:{cart_id}")
            if cart_json:
                return json.loads(cart_json)
        except Exception as e:
            print(f"❌ Redis get error: {e}")
    
    # Fallback to memory
    return _memory_carts.get(cart_id, {"items": [], "total": 0.0})

def save_cart(cart_id, cart_data):
    """Save cart to Redis or memory."""
    if _redis_client:
        try:
            _redis_client.setex(
                f"cart:{cart_id}",
                86400,  # 24 hour TTL
                json.dumps(cart_data)
            )
            return True
        except Exception as e:
            print(f"❌ Redis save error: {e}")
    
    # Fallback to memory
    _memory_carts[cart_id] = cart_data
    return True

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    redis_status = "connected" if _redis_client else "in-memory"
    
    return jsonify({
        "service": "cart-service",
        "status": "healthy",
        "storage": redis_status,
        "telemetry_enabled": telemetry_enabled,
        "operations": cart_stats["operations"],
        "carts_created": cart_stats["carts_created"],
        "uptime_seconds": (datetime.now() - cart_stats["start_time"]).total_seconds()
    }), 200

@app.route('/cart/<cart_id>', methods=['GET'])
def get_cart_endpoint(cart_id):
    """Get shopping cart contents."""
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("cart_service.get_cart") as span:
            span.set_attribute("service.component", "cart_service")
            span.set_attribute("service.name", "cart-service")
            span.set_attribute("cart.id", cart_id)
            
            cart_data = get_cart(cart_id)
            
            span.set_attribute("cart.items_count", len(cart_data.get("items", [])))
            span.set_attribute("cart.total", cart_data.get("total", 0.0))
            
            cart_stats["operations"] += 1
            
            return jsonify({
                "success": True,
                "cart_id": cart_id,
                "cart": cart_data
            }), 200
            
    except Exception as e:
        cart_stats["errors"] += 1
        print(f"❌ Error in get_cart: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        if token:
            context.detach(token)

@app.route('/cart/<cart_id>/add', methods=['POST'])
def add_to_cart(cart_id):
    """Add item to shopping cart."""
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("cart_service.add_item") as span:
            span.set_attribute("service.component", "cart_service")
            span.set_attribute("service.name", "cart-service")
            span.set_attribute("cart.id", cart_id)
            span.set_attribute("operation.type", "add_item")
            
            data = request.get_json() or {}
            product_id = data.get("product_id")
            product_name = data.get("product_name", "Unknown Product")
            price = float(data.get("price", 0.0))
            quantity = int(data.get("quantity", 1))
            
            if not product_id:
                return jsonify({"success": False, "error": "product_id required"}), 400
            
            span.set_attribute("product.id", product_id)
            span.set_attribute("product.name", product_name)
            span.set_attribute("product.quantity", quantity)
            
            # Get current cart
            cart_data = get_cart(cart_id)
            
            # Add or update item
            items = cart_data.get("items", [])
            found = False
            
            for item in items:
                if item["product_id"] == product_id:
                    item["quantity"] += quantity
                    found = True
                    break
            
            if not found:
                items.append({
                    "product_id": product_id,
                    "product_name": product_name,
                    "price": price,
                    "quantity": quantity
                })
            
            # Recalculate total
            total = sum(item["price"] * item["quantity"] for item in items)
            
            cart_data = {
                "items": items,
                "total": total,
                "updated_at": datetime.now().isoformat()
            }
            
            # Save cart
            save_cart(cart_id, cart_data)
            
            span.set_attribute("cart.items_count", len(items))
            span.set_attribute("cart.total", total)
            
            cart_stats["operations"] += 1
            cart_stats["items_added"] += 1
            if not found:
                cart_stats["carts_created"] += 1
            
            return jsonify({
                "success": True,
                "cart_id": cart_id,
                "cart": cart_data
            }), 200
            
    except Exception as e:
        cart_stats["errors"] += 1
        print(f"❌ Error in add_to_cart: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        if token:
            context.detach(token)

@app.route('/cart/<cart_id>/remove', methods=['POST'])
def remove_from_cart(cart_id):
    """Remove item from shopping cart."""
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("cart_service.remove_item") as span:
            span.set_attribute("service.component", "cart_service")
            span.set_attribute("service.name", "cart-service")
            span.set_attribute("cart.id", cart_id)
            span.set_attribute("operation.type", "remove_item")
            
            data = request.get_json() or {}
            product_id = data.get("product_id")
            
            if not product_id:
                return jsonify({"success": False, "error": "product_id required"}), 400
            
            span.set_attribute("product.id", product_id)
            
            # Get current cart
            cart_data = get_cart(cart_id)
            items = cart_data.get("items", [])
            
            # Remove item
            items = [item for item in items if item["product_id"] != product_id]
            
            # Recalculate total
            total = sum(item["price"] * item["quantity"] for item in items)
            
            cart_data = {
                "items": items,
                "total": total,
                "updated_at": datetime.now().isoformat()
            }
            
            # Save cart
            save_cart(cart_id, cart_data)
            
            span.set_attribute("cart.items_count", len(items))
            span.set_attribute("cart.total", total)
            
            cart_stats["operations"] += 1
            cart_stats["items_removed"] += 1
            
            return jsonify({
                "success": True,
                "cart_id": cart_id,
                "cart": cart_data
            }), 200
            
    except Exception as e:
        cart_stats["errors"] += 1
        print(f"❌ Error in remove_from_cart: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        if token:
            context.detach(token)

@app.route('/cart/<cart_id>/clear', methods=['POST'])
def clear_cart(cart_id):
    """Clear all items from cart."""
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("cart_service.clear_cart") as span:
            span.set_attribute("service.component", "cart_service")
            span.set_attribute("service.name", "cart-service")
            span.set_attribute("cart.id", cart_id)
            span.set_attribute("operation.type", "clear_cart")
            
            cart_data = {
                "items": [],
                "total": 0.0,
                "updated_at": datetime.now().isoformat()
            }
            
            save_cart(cart_id, cart_data)
            
            cart_stats["operations"] += 1
            
            return jsonify({
                "success": True,
                "cart_id": cart_id,
                "cart": cart_data
            }), 200
            
    except Exception as e:
        cart_stats["errors"] += 1
        print(f"❌ Error in clear_cart: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    return jsonify({
        **cart_stats,
        "uptime_seconds": (datetime.now() - cart_stats["start_time"]).total_seconds()
    }), 200

if __name__ == '__main__':
    print("🛒 Cart Service (Redis) starting on port 8013...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    
    # Initialize Redis
    initialize_redis()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8013, debug=False)

