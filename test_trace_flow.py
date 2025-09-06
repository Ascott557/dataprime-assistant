#!/usr/bin/env python3
import requests
import json
import time

# Generate a user journey trace ID
trace_id = "87a3aa5cc629622d39b82fe3cfbbddaa"
span_id = "6872804a4c85579a"

headers = {
    'traceparent': f'00-{trace_id}-{span_id}-01',
    'tracestate': f'parent={span_id}',
    'Content-Type': 'application/json'
}

print(f"🔍 Testing user journey with trace ID: {trace_id}")
print(f"🔗 Root span ID: {span_id}")

# Step 1: Generate query
print("\n1️⃣ Generating query...")
response1 = requests.post('http://localhost:8010/api/generate-query', 
                         headers=headers,
                         json={'user_input': 'show me error logs from the last hour'})
result1 = response1.json()
print(f"   ✅ Query: {result1['success']}")
print(f"   📊 Trace Type: {result1.get('trace_type', 'unknown')}")
print(f"   🔍 Is Root: {result1.get('is_root_span', 'unknown')}")
print(f"   🆔 Trace ID: {result1.get('trace_id', 'unknown')}")

time.sleep(1)

# Step 2: Submit feedback - should join same trace
print("\n2️⃣ Submitting feedback...")
response2 = requests.post('http://localhost:8010/api/feedback',
                         headers=headers,
                         json={
                             'user_input': 'show me error logs from the last hour',
                             'generated_query': result1.get('query', ''),
                             'rating': 5,
                             'comment': 'Great query!'
                         })
result2 = response2.json()
print(f"   ✅ Feedback: {result2['success']}")
print(f"   📊 Trace Type: {result2.get('trace_type', 'unknown')}")
print(f"   🔍 Is Root: {result2.get('is_root_span', 'unknown')}") 
print(f"   🆔 Trace ID: {result2.get('trace_id', 'unknown')}")
print(f"   ✅ Should be child: {result2.get('should_be_child', 'unknown')}")

print(f"\n📋 SUMMARY:")
print(f"   Expected trace ID: {trace_id}")
print(f"   Query trace ID:    {result1.get('trace_id', 'N/A')}")
print(f"   Feedback trace ID: {result2.get('trace_id', 'N/A')}")
print(f"   Both same trace:   {result1.get('trace_id') == result2.get('trace_id')}")
print(f"   Both child spans:  {result1.get('trace_type') == 'child' and result2.get('trace_type') == 'child'}")
