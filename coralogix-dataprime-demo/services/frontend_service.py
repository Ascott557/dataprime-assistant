#!/usr/bin/env python3
"""
Frontend Service - Main Orchestrator for V5 E-commerce Architecture
Coordinates all service-to-service calls for realistic microservices flow

Endpoints:
- /api/browse (baseline traffic - always healthy, fast)
- /api/checkout (demo traffic - includes slow recommendations, may fail)
"""

import os
import sys
import random
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace import Status, StatusCode, SpanKind

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized
from app.shared_span_attributes import (
    DemoSpanAttributes,
    calculate_demo_minute,
    is_demo_mode
)

def extract_and_attach_trace_context():
    """Extract trace context from incoming request."""
    try:
        from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
        headers = dict(request.headers)
        propagator = TraceContextTextMapPropagator()
        incoming_context = propagator.extract(headers)
        
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                return token, False
            else:
                context.detach(token)
        
        return None, True
    except Exception as e:
        print(f"⚠️ Trace context extraction failed: {e}")
        return None, True

def propagate_trace_context():
    """Propagate trace context to downstream services."""
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    headers = {}
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers

# Initialize telemetry
telemetry_enabled = ensure_telemetry_initialized()
tracer = trace.get_tracer(__name__)

app = Flask(__name__)
CORS(app)

# Service URLs - using EXISTING endpoints (no port changes)
CART_URL = os.getenv("CART_URL", "http://cart:8013")
PRODUCT_CATALOG_URL = os.getenv("PRODUCT_CATALOG_URL", "http://product-catalog:8014")
PAYMENT_SERVICE_URL = os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8017")
CHECKOUT_URL = os.getenv("CHECKOUT_URL", "http://checkout:8016")

# Frontend statistics
frontend_stats = {
    "baseline_requests": 0,
    "demo_requests": 0,
    "successful_checkouts": 0,
    "failed_checkouts": 0
}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "frontend",
        "telemetry_enabled": telemetry_enabled,
        "endpoints": {
            "baseline": "/api/browse",
            "demo": "/api/checkout"
        },
        "stats": frontend_stats
    }), 200

@app.route('/api/browse', methods=['POST'])
def browse_products():
    """
    Baseline Traffic Endpoint - Fast, always healthy
    
    Flow: Cart → Products (indexed) → (optionally Payment → Checkout)
    This simulates light browsing without checkout
    """
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("frontend_browse") as span:
            span.set_attribute("traffic.type", "baseline")
            span.set_attribute("http.route", "/api/browse")
            span.set_attribute("service.name", "frontend")
            span.set_attribute("operation.type", "browse")
            
            # Get request data
            data = request.get_json() or {}
            user_id = data.get("user_id", f"user-{random.randint(1000, 9999)}")
            cart_id = data.get("cart_id", f"cart-{random.randint(1000, 9999)}")
            
            span.set_attribute("user.id", user_id)
            span.set_attribute("cart.id", cart_id)
            
            # Prepare headers for downstream calls
            headers = propagate_trace_context()
            
            # Step 1: Get cart (fast - should always succeed)
            try:
                with tracer.start_as_current_span("call_cart", kind=SpanKind.CLIENT) as cart_span:
                    cart_span.set_attribute("peer.service", "cart-service")
                    cart_span.set_attribute("http.url", f"{CART_URL}/cart/{cart_id}")
                    
                    cart_response = requests.get(
                        f"{CART_URL}/cart/{cart_id}",
                        headers=headers,
                        timeout=2
                    )
                    cart_span.set_attribute("http.status_code", cart_response.status_code)
            except Exception as e:
                print(f"⚠️ Cart service error (non-critical): {e}")
            
            # Step 2: Get products (fast indexed query - should always succeed)
            try:
                with tracer.start_as_current_span("call_products", kind=SpanKind.CLIENT) as prod_span:
                    prod_span.set_attribute("peer.service", "product-catalog")
                    prod_span.set_attribute("http.url", f"{PRODUCT_CATALOG_URL}/products")
                    prod_span.set_attribute("query.category", "electronics")
                    
                    products_response = requests.get(
                        f"{PRODUCT_CATALOG_URL}/products",
                        params={"category": "electronics", "traffic_type": "baseline"},
                        headers=headers,
                        timeout=3
                    )
                    prod_span.set_attribute("http.status_code", products_response.status_code)
            except Exception as e:
                print(f"⚠️ Product catalog error (non-critical): {e}")
            
            # Update stats
            frontend_stats["baseline_requests"] += 1
            
            return jsonify({
                "status": "success",
                "flow": "baseline_browse",
                "user_id": user_id,
                "cart_id": cart_id,
                "message": "Browse completed successfully"
            }), 200
    
    except Exception as e:
        print(f"❌ Browse error: {e}")
        if 'span' in locals():
            span.set_status(Status(StatusCode.ERROR))
        return jsonify({"error": str(e)}), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/api/checkout', methods=['POST'])
