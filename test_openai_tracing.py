#!/usr/bin/env python3
import os
import sys
sys.path.append('.')
from shared_telemetry_working import ensure_telemetry_initialized
from openai import OpenAI
from opentelemetry import trace

# Initialize telemetry
print("🔧 Initializing telemetry...")
result = ensure_telemetry_initialized()
print(f"   Telemetry initialized: {result}")

# Get tracer
tracer = trace.get_tracer(__name__)

# Initialize OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

print("\n🤖 Testing OpenAI call with tracing...")

with tracer.start_as_current_span("test_openai_call") as span:
    span.set_attribute("test.operation", "openai_direct")
    
    # This should be automatically traced by LLM-tracekit
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Say 'Hello from traced OpenAI'"}],
        max_tokens=10
    )
    
    print(f"   Response: {response.choices[0].message.content}")
    print(f"   Span trace ID: {format(span.get_span_context().trace_id, '032x')}")

print("✅ Test completed - check Coralogix for the trace")
