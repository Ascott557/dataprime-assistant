#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Shipping Service - Shipping Calculation for E-commerce
Calculates shipping costs and delivery estimates with OpenTelemetry tracing.
"""

import os
import sys
import random
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry
telemetry_enabled = ensure_telemetry_initialized()
tracer = trace.get_tracer(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Shipping methods with base costs
SHIPPING_METHODS = {
    "standard": {"name": "Standard Shipping", "base_cost": 5.99, "days": "5-7"},
    "express": {"name": "Express Shipping", "base_cost": 12.99, "days": "2-3"},
    "overnight": {"name": "Overnight Shipping", "base_cost": 24.99, "days": "1"}
}

# Service stats
shipping_stats = {
    "calculations": 0,
    "start_time": datetime.now()
}

def extract_and_attach_trace_context():
    """Extract trace context from incoming request."""
    try:
        headers = dict(request.headers)
        propagator = TraceContextTextMapPropagator()
        incoming_context = propagator.extract(headers)
        
        if incoming_context:
            token = context.attach(incoming_context)
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                return token, False
            context.detach(token)
        
        return None, True
    except Exception as e:
        print(f"⚠️ Trace context extraction failed: {e}")
        return None, True

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "shipping-service",
        "telemetry_enabled": telemetry_enabled,
        "shipping_methods": list(SHIPPING_METHODS.keys()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/calculate', methods=['POST'])
def calculate_shipping():
    """Calculate shipping cost and delivery estimate."""
    token = None
    
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("shipping_service.calculate") as span:
            span.set_attribute("service.component", "shipping_service")
            span.set_attribute("service.name", "shipping-service")
            
            data = request.get_json() or {}
            weight = float(data.get("weight", 1.0))  # kg
            destination = data.get("destination", "domestic")
            method = data.get("method", "standard")
            
            span.set_attribute("shipping.weight", weight)
            span.set_attribute("shipping.destination", destination)
            span.set_attribute("shipping.method", method)
            
            if method not in SHIPPING_METHODS:
                return jsonify({"error": "Invalid shipping method"}), 400
            
            # Calculate cost based on weight and destination
            base_cost = SHIPPING_METHODS[method]["base_cost"]
            weight_surcharge = max(0, (weight - 2.0) * 2.00)  # $2 per kg over 2kg
            destination_multiplier = 1.5 if destination == "international" else 1.0
            
            total_cost = (base_cost + weight_surcharge) * destination_multiplier
            
            # Estimate delivery date
            delivery_days = SHIPPING_METHODS[method]["days"]
            estimated_delivery = (datetime.now() + timedelta(days=int(delivery_days.split('-')[0]))).strftime('%Y-%m-%d')
            
            span.set_attribute("shipping.cost", total_cost)
            span.set_attribute("shipping.delivery_date", estimated_delivery)
            
            shipping_stats["calculations"] += 1
            
            return jsonify({
                "method": SHIPPING_METHODS[method]["name"],
                "cost": round(total_cost, 2),
                "estimated_days": delivery_days,
                "estimated_delivery": estimated_delivery,
                "weight": weight,
                "destination": destination
            })
            
    finally:
        if token:
            context.detach(token)

@app.route('/methods', methods=['GET'])
def get_shipping_methods():
    """Get available shipping methods."""
    token = None
    
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("shipping_service.get_methods") as span:
            span.set_attribute("service.component", "shipping_service")
            span.set_attribute("service.name", "shipping-service")
            
            return jsonify({
                "methods": SHIPPING_METHODS
            })
            
    finally:
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    return jsonify({
        **shipping_stats,
        "uptime_seconds": (datetime.now() - shipping_stats["start_time"]).total_seconds()
    })

if __name__ == '__main__':
    print("📦 Shipping Service starting on port 8019...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Shipping methods: {', '.join(SHIPPING_METHODS.keys())}")
    app.run(host='0.0.0.0', port=8019, debug=False)

