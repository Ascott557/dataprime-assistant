#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Ad Service - Advertisement Service for E-commerce
Serves targeted advertisements with OpenTelemetry tracing.
"""

import os
import sys
import random
from datetime import datetime
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

# Sample ads database
ADS = [
    {"id": 1, "title": "Premium Headphones Sale", "category": "electronics", "ctr": 0.05},
    {"id": 2, "title": "Summer Furniture Collection", "category": "furniture", "ctr": 0.03},
    {"id": 3, "title": "Fitness Equipment Special", "category": "sports", "ctr": 0.04},
    {"id": 4, "title": "Smart Home Devices", "category": "electronics", "ctr": 0.06},
    {"id": 5, "title": "Kitchen Appliances Deal", "category": "appliances", "ctr": 0.045}
]

# Service stats
ad_stats = {
    "impressions": 0,
    "clicks": 0,
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
        "service": "ad-service",
        "telemetry_enabled": telemetry_enabled,
        "total_ads": len(ADS),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/ads', methods=['GET'])
def get_ads():
    """Get targeted ads based on category."""
    token = None
    
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("ad_service.get_ads") as span:
            span.set_attribute("service.component", "ad_service")
            span.set_attribute("service.name", "ad-service")
            
            category = request.args.get('category', 'all')
            limit = int(request.args.get('limit', 3))
            
            span.set_attribute("ad.category", category)
            span.set_attribute("ad.limit", limit)
            
            # Filter ads by category if specified
            if category != 'all':
                filtered_ads = [ad for ad in ADS if ad["category"] == category]
            else:
                filtered_ads = ADS
            
            # Select random ads up to limit
            selected_ads = random.sample(filtered_ads, min(limit, len(filtered_ads)))
            
            span.set_attribute("ad.served_count", len(selected_ads))
            ad_stats["impressions"] += len(selected_ads)
            
            return jsonify({
                "ads": selected_ads,
                "count": len(selected_ads)
            })
            
    finally:
        if token:
            context.detach(token)

@app.route('/ads/<int:ad_id>/click', methods=['POST'])
def record_click(ad_id):
    """Record an ad click."""
    token = None
    
    try:
        token, is_root = extract_and_attach_trace_context()
        
        with tracer.start_as_current_span("ad_service.record_click") as span:
            span.set_attribute("service.component", "ad_service")
            span.set_attribute("service.name", "ad-service")
            span.set_attribute("ad.id", ad_id)
            
            ad = next((a for a in ADS if a["id"] == ad_id), None)
            
            if not ad:
                return jsonify({"error": "Ad not found"}), 404
            
            ad_stats["clicks"] += 1
            
            span.set_attribute("ad.title", ad["title"])
            
            return jsonify({
                "success": True,
                "ad_id": ad_id,
                "message": "Click recorded"
            })
            
    finally:
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    ctr = (ad_stats["clicks"] / ad_stats["impressions"]) if ad_stats["impressions"] > 0 else 0
    
    return jsonify({
        **ad_stats,
        "ctr": round(ctr, 4),
        "uptime_seconds": (datetime.now() - ad_stats["start_time"]).total_seconds()
    })

if __name__ == '__main__':
    print("📺 Ad Service starting on port 8017...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   Total ads available: {len(ADS)}")
    app.run(host='0.0.0.0', port=8017, debug=False)

