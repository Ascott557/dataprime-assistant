#!/usr/bin/env python3
import requests

# Test the difference in trace context extraction between API Gateway and Query Service

trace_id = "test1234567890123456789012345678"
span_id = "test123456789012"

headers = {
    'traceparent': f'00-{trace_id}-{span_id}-01',
    'tracestate': f'parent={span_id}',
    'Content-Type': 'application/json'
}

print(f"🔍 COMPARING TRACE EXTRACTION")
print(f"📋 Test headers:")
print(f"   traceparent: {headers['traceparent']}")

# Test API Gateway (has robust manual extraction)
print(f"\n🌐 API GATEWAY EXTRACTION:")
api_response = requests.post('http://localhost:8010/api/generate-query',
                           headers=headers,
                           json={'user_input': 'test extraction'})
api_result = api_response.json()
print(f"   Extracts trace: {api_result.get('trace_id') == trace_id}")
print(f"   Creates child span: {api_result.get('trace_type') == 'child'}")
print(f"   Trace ID: {api_result.get('trace_id')}")

# Test Query Service directly (has simple extraction)
print(f"\n🧠 QUERY SERVICE EXTRACTION:")
query_response = requests.post('http://localhost:8011/generate',
                             headers=headers, 
                             json={'user_input': 'test extraction'})
query_result = query_response.json()
print(f"   Returns trace info: {'trace_id' in query_result}")
print(f"   Response keys: {list(query_result.keys())}")

# The hypothesis: Query Service's simple extraction fails where API Gateway's manual extraction succeeds
print(f"\n💡 HYPOTHESIS:")
print(f"   - API Gateway has manual trace context parsing that works")
print(f"   - Query Service only uses OpenTelemetry propagator which might fail")
print(f"   - OpenAI calls happen in Query Service with failed trace context")
print(f"   - Result: OpenAI calls create new root spans instead of joining existing trace")

# Let's check what headers the API Gateway actually sends to Query Service
print(f"\n🔍 Let's add some debugging to see what's happening...")
