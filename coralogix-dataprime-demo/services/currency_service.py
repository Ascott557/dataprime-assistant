#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Currency Service - Currency Conversion for E-commerce
Provides currency exchange rates and conversion with OpenTelemetry tracing.
"""

import os
import sys
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from opentelemetry import trace, context
from opentelemetry.trace import SpanKind
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

# Hardcoded exchange rates for demo (base: USD)
EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "JPY": 149.50,
    "CAD": 1.36,
    "AUD": 1.52,
    "CHF": 0.88,
    "CNY": 7.24
}

# Service stats
currency_stats = {
    "conversions": 0,
    "rate_requests": 0,
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
        "service": "currency-service",
        "telemetry_enabled": telemetry_enabled,
        "supported_currencies": list(EXCHANGE_RATES.keys()),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/rates', methods=['GET'])
def get_rates():
    """Get all exchange rates."""
    token = None
    
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("currency_service.get_rates") as span:
            span.set_attribute("service.component", "currency_service")
            span.set_attribute("service.name", "currency-service")
            
            currency_stats["rate_requests"] += 1
            
            return jsonify({
                "base": "USD",
                "rates": EXCHANGE_RATES,
                "timestamp": datetime.now().isoformat()
            })
            
    finally:
        if token:
            context.detach(token)

@app.route('/convert', methods=['POST'])
def convert_currency():
    """Convert amount between currencies."""
    token = None
    
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("currency_service.convert") as span:
            span.set_attribute("service.component", "currency_service")
            span.set_attribute("service.name", "currency-service")
            
            data = request.get_json() or {}
            amount = float(data.get("amount", 0))
            from_currency = data.get("from", "USD").upper()
            to_currency = data.get("to", "USD").upper()
            
            span.set_attribute("currency.amount", amount)
            span.set_attribute("currency.from", from_currency)
            span.set_attribute("currency.to", to_currency)
            
            if from_currency not in EXCHANGE_RATES or to_currency not in EXCHANGE_RATES:
                return jsonify({"error": "Unsupported currency"}), 400
            
            # Convert: amount * (to_rate / from_rate)
            converted = amount * (EXCHANGE_RATES[to_currency] / EXCHANGE_RATES[from_currency])
            
            span.set_attribute("currency.converted_amount", converted)
            currency_stats["conversions"] += 1
            
            return jsonify({
                "amount": amount,
                "from": from_currency,
                "to": to_currency,
                "converted": round(converted, 2),
                "rate": EXCHANGE_RATES[to_currency] / EXCHANGE_RATES[from_currency]
            })
            
    finally:
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    return jsonify({
        **currency_stats,
        "uptime_seconds": (datetime.now() - currency_stats["start_time"]).total_seconds()
    })

if __name__ == '__main__':
    print("💱 Currency Service starting on port 8018...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Supported currencies: {', '.join(EXCHANGE_RATES.keys())}")
    app.run(host='0.0.0.0', port=8018, debug=False)

