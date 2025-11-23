#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Load Generator - E-commerce Traffic Generation and Orchestration
Generates realistic e-commerce traffic patterns with full OpenTelemetry tracing.
"""

import os
import sys
import time
import random
import requests
from datetime import datetime
from threading import Lock, Thread
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
import structlog

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized, get_telemetry_status

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()

# Initialize telemetry
telemetry_enabled = ensure_telemetry_initialized()

# Get the tracer
tracer = trace.get_tracer(__name__)

print(f"🔍 Telemetry status: {get_telemetry_status()}")

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# E-commerce service endpoints
PRODUCT_CATALOG_URL = os.getenv("PRODUCT_CATALOG_URL", "http://product-catalog:8014")
CHECKOUT_URL = os.getenv("CHECKOUT_URL", "http://checkout:8016")
CART_URL = os.getenv("CART_URL", "http://cart:8013")
RECOMMENDATION_URL = os.getenv("RECOMMENDATION_URL", "http://recommendation:8011")
CURRENCY_URL = os.getenv("CURRENCY_URL", "http://currency:8018")
SHIPPING_URL = os.getenv("SHIPPING_URL", "http://shipping:8019")

# V5: Frontend orchestrator (calls all other services)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend:8018")

# Load generator statistics
load_stats = {
    "requests_sent": 0,
    "errors": 0,
    "start_time": datetime.now(),
    "demo_mode": "normal"
}

# Thread-safe demo state management
demo_state = {
    'running': False,
    'scenario': None,
    'start_timestamp': None,
    'thread': None,
    'lock': Lock()
}

def propagate_trace_context(headers=None):
    """
    Propagate the current trace context to downstream services.
    CRITICAL: This is the pattern from working api_gateway.py
    """
    if headers is None:
        headers = {}
    
    # Try standard propagation first
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    
    # If standard propagation didn't work, create manual headers
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        span_context = current_span.get_span_context()
        trace_id = format(span_context.trace_id, '032x')
        span_id = format(span_context.span_id, '016x')
        
        # Create W3C traceparent header manually
        headers['traceparent'] = f"00-{trace_id}-{span_id}-01"
        print(f"🔗 Manual propagation - trace_id: {trace_id}, span_id: {span_id}")
    else:
        print("⚠️ No current span found for propagation")
    
    return headers

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "load-generator",
        "telemetry_enabled": telemetry_enabled,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/admin/generate-traffic', methods=['POST'])
def generate_traffic():
    """Generate realistic e-commerce traffic."""
    with tracer.start_as_current_span("load_generator.generate_traffic") as span:
        data = request.get_json() or {}
        duration_seconds = data.get('duration_seconds', 60)
        requests_per_minute = data.get('requests_per_minute', 30)
        
        span.set_attribute("traffic.duration_seconds", duration_seconds)
        span.set_attribute("traffic.rpm", requests_per_minute)
        span.set_attribute("service.component", "load_generator")
        
        requests_generated = 0
        errors = 0
        
        delay = 60.0 / requests_per_minute
        end_time = time.time() + duration_seconds
        
        print(f"🚀 Generating traffic: {requests_per_minute} rpm for {duration_seconds}s")
        
        while time.time() < end_time:
            with tracer.start_as_current_span("load_generator.request") as req_span:
                # Propagate trace context
                headers = propagate_trace_context()
                
                try:
                    # Choose action randomly
                    action = random.choice(['browse', 'browse', 'browse', 'checkout'])
                    
                    if action == 'browse':
                        # Browse products (70% of traffic) - V5: Call Frontend orchestrator
                        req_span.set_attribute("action", "browse_products")
                        req_span.set_attribute("traffic.type", "baseline")
                        user_id = f"user-{random.randint(1000, 9999)}"
                        cart_id = f"cart-{random.randint(1000, 9999)}"
                        
                        response = requests.post(
                            f"{FRONTEND_URL}/api/browse",
                            json={"user_id": user_id, "cart_id": cart_id},
                            headers=headers,
                            timeout=10
                        )
                        requests_generated += 1
                    
                    else:
                        # Checkout attempt (30% of traffic) - V5: Call Frontend orchestrator
                        req_span.set_attribute("action", "checkout")
                        req_span.set_attribute("traffic.type", "demo")
                        user_id = f"user-{random.randint(1000, 9999)}"
                        cart_id = f"cart-{random.randint(1000, 9999)}"
                        
                        response = requests.post(
                            f"{FRONTEND_URL}/api/checkout",
                            json={"user_id": user_id, "cart_id": cart_id},
                            headers=headers,
                            timeout=10
                        )
                        requests_generated += 1
                    
                    if response.status_code >= 400:
                        errors += 1
                        req_span.set_status(Status(StatusCode.ERROR))
                    
                except Exception as e:
                    errors += 1
                    req_span.set_status(Status(StatusCode.ERROR, str(e)))
                    print(f"Request error: {e}")
                
                time.sleep(delay)
        
        load_stats["requests_sent"] += requests_generated
        load_stats["errors"] += errors
        
        return jsonify({
            "status": "complete",
            "requests_generated": requests_generated,
            "errors": errors,
            "duration_seconds": duration_seconds,
            "requests_per_minute": requests_per_minute
        })

@app.route('/admin/demo-mode', methods=['POST'])
def set_demo_mode():
    """Set demo mode (normal or blackfriday)."""
    data = request.get_json() or {}
    mode = data.get('mode', 'normal')
    
    load_stats["demo_mode"] = mode
    
    print(f"🎭 Demo mode set to: {mode}")
    
    return jsonify({
        "status": "success",
        "mode": mode,
        "message": f"Demo mode set to {mode}"
    })

@app.route('/admin/stats', methods=['GET'])
def get_stats():
    """Get load generator statistics."""
    return jsonify({
        **load_stats,
        "uptime_seconds": (datetime.now() - load_stats["start_time"]).total_seconds()
    })

@app.route('/api/products/browse', methods=['POST'])
def browse_products():
    """Simulate user browsing products with full trace."""
    with tracer.start_as_current_span("user_session.browse_products") as span:
        data = request.get_json() or {}
        category = data.get('category', 'electronics')
        price_min = data.get('price_min', 0)
        price_max = data.get('price_max', 1000)
        
        span.set_attribute("user.action", "browse")
        span.set_attribute("product.category", category)
        span.set_attribute("service.component", "load_generator")
        
        # Call product catalog service
        with tracer.start_as_current_span("load_generator.call_product_catalog") as call_span:
            headers = propagate_trace_context()
            
            try:
                response = requests.get(
                    f"{PRODUCT_CATALOG_URL}/products",
                    params={"category": category, "price_min": price_min, "price_max": price_max},
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code == 200:
                    products = response.json()
                    call_span.set_attribute("products.count", products.get("products", 0) if isinstance(products, dict) else len(products))
                    
                    return jsonify({
                        "success": True,
                        "products": products
                    })
                else:
                    call_span.set_status(Status(StatusCode.ERROR))
                    return jsonify({
                        "success": False,
                        "error": f"Product service returned {response.status_code}"
                    }), response.status_code
                    
            except Exception as e:
                call_span.set_status(Status(StatusCode.ERROR, str(e)))
                load_stats["errors"] += 1
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

@app.route('/api/checkout', methods=['POST'])
def checkout_flow():
    """Simulate complete checkout flow with trace."""
    with tracer.start_as_current_span("user_session.checkout") as span:
        data = request.get_json() or {}
        user_id = data.get('user_id', f'user-{random.randint(1000, 9999)}')
        product_id = data.get('product_id', random.randint(1, 10))
        quantity = data.get('quantity', 1)
        
        span.set_attribute("user.action", "checkout")
        span.set_attribute("user.id", user_id)
        span.set_attribute("product.id", product_id)
        span.set_attribute("service.component", "load_generator")
        
        # Call checkout service
        with tracer.start_as_current_span("load_generator.call_checkout") as call_span:
            headers = propagate_trace_context()
            
            try:
                response = requests.post(
                    f"{CHECKOUT_URL}/orders/create",
                    json={
                        "user_id": user_id,
                        "product_id": product_id,
                        "quantity": quantity
                    },
                    headers=headers,
                    timeout=10
                )
                
                if response.status_code in [200, 201]:
                    order_data = response.json()
                    call_span.set_attribute("order.success", True)
                    
                    return jsonify({
                        "success": True,
                        "order": order_data
                    })
                else:
                    call_span.set_status(Status(StatusCode.ERROR))
                    return jsonify({
                        "success": False,
                        "error": f"Checkout service returned {response.status_code}"
                    }), response.status_code
                    
            except Exception as e:
                call_span.set_status(Status(StatusCode.ERROR, str(e)))
                load_stats["errors"] += 1
                return jsonify({
                    "success": False,
                    "error": str(e)
                }), 500

def _run_demo_thread(scenario, duration, start_ts):
    """Run Black Friday scenario in separate thread."""
    try:
        service_urls = {
            'product_catalog': PRODUCT_CATALOG_URL,
            'checkout': CHECKOUT_URL,
            'cart': CART_URL
        }
        
        scenario.generate_traffic(
            duration_minutes=duration,
            start_timestamp=start_ts,
            service_urls=service_urls,
            propagate_fn=propagate_trace_context
        )
    except Exception as e:
        logger.error("demo_thread_failed", error=str(e))
    finally:
        with demo_state['lock']:
            demo_state['running'] = False
        logger.info("demo_thread_completed")


@app.route('/admin/start-demo', methods=['POST'])
def start_demo():
    """Start Black Friday traffic scenario with thread-safe state management."""
    with demo_state['lock']:
        if demo_state['running']:
            return jsonify({
                "error": "Demo already running",
                "current_demo": {
                    "start_timestamp": demo_state['start_timestamp'],
                    "elapsed_seconds": time.time() - demo_state['start_timestamp']
                }
            }), 400
        
        data = request.get_json() or {}
        scenario = data.get('scenario', 'blackfriday')
        duration_minutes = data.get('duration_minutes', 30)
        peak_rpm = data.get('peak_rpm', 120)
        
        if scenario != 'blackfriday':
            return jsonify({
                "error": "Only 'blackfriday' scenario supported"
            }), 400
        
        logger.info(
            "demo_start_requested",
            scenario=scenario,
            duration_minutes=duration_minutes,
            peak_rpm=peak_rpm
        )
        
        # Import and instantiate Black Friday scenario
        try:
            from black_friday_scenario import BlackFridayScenario
            
            bf_scenario = BlackFridayScenario()
            bf_scenario.peak_rpm = peak_rpm  # Allow override
            
            start_timestamp = time.time()
            
            # Update state
            demo_state['running'] = True
            demo_state['scenario'] = bf_scenario
            demo_state['start_timestamp'] = start_timestamp
            
            # Launch non-daemon thread for clean shutdown
            thread = Thread(
                target=_run_demo_thread,
                args=(bf_scenario, duration_minutes, start_timestamp),
                daemon=False  # Non-daemon for clean shutdown
            )
            demo_state['thread'] = thread
            thread.start()
            
            logger.info(
                "demo_started",
                start_timestamp=start_timestamp,
                duration_minutes=duration_minutes
            )
            
            return jsonify({
                "status": "demo_started",
                "scenario": scenario,
                "duration_minutes": duration_minutes,
                "peak_rpm": peak_rpm,
                "start_timestamp": start_timestamp,
                "start_time_iso": datetime.fromtimestamp(start_timestamp).isoformat()
            }), 200
            
        except ImportError as e:
            logger.error("failed_to_import_scenario", error=str(e))
            return jsonify({
                "error": "Failed to load Black Friday scenario",
                "details": str(e)
            }), 500
        except Exception as e:
            logger.error("demo_start_failed", error=str(e))
            demo_state['running'] = False
            return jsonify({
                "error": "Failed to start demo",
                "details": str(e)
            }), 500


@app.route('/admin/demo-status', methods=['GET'])
def demo_status():
    """Get current Black Friday demo status."""
    with demo_state['lock']:
        if not demo_state['running']:
            return jsonify({
                "running": False,
                "message": "No demo currently running"
            }), 200
        
        scenario = demo_state['scenario']
        start_ts = demo_state['start_timestamp']
        
        if not scenario or not start_ts:
            return jsonify({
                "running": False,
                "message": "Demo state incomplete"
            }), 200
        
        elapsed_seconds = time.time() - start_ts
        elapsed_minutes = elapsed_seconds / 60
        
        current_rpm = scenario.get_current_rpm(elapsed_minutes)
        phase = scenario.get_current_phase(elapsed_minutes)
        
        # Calculate error rate
        error_rate = 0
        if scenario.requests_sent > 0:
            error_rate = scenario.errors / scenario.requests_sent
        
        return jsonify({
            "running": True,
            "elapsed_minutes": int(elapsed_minutes),
            "elapsed_seconds": int(elapsed_seconds),
            "current_rpm": current_rpm,
            "phase": phase,
            "requests_sent": scenario.requests_sent,
            "errors": scenario.errors,
            "current_error_rate": round(error_rate, 3),
            "checkouts_attempted": scenario.checkouts_attempted,
            "checkouts_failed": scenario.checkouts_failed,
            "start_timestamp": start_ts,
            "start_time_iso": datetime.fromtimestamp(start_ts).isoformat()
        }), 200


@app.route('/admin/stop-demo', methods=['POST'])
def stop_demo():
    """Stop the currently running demo."""
    with demo_state['lock']:
        if not demo_state['running']:
            return jsonify({
                "message": "No demo currently running"
            }), 200
        
        demo_state['running'] = False
        
        logger.info("demo_stop_requested")
        
        return jsonify({
            "status": "stopping",
            "message": "Demo will stop after current request completes"
        }), 200


if __name__ == '__main__':
    print("🚀 Load Generator starting on port 8010...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Demo mode: {load_stats['demo_mode']}")
    app.run(host='0.0.0.0', port=8010, debug=False)

