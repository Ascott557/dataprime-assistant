#!/usr/bin/env python3
import requests
import secrets

# Generate proper W3C compliant trace IDs
def generate_trace_id():
    """Generate a proper 32-character hex trace ID"""
    return secrets.token_hex(16)  # 16 bytes = 32 hex characters

def generate_span_id():
    """Generate a proper 16-character hex span ID"""
    return secrets.token_hex(8)   # 8 bytes = 16 hex characters

trace_id = generate_trace_id()
span_id = generate_span_id()

print(f"🔍 TESTING WITH PROPER W3C TRACE FORMAT")
print(f"📋 Trace ID: {trace_id} (length: {len(trace_id)})")
print(f"📋 Span ID:  {span_id} (length: {len(span_id)})")

headers = {
    'traceparent': f'00-{trace_id}-{span_id}-01',
    'tracestate': f'parent={span_id}',
    'Content-Type': 'application/json'
}

print(f"📋 Headers: {headers['traceparent']}")

# Test API Gateway
print(f"\n🌐 TESTING API GATEWAY...")
response = requests.post('http://localhost:8010/api/generate-query',
                        headers=headers,
                        json={'user_input': 'test proper w3c format'})

result = response.json()
print(f"   Success: {result.get('success')}")
print(f"   Expected trace: {trace_id}")
print(f"   Actual trace:   {result.get('trace_id')}")
print(f"   MATCH: {result.get('trace_id') == trace_id}")
print(f"   Trace type: {result.get('trace_type')}")
print(f"   Is root: {result.get('is_root_span')}")

if result.get('trace_id') == trace_id:
    print(f"\n✅ SUCCESS! Trace context extraction is working!")
    print(f"   This means the issue was invalid trace ID format in previous tests")
else:
    print(f"\n❌ STILL FAILING - deeper issue with trace propagation")

# Test Query Service directly
print(f"\n🧠 TESTING QUERY SERVICE DIRECTLY...")
query_response = requests.post('http://localhost:8011/generate',
                              headers=headers,
                              json={'user_input': 'test proper w3c format'})
query_result = query_response.json()
print(f"   Success: {query_result.get('success')}")
print(f"   Has trace info: {'trace_id' in query_result}")
print(f"   Response keys: {list(query_result.keys())}")
