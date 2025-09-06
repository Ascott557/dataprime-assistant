#!/usr/bin/env python3
import requests
import secrets

# Generate PROPER W3C compliant trace IDs
trace_id = secrets.token_hex(16)  # 32 hex chars
span_id = secrets.token_hex(8)    # 16 hex chars

print(f"🧪 TESTING WITH PROPER W3C FORMAT")
print(f"📋 Trace ID: {trace_id} (length: {len(trace_id)})")
print(f"📋 Span ID:  {span_id} (length: {len(span_id)})")

headers = {
    'traceparent': f'00-{trace_id}-{span_id}-01',
    'tracestate': f'parent={span_id}',
    'Content-Type': 'application/json'
}

print(f"📤 Headers: {headers['traceparent']}")

# Test query
print(f"\n1️⃣ Testing Query Generation:")
response = requests.post('http://localhost:8010/api/generate-query',
                        headers=headers,
                        json={'user_input': 'test proper w3c format'})

if response.status_code == 200:
    result = response.json()
    print(f"   Expected: {trace_id}")
    print(f"   Actual:   {result.get('trace_id')}")
    print(f"   MATCH: {result.get('trace_id') == trace_id}")
    print(f"   Type: {result.get('trace_type')}")
    print(f"   Root: {result.get('is_root_span')}")
    
    if result.get('trace_id') == trace_id:
        print(f"   ✅ SUCCESS: Trace propagation working!")
        
        # Test feedback with same headers
        print(f"\n2️⃣ Testing Feedback with Same Headers:")
        feedback_response = requests.post('http://localhost:8010/api/feedback',
                                        headers=headers,
                                        json={
                                            'user_input': 'test',
                                            'generated_query': 'test',
                                            'rating': 5
                                        })
        
        if feedback_response.status_code == 200:
            feedback_result = feedback_response.json()
            print(f"   Expected: {trace_id}")
            print(f"   Actual:   {feedback_result.get('trace_id')}")
            print(f"   MATCH: {feedback_result.get('trace_id') == trace_id}")
            print(f"   Type: {feedback_result.get('trace_type')}")
            print(f"   Root: {feedback_result.get('is_root_span')}")
            
            if feedback_result.get('trace_id') == trace_id:
                print(f"   ✅ Both operations in same trace!")
                print(f"   💡 Issue might be in span parent-child relationships, not trace joining")
            else:
                print(f"   ❌ Feedback creates different trace")
        
    else:
        print(f"   ❌ FAILED: API Gateway not joining traces properly")
        print(f"   💡 Backend trace extraction is broken")
else:
    print(f"   ❌ Query failed: {response.status_code}")
