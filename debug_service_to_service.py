#!/usr/bin/env python3

# Let's create a simple test server to see what headers the API Gateway sends
from flask import Flask, request, jsonify
import threading
import time
import requests

app = Flask(__name__)

received_headers = {}

@app.route('/debug-headers', methods=['POST'])
def debug_headers():
    global received_headers
    received_headers = dict(request.headers)
    print(f"🔍 RECEIVED HEADERS FROM API GATEWAY:")
    for key, value in received_headers.items():
        print(f"   {key}: {value}")
    
    # Check for trace headers specifically
    traceparent = received_headers.get('traceparent') or received_headers.get('Traceparent')
    tracestate = received_headers.get('tracestate') or received_headers.get('Tracestate')
    
    print(f"\n📋 TRACE HEADERS:")
    print(f"   traceparent: {traceparent}")
    print(f"   tracestate: {tracestate}")
    
    return jsonify({"headers_received": len(received_headers)})

# Start debug server in background
def run_debug_server():
    app.run(host='127.0.0.1', port=9999, debug=False)

print(f"🚀 Starting debug server on port 9999...")
server_thread = threading.Thread(target=run_debug_server, daemon=True)
server_thread.start()
time.sleep(1)

# Now test: send trace to API Gateway and see what it forwards
trace_id = "aabbccdd112233445566778899aabbcc"
span_id = "1122334455667788"

headers = {
    'traceparent': f'00-{trace_id}-{span_id}-01',
    'Content-Type': 'application/json'
}

print(f"\n📤 SENDING TO API GATEWAY:")
print(f"   traceparent: {headers['traceparent']}")

# Modify the query service URL temporarily to point to our debug server
print(f"\n⚠️ NOTE: This test would require temporarily modifying the API Gateway")
print(f"   to send requests to port 9999 instead of the real query service")
print(f"   But we can still test the format...")

# Instead, let's test the Query Service's extraction directly
print(f"\n🧠 TESTING QUERY SERVICE EXTRACTION:")
query_response = requests.post('http://localhost:8011/generate',
                             headers=headers,
                             json={'user_input': 'debug headers test'})

if query_response.status_code == 200:
    query_result = query_response.json()
    print(f"   Query service responds successfully")
    print(f"   Returns trace info: {'trace_id' in query_result}")
    
    # The key question: Is the Query Service creating a new trace or joining the existing one?
    print(f"\n🔍 KEY ISSUE ANALYSIS:")
    print(f"   1. API Gateway properly joins trace: {trace_id}")
    print(f"   2. API Gateway sends headers to Query Service")
    print(f"   3. Query Service extraction fails -> creates NEW trace")
    print(f"   4. OpenAI calls happen in Query Service's NEW trace") 
    print(f"   5. Result: Disconnected traces in Coralogix")
else:
    print(f"   Query service error: {query_response.status_code}")

print(f"\n💡 SOLUTION: Fix Query Service trace context extraction")
print(f"   Copy the robust extraction logic from API Gateway to Query Service")