def checkout():
    """
    Demo Traffic Endpoint - Full checkout flow with recommendations
    
    Flow: Cart → Recommendations (SLOW/FAILS) → Payment → Checkout
    The recommendation call is the failure point during demo mode
    """
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("frontend_checkout") as span:
            span.set_attribute("traffic.type", "demo")
            span.set_attribute("http.route", "/api/checkout")
            span.set_attribute("service.name", "frontend")
            span.set_attribute("operation.type", "checkout")
            
            # Get request data
            data = request.get_json() or {}
            user_id = data.get("user_id", f"user-{random.randint(1000, 9999)}")
            cart_id = data.get("cart_id", f"cart-{random.randint(1000, 9999)}")
            
            # Calculate demo minute for progressive failures
            demo_minute = calculate_demo_minute()
            span.set_attribute("demo.minute", demo_minute)
            span.set_attribute("user.id", user_id)
            span.set_attribute("cart.id", cart_id)
            
            # Prepare headers for downstream calls
            headers = propagate_trace_context()
            
            # Step 1: Get cart (always fast)
            try:
                with tracer.start_as_current_span("call_cart", kind=SpanKind.CLIENT) as cart_span:
                    cart_span.set_attribute("peer.service", "cart-service")
                    cart_span.set_attribute("http.url", f"{CART_URL}/cart/{cart_id}")
                    
                    cart_response = requests.get(
                        f"{CART_URL}/cart/{cart_id}",
                        headers=headers,
                        timeout=2
                    )
                    cart_span.set_attribute("http.status_code", cart_response.status_code)
                    
                    # Extract cart total for payment
                    cart_data = cart_response.json() if cart_response.status_code == 200 else {}
                    cart_total = cart_data.get("cart", {}).get("total", 99.99)
            except Exception as e:
                print(f"⚠️ Cart service error: {e}")
                cart_total = 99.99
            
            # Step 2: Get recommendations (SLOW - this is the failure point)
            if is_demo_mode() and demo_minute >= 1:
                try:
                    with tracer.start_as_current_span("call_recommendations", kind=SpanKind.CLIENT) as rec_span:
                        rec_span.set_attribute("peer.service", "product-catalog")
                        rec_span.set_attribute("traffic.type", "demo")
                        rec_span.set_attribute("http.url", f"{PRODUCT_CATALOG_URL}/products/recommendations")
                        rec_span.set_attribute("query.category", "electronics")
                        
                        rec_response = requests.get(
                            f"{PRODUCT_CATALOG_URL}/products/recommendations",
                            params={"category": "electronics", "traffic_type": "demo"},
                            headers=headers,
                            timeout=5  # This will timeout during peak demo
                        )
                        
                        rec_span.set_attribute("http.status_code", rec_response.status_code)
                        
                        if rec_response.status_code >= 500:
                            raise Exception(f"Recommendations service error: {rec_response.status_code}")
                
                except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                    # Recommendation timeout/error - this blocks checkout!
                    rec_span.set_status(Status(StatusCode.ERROR))
                    rec_span.set_attribute("error.type", "timeout")
                    rec_span.set_attribute("error.message", str(e))
                    
                    span.set_status(Status(StatusCode.ERROR))
                    
                    # Set checkout failed attributes
                    order_id = f"order-{user_id}-failed"
                    DemoSpanAttributes.set_checkout_failed(
                        span=span,
                        order_id=order_id,
                        user_id=user_id,
                        total=cart_total,
                        failure_reason="product-recommendations-timeout"
                    )
                    
                    # Update stats
                    frontend_stats["demo_requests"] += 1
                    frontend_stats["failed_checkouts"] += 1
                    
                    print(f"🔴 Checkout failed: recommendations timeout (demo minute {demo_minute})")
                    
                    return jsonify({
                        "error": "Checkout failed",
                        "reason": "Product recommendations unavailable",
                        "demo_minute": demo_minute,
                        "message": "Unable to complete checkout due to service timeout"
                    }), 503
            
            # Step 3: Process payment (only reached if recommendations succeeded)
            try:
                with tracer.start_as_current_span("call_payment", kind=SpanKind.CLIENT) as pay_span:
                    pay_span.set_attribute("peer.service", "payment-service")
                    pay_span.set_attribute("http.url", f"{PAYMENT_SERVICE_URL}/api/payment/process")
                    pay_span.set_attribute("payment.amount", cart_total)
                    
                    payment_response = requests.post(
                        f"{PAYMENT_SERVICE_URL}/api/payment/process",
                        json={"amount": cart_total, "user_id": user_id, "payment_method": "credit_card"},
                        headers=headers,
                        timeout=3
                    )
                    pay_span.set_attribute("http.status_code", payment_response.status_code)
                    
                    payment_data = payment_response.json() if payment_response.status_code == 200 else {}
                    transaction_id = payment_data.get("transaction_id", "unknown")
                    pay_span.set_attribute("payment.transaction_id", transaction_id)
            except Exception as e:
                print(f"⚠️ Payment service error: {e}")
                transaction_id = "unknown"
            
            # Step 4: Create order (final step)
            try:
                with tracer.start_as_current_span("call_checkout", kind=SpanKind.CLIENT) as checkout_span:
                    checkout_span.set_attribute("peer.service", "checkout")
                    checkout_span.set_attribute("http.url", f"{CHECKOUT_URL}/orders/create")
                    
                    order_response = requests.post(
                        f"{CHECKOUT_URL}/orders/create",
                        json={
                            "user_id": user_id,
                            "product_id": f"prod-{random.randint(100, 999)}",
                            "quantity": 1
                        },
                        headers=headers,
                        timeout=2
                    )
                    checkout_span.set_attribute("http.status_code", order_response.status_code)
                    
                    order_data = order_response.json() if order_response.status_code == 200 else {}
                    order_id = order_data.get("order_id", "unknown")
                    checkout_span.set_attribute("order.id", order_id)
            except Exception as e:
                print(f"⚠️ Checkout service error: {e}")
                order_id = "unknown"
            
            # Update stats
            frontend_stats["demo_requests"] += 1
            frontend_stats["successful_checkouts"] += 1
            
            span.set_status(Status(StatusCode.OK))
            span.set_attribute("checkout.order_id", order_id)
            span.set_attribute("payment.transaction_id", transaction_id)
            
            print(f"✅ Checkout success: Order {order_id}, Transaction {transaction_id}")
            
            return jsonify({
                "status": "success",
                "flow": "demo_checkout",
                "user_id": user_id,
                "order_id": order_id,
                "transaction_id": transaction_id,
                "total": cart_total,
                "demo_minute": demo_minute
            }), 200
    
    except Exception as e:
        print(f"❌ Checkout error: {e}")
        if 'span' in locals():
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
        
        frontend_stats["demo_requests"] += 1
        frontend_stats["failed_checkouts"] += 1
        
        return jsonify({"error": str(e)}), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get frontend statistics"""
    return jsonify(frontend_stats), 200

if __name__ == '__main__':
    print("🌐 Frontend Service (V5 Orchestrator) starting on port 8018...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Cart URL: {CART_URL}")
    print(f"   Product Catalog URL: {PRODUCT_CATALOG_URL}")
    print(f"   Payment URL: {PAYMENT_SERVICE_URL}")
    print(f"   Checkout URL: {CHECKOUT_URL}")
    print("")
    print("   Endpoints:")
    print("   - POST /api/browse (baseline traffic)")
    print("   - POST /api/checkout (demo traffic)")
    print("")
    app.run(host='0.0.0.0', port=8018, debug=False)

