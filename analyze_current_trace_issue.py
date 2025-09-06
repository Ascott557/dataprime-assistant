#!/usr/bin/env python3
import requests
import json

print("🔍 ANALYZING CURRENT TRACE STRUCTURE ISSUE")
print("="*60)

# Generate a test trace to understand the current behavior
trace_id = "test94ac1ac2166371c52329871dfc5c0bce"
session_span_id = "test123456789012"

print(f"🧪 Testing with controlled trace IDs:")
print(f"   Trace ID: {trace_id}")
print(f"   Session Span ID: {session_span_id}")

# Test 1: Generate Query
print(f"\n1️⃣ TESTING QUERY GENERATION:")
query_headers = {
    'traceparent': f'00-{trace_id}-{session_span_id}-01',
    'tracestate': f'parent={session_span_id}',
    'Content-Type': 'application/json'
}

query_response = requests.post('http://localhost:8010/api/generate-query',
                              headers=query_headers,
                              json={'user_input': 'test current trace structure'})

if query_response.status_code == 200:
    query_result = query_response.json()
    print(f"   ✅ Query Success: {query_result.get('success')}")
    print(f"   📊 Returned Trace ID: {query_result.get('trace_id')}")
    print(f"   📊 Trace Type: {query_result.get('trace_type')}")
    print(f"   📊 Is Root: {query_result.get('is_root_span')}")
    print(f"   🔍 Trace Match: {query_result.get('trace_id') == trace_id}")
    
    # Check if query response includes span ID for chaining
    response_keys = list(query_result.keys())
    print(f"   📋 Response Keys: {response_keys}")
    if 'span_id' in query_result:
        query_span_id = query_result['span_id']
        print(f"   🔗 Query Span ID: {query_span_id}")
    else:
        print(f"   ⚠️ No span_id in response - can't chain operations")
        query_span_id = None
else:
    print(f"   ❌ Query failed: {query_response.status_code}")
    query_span_id = None

# Test 2: Submit Feedback with same session span
print(f"\n2️⃣ TESTING FEEDBACK SUBMISSION:")
feedback_headers = {
    'traceparent': f'00-{trace_id}-{session_span_id}-01',  # Same parent as query
    'tracestate': f'parent={session_span_id}',
    'Content-Type': 'application/json'
}

feedback_response = requests.post('http://localhost:8010/api/feedback',
                                 headers=feedback_headers,
                                 json={
                                     'user_input': 'test current trace structure',
                                     'generated_query': 'test query',
                                     'rating': 5,
                                     'comment': 'testing'
                                 })

if feedback_response.status_code == 200:
    feedback_result = feedback_response.json()
    print(f"   ✅ Feedback Success: {feedback_result.get('success')}")
    print(f"   📊 Returned Trace ID: {feedback_result.get('trace_id')}")
    print(f"   📊 Trace Type: {feedback_result.get('trace_type')}")
    print(f"   📊 Is Root: {feedback_result.get('is_root_span')}")
    print(f"   📊 Should Be Child: {feedback_result.get('should_be_child')}")
    print(f"   🔍 Trace Match: {feedback_result.get('trace_id') == trace_id}")
else:
    print(f"   ❌ Feedback failed: {feedback_response.status_code}")

# Analysis
print(f"\n🤔 ANALYSIS:")
print(f"Both operations using same parent span ID: {session_span_id}")
print(f"Expected result: Two child spans under same parent")
print(f"\n💡 POSSIBLE ISSUES:")
print(f"1. API Gateway creates spans but doesn't report span IDs back")
print(f"2. Frontend can't maintain proper parent-child chains")
print(f"3. Services create separate contexts even with same parent")
print(f"4. W3C trace propagation isn't creating proper hierarchy")

print(f"\n🔧 INVESTIGATION NEEDED:")
print(f"1. Check if API Gateway returns span IDs in responses")
print(f"2. Verify how services handle identical parent span IDs") 
print(f"3. Look at actual span creation in API Gateway")
print(f"4. Check if timing affects trace structure")
