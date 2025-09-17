#!/usr/bin/env python3
"""Working telemetry - exactly like the successful direct test"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

_telemetry_initialized = False

def ensure_telemetry_initialized():
    """Initialize telemetry exactly like the successful direct test."""
    global _telemetry_initialized
    
    if _telemetry_initialized:
        return True
        
    try:
        print("🔧 Initializing telemetry like successful direct test...")
        
        # Import only what we know works
        from llm_tracekit import OpenAIInstrumentor, setup_export_to_coralogix
        print("✅ llm_tracekit imports successful")
        
        # Setup Coralogix export with proper regional endpoint configuration
        # Based on: https://coralogix.com/blog/everything-you-need-to-know-about-the-new-coralogix-endpoints/
        cx_domain = os.getenv('CX_DOMAIN', 'eu2.coralogix.com')
        
        # Map domains to correct ingress endpoints with port 443
        if cx_domain == 'us1.coralogix.com':
            cx_endpoint = 'https://ingress.us1.coralogix.com:443'
        elif cx_domain == 'us2.coralogix.com':
            cx_endpoint = 'https://ingress.us2.coralogix.com:443'
        elif cx_domain == 'eu1.coralogix.com':
            cx_endpoint = 'https://ingress.eu1.coralogix.com:443'
        elif cx_domain == 'eu2.coralogix.com':
            cx_endpoint = 'https://ingress.eu2.coralogix.com:443'
        elif cx_domain == 'ap1.coralogix.com':
            cx_endpoint = 'https://ingress.ap1.coralogix.com:443'
        elif cx_domain == 'ap2.coralogix.com':
            cx_endpoint = 'https://ingress.ap2.coralogix.com:443'
        elif cx_domain == 'ap3.coralogix.com':
            cx_endpoint = 'https://ingress.ap3.coralogix.com:443'
        # Legacy domain support (deprecated)
        elif cx_domain == 'coralogix.com':
            cx_endpoint = 'https://ingress.eu1.coralogix.com:443'  # EU1 default
        elif cx_domain == 'coralogix.us':
            cx_endpoint = 'https://ingress.us1.coralogix.com:443'  # US1 default
        elif cx_domain == 'coralogix.in':
            cx_endpoint = 'https://ingress.ap1.coralogix.com:443'  # AP1 default
        elif cx_domain == 'coralogixsg.com':
            cx_endpoint = 'https://ingress.ap2.coralogix.com:443'  # AP2 default
        else:
            # Default to EU2 for new installations
            cx_endpoint = 'https://ingress.eu2.coralogix.com:443'
            
        print(f"🔧 Using Coralogix endpoint: {cx_endpoint}")
        print(f"🔧 Application: {os.getenv('CX_APPLICATION_NAME', 'dataprime-demo')}")
        print(f"🔧 Subsystem: {os.getenv('CX_SUBSYSTEM_NAME', 'ai-assistant')}")
        
        setup_export_to_coralogix(
            service_name="dataprime_assistant",
            application_name=os.getenv('CX_APPLICATION_NAME', 'dataprime-demo'),
            subsystem_name=os.getenv('CX_SUBSYSTEM_NAME', 'ai-assistant'),
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=cx_endpoint,
            capture_content=True
        )
        print("✅ Coralogix export configured")
        
        # Initialize OpenAI instrumentation (this is what matters for AI Center)
        OpenAIInstrumentor().instrument()
        print("✅ OpenAI instrumentation enabled")
        
        # Try to add other instrumentation if available, but don't fail if not
        try:
            from opentelemetry.instrumentation.requests import RequestsInstrumentor
            RequestsInstrumentor().instrument()
            print("✅ Requests instrumentation enabled")
        except ImportError:
            print("⚠️ Requests instrumentation not available - continuing without it")
            
        # 🔥 REMOVED Flask auto-instrumentation - it creates automatic root spans
        # This was causing every HTTP request to become a separate root trace
        print("🚫 Flask auto-instrumentation DISABLED for manual trace control")
            
        try:
            from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
            SQLite3Instrumentor().instrument()
            print("✅ SQLite instrumentation enabled")
        except ImportError:
            print("⚠️ SQLite instrumentation not available - continuing without it")
        
        _telemetry_initialized = True
        print("✅ Telemetry initialized successfully (minimal working version)")
        return True
        
    except Exception as e:
        print(f"❌ Telemetry initialization failed: {e}")
        import traceback
        print(f"📋 Full error trace: {traceback.format_exc()}")
        return False

def get_telemetry_status():
    """Get current telemetry initialization status."""
    return _telemetry_initialized
