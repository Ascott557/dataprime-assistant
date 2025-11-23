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
import asyncio
import aiohttp
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
from app.shared_span_attributes import calculate_demo_minute, is_demo_mode

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


class DualModeLoadGenerator:
    """
    Generates both baseline and demo traffic simultaneously.
    
    Baseline: 100 rpm to /products (fast, indexed) - always healthy
    Demo: 800→4200 rpm to /products/recommendations (slow, unindexed) - progressive failures
    """
    
    def __init__(self):
        self.baseline_rpm = 100
        self.demo_base_rpm = 800
        self.demo_peak_rpm = 4200
        self.baseline_stats = {"requests": 0, "errors": 0}
        self.demo_stats = {"requests": 0, "errors": 0}
    
    def calculate_demo_rpm(self, demo_minute):
        """Calculate current demo RPM based on elapsed minutes."""
        if demo_minute < 0:
            return 0
        elif demo_minute < 10:
            # Ramp up: 800 → 3400 rpm over 10 minutes
            return int(800 + (demo_minute * 260))
        elif demo_minute < 25:
            # Peak: 4200 rpm sustained
            return 4200
        else:
            # Wind down: 4200 → 1000 rpm
            return max(1000, int(4200 - ((demo_minute - 25) * 640)))
    
    async def generate_baseline_traffic(self):
        """Continuous 100 rpm to /products endpoint - always healthy."""
        async with aiohttp.ClientSession() as session:
            while True:
                with tracer.start_as_current_span("baseline_request") as span:
                    span.set_attribute("traffic.type", "baseline")
                    span.set_attribute("traffic.category", "control")
                    
                    headers = propagate_trace_context()
                    
                    try:
                        async with session.get(
                            f"{PRODUCT_CATALOG_URL}/products",
                            params={"category": "electronics"},
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=2)
                        ) as response:
                            span.set_attribute("http.status_code", response.status)
                            self.baseline_stats["requests"] += 1
                            
                            if response.status >= 500:
                                span.set_status(Status(StatusCode.ERROR))
                                self.baseline_stats["errors"] += 1
                            else:
                                span.set_status(Status(StatusCode.OK))
                    
                    except Exception as e:
                        logger.error("baseline_traffic_failure", error=str(e))
                        span.set_status(Status(StatusCode.ERROR))
                        self.baseline_stats["errors"] += 1
                
                await asyncio.sleep(0.6)  # 100 rpm = 0.6s delay
    
    async def generate_demo_traffic(self):
        """Progressive 800→4200 rpm to /products/recommendations - experiences failures."""
        async with aiohttp.ClientSession() as session:
            while True:
                if not is_demo_mode():
                    await asyncio.sleep(10)
                    continue
                
                demo_minute = calculate_demo_minute()
                current_rpm = self.calculate_demo_rpm(demo_minute)
                
                if current_rpm == 0:
                    await asyncio.sleep(1)
                    continue
                
                with tracer.start_as_current_span("demo_request") as span:
                    span.set_attribute("traffic.type", "demo")
                    span.set_attribute("traffic.category", "blackfriday")
                    span.set_attribute("demo_minute", demo_minute)
                    
                    headers = propagate_trace_context()
                    
                    try:
                        async with session.get(
                            f"{PRODUCT_CATALOG_URL}/products/recommendations",
                            params={
                                "category": "electronics",
                                "user_id": f"user-{random.randint(1000, 9999)}"
                            },
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=6)
                        ) as response:
                            span.set_attribute("http.status_code", response.status)
                            self.demo_stats["requests"] += 1
                            
                            if response.status >= 500:
                                span.set_status(Status(StatusCode.ERROR))
                                self.demo_stats["errors"] += 1
                            else:
                                span.set_status(Status(StatusCode.OK))
                    
                    except asyncio.TimeoutError:
                        span.set_attribute("error.type", "timeout")
                        span.set_status(Status(StatusCode.ERROR))
                        self.demo_stats["errors"] += 1
                    
                    except Exception as e:
                        span.set_attribute("error.type", type(e).__name__)
                        span.set_status(Status(StatusCode.ERROR))
                        self.demo_stats["errors"] += 1
                
                # Calculate delay based on current RPM
                rps = current_rpm / 60.0
                delay = 1.0 / rps
                await asyncio.sleep(delay)


# Global generator instance
_dual_mode_generator = None


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
                        # Browse products (70% of traffic)
                        req_span.set_attribute("action", "browse_products")
                        category = random.choice(['electronics', 'furniture', 'sports'])
                        
                        response = requests.get(
                            f"{PRODUCT_CATALOG_URL}/products",
                            params={"category": category, "price_min": 0, "price_max": 1000},
                            headers=headers,
                            timeout=10
                        )
                        requests_generated += 1
                    
                    else:
                        # Checkout attempt (30% of traffic)
                        req_span.set_attribute("action", "checkout")
                        response = requests.post(
                            f"{CHECKOUT_URL}/orders/create",
                            json={
                                "user_id": f"user-{random.randint(1000, 9999)}",
                                "product_id": random.randint(1, 10),
                                "quantity": random.randint(1, 3)
                            },
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


@app.route('/admin/traffic-stats', methods=['GET'])
def traffic_stats():
    """Get current traffic statistics for both baseline and demo modes."""
    global _dual_mode_generator
    
    demo_minute = calculate_demo_minute()
    current_demo_rpm = 0
    
    if _dual_mode_generator:
        current_demo_rpm = _dual_mode_generator.calculate_demo_rpm(demo_minute)
        baseline_stats = _dual_mode_generator.baseline_stats
        demo_stats = _dual_mode_generator.demo_stats
    else:
        baseline_stats = {"requests": 0, "errors": 0}
        demo_stats = {"requests": 0, "errors": 0}
    
    baseline_error_rate = (baseline_stats['errors'] / max(1, baseline_stats['requests'])) * 100
    demo_error_rate = (demo_stats['errors'] / max(1, demo_stats['requests'])) * 100
    
    return jsonify({
        "baseline": {
            "rpm": 100,
            "requests": baseline_stats["requests"],
            "errors": baseline_stats["errors"],
            "error_rate": f"{baseline_error_rate:.1f}%"
        },
        "demo": {
            "current_rpm": current_demo_rpm if is_demo_mode() else 0,
            "demo_minute": demo_minute,
            "requests": demo_stats["requests"],
            "errors": demo_stats["errors"],
            "error_rate": f"{demo_error_rate:.1f}%"
        }
    })


def start_dual_mode_on_startup():
    """Start dual-mode traffic automatically when service starts."""
    global _dual_mode_generator
    _dual_mode_generator = DualModeLoadGenerator()
    
    def run_async():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        baseline_task = loop.create_task(_dual_mode_generator.generate_baseline_traffic())
        demo_task = loop.create_task(_dual_mode_generator.generate_demo_traffic())
        
        loop.run_until_complete(asyncio.gather(baseline_task, demo_task))
    
    thread = Thread(target=run_async, daemon=True)
    thread.start()
    
    logger.info("dual_mode_traffic_started", 
                baseline_rpm=100, 
                demo_base_rpm=800,
                demo_peak_rpm=4200)
    print("🚀 Dual-mode traffic generator started")
    print("   Baseline: 100 rpm → /products (always healthy)")
    print("   Demo: 800-4200 rpm → /products/recommendations (progressive failures)")


if __name__ == '__main__':
    print("🚀 Load Generator starting on port 8010...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Demo mode: {load_stats['demo_mode']}")
    
    # Start dual-mode traffic automatically
    start_dual_mode_on_startup()
    
    app.run(host='0.0.0.0', port=8010, debug=False)

