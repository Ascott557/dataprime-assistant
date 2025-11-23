#!/usr/bin/env python3
"""
Payment Service - Simple payment gateway simulation
Part of V5 realistic e-commerce microservices architecture
"""

import os
import sys
import random
import time
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace import SpanKind, Status, StatusCode

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

def extract_and_attach_trace_context():
    """Extract trace context from incoming request."""
    try:
        from flask import request
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

# Initialize telemetry
telemetry_enabled = ensure_telemetry_initialized()
tracer = trace.get_tracer(__name__)

app = Flask(__name__)

# Service statistics
payment_stats = {
    "total_payments": 0,
    "successful_payments": 0,
    "failed_payments": 0,
    "total_amount_processed": 0.0
}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "payment-service",
        "telemetry_enabled": telemetry_enabled,
        "stats": payment_stats
    }), 200

@app.route('/api/payment/process', methods=['POST'])
def process_payment():
    """Process payment - simulates payment gateway (Stripe/PayPal)"""
    token = None
    
    try:
        # Extract and attach trace context
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("process_payment") as span:
            span.set_attribute("service.name", "payment-service")
            span.set_attribute("service.component", "payment_gateway")
            
            # Get payment data
            data = request.get_json() or {}
            amount = float(data.get("amount", 0.0))
            user_id = data.get("user_id", "unknown")
            payment_method = data.get("payment_method", "credit_card")
            
            # Set span attributes
            span.set_attribute("payment.amount", amount)
            span.set_attribute("payment.currency", "USD")
            span.set_attribute("payment.method", payment_method)
            span.set_attribute("user.id", user_id)
            
            # Validate amount
            if amount <= 0:
                span.set_status(Status(StatusCode.ERROR))
                span.set_attribute("error.type", "invalid_amount")
                payment_stats["failed_payments"] += 1
                return jsonify({
                    "status": "error",
                    "error": "Invalid payment amount"
                }), 400
            
            # Simulate payment gateway call (Stripe API)
            with tracer.start_as_current_span("payment_gateway_call", kind=SpanKind.CLIENT) as gateway_span:
                gateway_span.set_attribute("payment.gateway", "stripe")
                gateway_span.set_attribute("payment.gateway.endpoint", "https://api.stripe.com/v1/charges")
                gateway_span.set_attribute("payment.amount", amount)
                
                # Simulate network latency (100-200ms for payment gateway)
                gateway_delay = random.uniform(0.1, 0.2)
                time.sleep(gateway_delay)
                gateway_span.set_attribute("payment.gateway.latency_ms", int(gateway_delay * 1000))
                
                # Simulate 1% payment failure rate (declined cards, etc.)
                if random.random() < 0.01:
                    gateway_span.set_status(Status(StatusCode.ERROR))
                    span.set_status(Status(StatusCode.ERROR))
                    span.set_attribute("error.type", "payment_declined")
                    span.set_attribute("error.message", "Card declined by issuer")
                    payment_stats["total_payments"] += 1
                    payment_stats["failed_payments"] += 1
                    
                    return jsonify({
                        "status": "declined",
                        "error": "Payment declined by card issuer",
                        "amount": amount
                    }), 402  # Payment Required
            
            # Generate transaction ID
            transaction_id = f"txn-{random.randint(100000, 999999)}"
            
            # Update statistics
            payment_stats["total_payments"] += 1
            payment_stats["successful_payments"] += 1
            payment_stats["total_amount_processed"] += amount
            
            # Set success attributes
            span.set_attribute("payment.transaction_id", transaction_id)
            span.set_attribute("payment.status", "success")
            span.set_status(Status(StatusCode.OK))
            
            print(f"💳 Payment processed: ${amount:.2f} for user {user_id} - Transaction {transaction_id}")
            
            return jsonify({
                "status": "success",
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": "USD",
                "payment_method": payment_method,
                "timestamp": time.time()
            }), 200
    
    except Exception as e:
        if 'span' in locals():
            span.set_status(Status(StatusCode.ERROR))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
        
        payment_stats["total_payments"] += 1
        payment_stats["failed_payments"] += 1
        
        print(f"❌ Payment processing error: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
    
    finally:
        if token:
            context.detach(token)

@app.route('/api/payment/stats', methods=['GET'])
def get_stats():
    """Get payment service statistics"""
    return jsonify(payment_stats), 200

if __name__ == '__main__':
    print("💳 Payment Service starting on port 8017...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print("   Simulating Stripe payment gateway")
    app.run(host='0.0.0.0', port=8017, debug=False)

