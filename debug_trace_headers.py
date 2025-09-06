#!/usr/bin/env python3
import requests
import json

# Test what headers the API Gateway is sending to downstream services
trace_id = "12345678901234567890123456789012"
span_id = "1234567890123456"

headers = {
    'traceparent': f'00-{trace_id}-{span_id}-01',
    'tracestate': f'parent={span_id}',
    'Content-Type': 'application/json'
}

print(f"🔍 Testing API Gateway with trace headers:")
print(f"   traceparent: {headers['traceparent']}")
print(f"   tracestate: {headers['tracestate']}")

# Call API Gateway
response = requests.post('http://localhost:8010/api/generate-query', 
                        headers=headers,
                        json={'user_input': 'debug trace headers'})

result = response.json()
print(f"\n📊 API Gateway Response:")
print(f"   Success: {result.get('success')}")
print(f"   Trace Type: {result.get('trace_type')}")
print(f"   Is Root: {result.get('is_root_span')}")
print(f"   Trace ID: {result.get('trace_id')}")
print(f"   Expected: {trace_id}")
print(f"   Match: {result.get('trace_id') == trace_id}")

# Test calling query service directly
print(f"\n🧠 Testing Query Service directly:")
try:
    direct_response = requests.post('http://localhost:8011/generate',
                                   headers=headers, 
                                   json={'user_input': 'debug trace headers'})
    direct_result = direct_response.json()
    print(f"   Success: {direct_result.get('success')}")
    print(f"   Has trace info: {'trace_id' in direct_result}")
except Exception as e:
    print(f"   Error: {e}")
