#!/usr/bin/env python3
"""Official LLM-tracekit compatible telemetry for AI Center"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

_telemetry_initialized = False

def ensure_telemetry_initialized():
    """Initialize telemetry using official LLM-tracekit patterns for AI Center."""
    global _telemetry_initialized
    
    if _telemetry_initialized:
        return True
        
    try:
        print("🔧 Initializing official LLM-tracekit telemetry for AI Center...")
        
        # Official LLM-tracekit imports
        from llm_tracekit import OpenAIInstrumentor, setup_export_to_coralogix
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
        from opentelemetry.instrumentation.flask import FlaskInstrumentor
        
        # Import GenAI semantic conventions (required for AI Center)
        try:
            # Try the official OpenAI instrumentation that was installed
            from opentelemetry.instrumentation.openai import OpenAIInstrumentor as OfficialOpenAIInstrumentor
            print("✅ Official OpenAI instrumentation available")
            genai_available = True
        except ImportError:
            try:
                # Fallback to standard semantic conventions
                from opentelemetry.semconv.trace import SpanAttributes
                print("✅ Standard semantic conventions available - using for AI Center compatibility")
                genai_available = True
            except ImportError:
                print("⚠️ No semantic conventions available - AI Center may not work")
                genai_available = False
        
        print("✅ All instrumentation imports successful")

        # OFFICIAL setup_export_to_coralogix configuration for AI Center
        setup_export_to_coralogix(
            service_name="dataprime_assistant",
            application_name="ai-dataprime", 
            subsystem_name="query-generator",
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=os.getenv('CX_ENDPOINT'),
            capture_content=True  # CRITICAL: Required for AI Center content visibility
        )
        print("✅ Coralogix export configured with AI Center support")

        # Official instrumentation order (CRITICAL)
        print("🔧 Applying official LLM-tracekit instrumentation...")
        
        # 1. OpenAI instrumentation FIRST (most important for AI Center)
        OpenAIInstrumentor().instrument()
        print("✅ OpenAI instrumentation enabled (AI Center ready)")
        
        # 2. Other instrumentation
        RequestsInstrumentor().instrument()
        SQLite3Instrumentor().instrument()  
        FlaskInstrumentor().instrument()
        print("✅ Supporting instrumentation enabled")
        
        # 3. Set environment variables for services
        os.environ['GENAI_SEMANTIC_CONVENTIONS_AVAILABLE'] = str(genai_available)
        os.environ['AI_CENTER_READY'] = 'true'
        
        _telemetry_initialized = True
        print("✅ LLM-tracekit telemetry fully initialized for AI Center")
        return True
        
    except Exception as e:
        print(f"❌ LLM-tracekit telemetry initialization failed: {e}")
        import traceback
        print(f"📋 Full error trace: {traceback.format_exc()}")
        return False

def get_ai_center_status():
    """Check if AI Center is ready."""
    return {
        "telemetry_initialized": _telemetry_initialized,
        "genai_available": os.getenv('GENAI_SEMANTIC_CONVENTIONS_AVAILABLE') == 'True',
        "ai_center_ready": os.getenv('AI_CENTER_READY') == 'true'
    }

def get_telemetry_status():
    """Get current telemetry initialization status."""
    return _telemetry_initialized
