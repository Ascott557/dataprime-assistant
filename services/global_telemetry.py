#!/usr/bin/env python3
"""
🔧 Global Telemetry Configuration - Single Source of Truth
This module provides a single, consistent telemetry configuration for all services.
"""

import os
from opentelemetry import trace
from dotenv import load_dotenv

# Load environment variables once
load_dotenv()

# Global telemetry state
_telemetry_initialized = False
_global_tracer = None

def initialize_global_telemetry():
    """Initialize telemetry ONCE for the entire distributed system."""
    global _telemetry_initialized, _global_tracer
    
    if _telemetry_initialized:
        print("✅ Telemetry already initialized globally")
        return True
    
    try:
        print("🔧 Initializing SINGLE telemetry configuration for distributed system...")
        
        # Import telemetry libraries
        from llm_tracekit import setup_export_to_coralogix, OpenAIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        
        # Single service name for ALL components
        service_name = "dataprime_distributed_system"
        
        # Setup Coralogix export ONCE
        setup_export_to_coralogix(
            service_name=service_name,  # SAME for all services
            application_name="ai-dataprime-enterprise", 
            subsystem_name="distributed-microservices",  # Single subsystem
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=os.getenv('CX_ENDPOINT', 'https://ingress.coralogix.com/api/v1/otel/v1/traces'),
            capture_content=True
        )
        print("✅ Coralogix export configured with single service identity")
        
        # Instrument libraries ONCE
        OpenAIInstrumentor().instrument()
        print("✅ OpenAI instrumentation enabled globally")
        
        RequestsInstrumentor().instrument()
        print("✅ Requests instrumentation enabled globally")
        
        # Create single tracer for all services
        _global_tracer = trace.get_tracer("dataprime_distributed_system")
        print("✅ Global tracer created")
        
        _telemetry_initialized = True
        return True
        
    except Exception as e:
        print(f"❌ Global telemetry setup failed: {e}")
        print("⚠️  Services will continue without telemetry export...")
        return False

def get_global_tracer():
    """Get the global tracer instance - same for all services."""
    global _global_tracer
    
    if not _telemetry_initialized:
        initialize_global_telemetry()
    
    if _global_tracer is None:
        _global_tracer = trace.get_tracer("dataprime_distributed_system")
    
    return _global_tracer

def instrument_flask_app(app, service_name):
    """Instrument a Flask app with the global telemetry configuration."""
    if not _telemetry_initialized:
        initialize_global_telemetry()
    
    try:
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        FlaskInstrumentor().instrument_app(app)
        print(f"✅ Flask instrumentation enabled for {service_name}")
        return True
    except Exception as e:
        print(f"⚠️  Flask instrumentation failed for {service_name}: {e}")
        return False

def is_telemetry_enabled():
    """Check if telemetry is enabled."""
    return _telemetry_initialized
