#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


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
        print("🔧 Initializing telemetry with LLM content capture + k8s enrichment...")
        
        from llm_tracekit import OpenAIInstrumentor
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        print("✅ llm_tracekit and OpenTelemetry SDK imports successful")
        
        # Get service metadata from environment
        service_name = os.getenv('SERVICE_NAME', 'dataprime_assistant')
        otel_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://coralogix-opentelemetry-collector:4317')
        
        print(f"🔧 Service: {service_name}")
        print(f"🔧 OTel Collector endpoint: {otel_endpoint}")
        print(f"🔧 Application: {os.getenv('CX_APPLICATION_NAME', 'dataprime-demo')}")
        print(f"🔧 Subsystem: {os.getenv('CX_SUBSYSTEM_NAME', 'ai-assistant')}")
        
        # Create resource with service identity and metadata
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv('SERVICE_VERSION', '1.0.0'),
            "deployment.environment": "production",
        })
        
        # Setup tracer provider with resource attributes
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Export to local OTel Collector using insecure gRPC
        otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        
        print("✅ OTLP exporter configured for local OTel Collector")
        
        # Enable content capture via environment variables BEFORE instrumenting
        # These environment variables control OpenTelemetry GenAI semantic conventions
        os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
        
        # Initialize OpenAI instrumentation
        # The instrumentor reads the environment variable above for content capture
        OpenAIInstrumentor().instrument()
        
        print("✅ OpenAI instrumentation enabled (content capture: OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true)")
        
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
