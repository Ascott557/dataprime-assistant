#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Recommendation Service - E-commerce Product Recommendations (Rule-Based)
Provides product recommendations based on category and price, with full OpenTelemetry tracing.
"""

import os
import sys
import random
import requests
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

# Initialize OpenTelemetry
tracer = trace.get_tracer(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Service URLs
PRODUCT_CATALOG_URL = os.getenv("PRODUCT_CATALOG_URL", "http://product-catalog:8014")

# Recommendation stats
recommendation_stats = {
    "requests": 0,
    "successful": 0,
    "failed": 0,
    "start_time": datetime.now()
}

def extract_and_attach_trace_context():
    """Extract trace context from incoming request and attach it."""
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
                        print(f"🔧 Recommendation Service - Manually parsed trace_id: {manual_trace_id}")
                        break
        
        # Check if standard propagation worked
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                trace_id = format(current_span.get_span_context().trace_id, '032x')
                print(f"✅ Recommendation Service - Joined via propagator: {trace_id}")
                return token, False
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
                
                print(f"✅ Recommendation Service - Manually joined trace: {manual_trace_id}")
                return token, False
                
            except Exception as e:
                print(f"⚠️ Manual trace join failed: {e}")
                return None, True
        
        print("⚠️ Recommendation Service - Starting root trace (no parent)")
        return None, True
        
    except Exception as e:
        print(f"⚠️ Trace context extraction failed: {e}")
        return None, True

def propagate_trace_context(headers=None):
    """Propagate trace context to downstream services."""
    if headers is None:
        headers = {}
    
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    
    current_span = trace.get_current_span()
    if current_span and current_span.is_recording():
        span_context = current_span.get_span_context()
        trace_id = format(span_context.trace_id, '032x')
        span_id = format(span_context.span_id, '016x')
        headers['traceparent'] = f"00-{trace_id}-{span_id}-01"
    
    return headers

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "recommendation-service",
        "telemetry_initialized": telemetry_enabled,
        "requests_processed": recommendation_stats["requests"],
        "timestamp": datetime.now().isoformat()
    })

@app.route('/recommendations', methods=['POST'])
def get_recommendations():
    """
    Generate product recommendations based on user preferences.
    Uses rule-based logic instead of AI.
    """
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("recommendation_service.generate") as span:
            span.set_attribute("service.component", "recommendation_service")
            span.set_attribute("service.name", "recommendation-service")
            
            # Get request data
            data = request.get_json() or {}
            user_id = data.get("user_id", "anonymous")
            user_context = data.get("user_context", "")
            category = data.get("category", "electronics")
            price_range = data.get("price_range", [0, 1000])
            
            span.set_attribute("user.id", user_id)
            span.set_attribute("recommendation.category", category)
            span.set_attribute("recommendation.price_min", price_range[0])
            span.set_attribute("recommendation.price_max", price_range[1])
            
            recommendation_stats["requests"] += 1
            
            # Call product catalog service to get actual products
            with tracer.start_as_current_span("recommendation_service.get_products") as product_span:
                headers = propagate_trace_context()
                
                try:
                    response = requests.get(
                        f"{PRODUCT_CATALOG_URL}/products",
                        params={
                            "category": category,
                            "price_min": price_range[0],
                            "price_max": price_range[1]
                        },
                        headers=headers,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        product_data = response.json()
                        products = product_data.get("products", []) if isinstance(product_data, dict) else []
                        
                        product_span.set_attribute("products.found", len(products))
                        
                        # Generate simple recommendations
                        recommendations = []
                        for product in products[:5]:  # Top 5 products
                            recommendations.append({
                                "product_id": product.get("id"),
                                "product_name": product.get("name"),
                                "price": product.get("price"),
                                "reason": f"Popular in {category} category",
                                "relevance_score": random.uniform(0.7, 0.95)
                            })
                        
                        span.set_attribute("recommendations.count", len(recommendations))
                        span.set_attribute("recommendations.success", True)
                        
                        recommendation_stats["successful"] += 1
                        
                        return jsonify({
                            "success": True,
                            "user_id": user_id,
                            "recommendations": recommendations,
                            "based_on": {
                                "category": category,
                                "price_range": price_range,
                                "user_context": user_context
                            }
                        }), 200
                    
                    else:
                        product_span.set_status(Status(StatusCode.ERROR))
                        recommendation_stats["failed"] += 1
                        
                        return jsonify({
                            "success": False,
                            "error": f"Product service error: {response.status_code}"
                        }), 500
                        
                except Exception as e:
                    product_span.set_status(Status(StatusCode.ERROR, str(e)))
                    recommendation_stats["failed"] += 1
                    
                    return jsonify({
                        "success": False,
                        "error": f"Failed to fetch products: {str(e)}"
                    }), 500
                    
    except Exception as e:
        recommendation_stats["failed"] += 1
        print(f"❌ Error in get_recommendations: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
        
    finally:
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    return jsonify({
        **recommendation_stats,
        "uptime_seconds": (datetime.now() - recommendation_stats["start_time"]).total_seconds()
    }), 200

if __name__ == '__main__':
    print("🎯 Recommendation Service (Rule-Based) starting on port 8011...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Product Catalog URL: {PRODUCT_CATALOG_URL}")
    app.run(host='0.0.0.0', port=8011, debug=False)

