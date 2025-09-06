#!/usr/bin/env python3
import requests
import json
import time

def generate_w3c_trace_id():
    """Generate a W3C compliant trace ID"""
    import random
    return ''.join([f'{random.randint(0, 15):x}' for _ in range(32)])

def generate_w3c_span_id():
    """Generate a W3C compliant span ID"""
    import random  
    return ''.join([f'{random.randint(0, 15):x}' for _ in range(16)])

# Simulate user session like the frontend
session_trace_id = generate_w3c_trace_id()
session_span_id = generate_w3c_span_id()

print(f"👤 Simulating user session")
print(f"🆔 Session trace ID: {session_trace_id}")
print(f"🔗 Session span ID: {session_span_id}")

# Simulate frontend headers (matching distributed_frontend.py)
headers = {
    'traceparent': f'00-{session_trace_id}-{session_span_id}-01',
    'tracestate': f'parent={session_span_id}', 
    'Content-Type': 'application/json'
}

# Simulate complete user journey
print("\n🚀 Starting user journey...")

# 1. User asks question
print("\n1️⃣ User asks question...")
query_response = requests.post('http://localhost:8010/api/generate-query',
                              headers=headers,
                              json={'user_input': 'Find errors in my application logs'})
query_result = query_response.json()

print(f"   Query generated: {query_result['success']}")
print(f"   Trace joined existing: {query_result.get('trace_type') == 'child'}")
print(f"   Services called: {', '.join(query_result.get('services_called', []))}")

# 2. User provides feedback (should be part of same trace)
print("\n2️⃣ User provides feedback...")
feedback_response = requests.post('http://localhost:8010/api/feedback', 
                                 headers=headers,
                                 json={
                                     'user_input': 'Find errors in my application logs',
                                     'generated_query': query_result.get('query', ''),
                                     'rating': 4,
                                     'comment': 'Good query, helpful results'
                                 })
feedback_result = feedback_response.json()

print(f"   Feedback submitted: {feedback_result['success']}") 
print(f"   Trace joined existing: {feedback_result.get('trace_type') == 'child'}")

# Final analysis
print(f"\n📊 DISTRIBUTED TRACE ANALYSIS:")
print(f"   Session trace ID:     {session_trace_id}")
print(f"   Query trace ID:       {query_result.get('trace_id', 'N/A')}")
print(f"   Feedback trace ID:    {feedback_result.get('trace_id', 'N/A')}")
print(f"   ✅ All same trace:    {session_trace_id == query_result.get('trace_id') == feedback_result.get('trace_id')}")
print(f"   ✅ No root spans:     {query_result.get('trace_type') == 'child' and feedback_result.get('trace_type') == 'child'}")
print(f"   ✅ Trace propagated:  {query_result.get('is_root_span') == False and feedback_result.get('is_root_span') == False}")

if session_trace_id == query_result.get('trace_id') == feedback_result.get('trace_id'):
    print("\n🎉 SUCCESS: Distributed tracing is working perfectly!")
    print("   - All operations join the user session trace")
    print("   - No separate root spans are created") 
    print("   - Feedback system correctly joins existing trace")
    print("   - Should appear as single connected trace in Coralogix AI Center")
else:
    print("\n❌ ISSUE: Trace IDs don't match - investigate further")
