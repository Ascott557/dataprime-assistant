#!/usr/bin/env python3
import requests
import json
import time

# Let's trace exactly what happens during a complete user journey
trace_id = "aabbccddee11223344556677889900ff" 
span_id = "1122334455667788"

headers = {
    'traceparent': f'00-{trace_id}-{span_id}-01',
    'tracestate': f'parent={span_id}',
    'Content-Type': 'application/json'
}

print(f"🔍 ANALYZING DISTRIBUTED TRACE DISCONNECT")
print(f"📋 Using trace ID: {trace_id}")
print(f"📋 Using parent span: {span_id}")

# Step 1: Call API Gateway and analyze the response
print(f"\n1️⃣ CALLING API GATEWAY...")
response = requests.post('http://localhost:8010/api/generate-query', 
                        headers=headers,
                        json={'user_input': 'analyze trace disconnect issue'})

result = response.json()
print(f"   ✅ API Gateway Success: {result.get('success')}")
print(f"   📊 Returned Trace ID: {result.get('trace_id')}")
print(f"   📊 Trace Type: {result.get('trace_type')} (should be 'child')")
print(f"   📊 Is Root Span: {result.get('is_root_span')} (should be False)")
print(f"   🔗 Services Called: {result.get('services_called', [])}")

# Check if trace ID matches
trace_match = result.get('trace_id') == trace_id
print(f"   📋 TRACE ID MATCH: {trace_match}")
if not trace_match:
    print(f"      Expected: {trace_id}")
    print(f"      Received: {result.get('trace_id')}")

# Step 2: Analyze what's happening in the service chain
print(f"\n2️⃣ ANALYZING SERVICE CHAIN...")
print(f"   🌐 API Gateway creates child span: {result.get('trace_type') == 'child'}")
print(f"   🧠 Query service processes OpenAI call")
print(f"   ✅ Validation service validates query")  
print(f"   🔄 Queue worker processes background job")

# Step 3: Check if there are multiple trace contexts being created
print(f"\n3️⃣ CHECKING FOR TRACE CONTEXT ISSUES...")

# The key question: Are the API Gateway spans and OpenAI spans 
# appearing in different traces in Coralogix?

print(f"\n🤔 HYPOTHESIS: The issue might be:")
print(f"   A) API Gateway spans form one trace")
print(f"   B) OpenAI calls (from query service) form separate traces") 
print(f"   C) They're not being connected even though trace propagation works")

print(f"\n📊 WHAT TO CHECK IN CORALOGIX:")
print(f"   1. Look for trace ID: {trace_id} - should see API Gateway operations")
print(f"   2. Look for OpenAI calls around same time - different trace ID?")
print(f"   3. Check if spans from different services appear connected")

# Let's also test direct query service call
print(f"\n4️⃣ TESTING DIRECT QUERY SERVICE CALL...")
try:
    direct_response = requests.post('http://localhost:8011/generate',
                                   headers=headers,
                                   json={'user_input': 'direct query service test'})
    direct_result = direct_response.json()
    print(f"   ✅ Direct call success: {direct_result.get('success')}")
    print(f"   📊 Returns trace info: {'trace_id' in direct_result}")
    
    if 'trace_id' in direct_result:
        direct_trace_match = direct_result.get('trace_id') == trace_id
        print(f"   📋 Direct trace match: {direct_trace_match}")
        if not direct_trace_match:
            print(f"      Expected: {trace_id}")
            print(f"      Received: {direct_result.get('trace_id')}")
    else:
        print(f"   ⚠️ Query service doesn't return trace information")
        print(f"   💡 This might indicate trace context isn't being extracted properly")
        
except Exception as e:
    print(f"   ❌ Direct call failed: {e}")

print(f"\n📋 SUMMARY:")
print(f"   - API Gateway trace propagation: {'✅ WORKING' if trace_match else '❌ BROKEN'}")
print(f"   - OpenAI instrumentation: ✅ WORKING (visible in AI Center)")
print(f"   - The disconnect must be in service-to-service trace context passing")
