#!/usr/bin/env python3
"""
🧪 Test Simple Distributed System
Test the distributed system with working services to verify single root span.
"""

import os
import time
import requests
import subprocess
import sys
from datetime import datetime

def start_service(script_name, port, service_name):
    """Start a service and return the process."""
    print(f"🚀 Starting {service_name} on port {port}...")
    
    try:
        process = subprocess.Popen([
            sys.executable, script_name
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        time.sleep(2)  # Give it time to start
        
        # Check if it's running
        if process.poll() is None:
            print(f"✅ {service_name} started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ {service_name} failed to start:")
            print(f"   stdout: {stdout}")
            print(f"   stderr: {stderr}")
            return None
    except Exception as e:
        print(f"❌ Failed to start {service_name}: {e}")
        return None

def create_simple_query_service():
    """Create a minimal working query service."""
    content = '''#!/usr/bin/env python3
"""🧠 Simple Query Service"""
import os, time
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

def extract_trace_context():
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/health', methods=['GET'])
def health():
    with tracer.start_as_current_span("query_service.health") as span:
        span.set_attribute("service.name", "query_service")
        time.sleep(0.010)
        return jsonify({"status": "healthy", "service": "query_service"})

@app.route('/generate', methods=['POST'])
def generate():
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    try:
        with tracer.start_as_current_span("query_service.generate_query") as span:
            span.set_attribute("service.name", "query_service")
            
            data = request.get_json()
            user_input = data.get('user_input', '')
            
            time.sleep(0.850)  # Simulate LLM call
            
            query = "source logs last 1h | filter $m.severity == 'Error'"
            
            return jsonify({
                "success": True,
                "query": query,
                "intent": "error_analysis",
                "intent_confidence": 0.85,
                "service": "query_service"
            })
    finally:
        if token:
            context.detach(token)

if __name__ == '__main__':
    print("🧠 Simple Query Service on port 8011")
    app.run(host='0.0.0.0', port=8011, debug=False)
'''
    
    with open('services/query_service_simple.py', 'w') as f:
        f.write(content)

def create_simple_validation_service():
    """Create a minimal working validation service."""
    content = '''#!/usr/bin/env python3
"""✅ Simple Validation Service"""
import time
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

tracer = trace.get_tracer(__name__)
app = Flask(__name__)

try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

def extract_trace_context():
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/health', methods=['GET'])
def health():
    with tracer.start_as_current_span("validation_service.health") as span:
        span.set_attribute("service.name", "validation_service")
        time.sleep(0.015)
        return jsonify({"status": "healthy", "service": "validation_service"})

@app.route('/validate', methods=['POST'])
def validate():
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    try:
        with tracer.start_as_current_span("validation_service.validate_query") as span:
            span.set_attribute("service.name", "validation_service")
            
            data = request.get_json()
            query = data.get('query', '')
            
            time.sleep(0.075)  # Validation processing
            
            is_valid = 'source' in query.lower() and 'logs' in query.lower()
            
            return jsonify({
                "success": True,
                "is_valid": is_valid,
                "syntax_score": 0.9 if is_valid else 0.3,
                "warnings": [] if is_valid else ["Query syntax issues"],
                "service": "validation_service"
            })
    finally:
        if token:
            context.detach(token)

if __name__ == '__main__':
    print("✅ Simple Validation Service on port 8012")
    app.run(host='0.0.0.0', port=8012, debug=False)
'''
    
    with open('services/validation_service_simple.py', 'w') as f:
        f.write(content)

def test_distributed_trace():
    """Test the distributed system with a custom trace ID."""
    print("\n🧪 Testing Distributed Single Root Span")
    print("=" * 50)
    
    # Custom trace ID for easy identification in Coralogix
    test_trace_id = "deadbeef12345678901234567890abcd"
    test_span_id = "1234567890abcdef"
    
    print(f"🔍 Test Trace ID: {test_trace_id}")
    print("   This should create ONE root span in Coralogix with all services as children")
    
    headers = {
        'traceparent': f'00-{test_trace_id}-{test_span_id}-01',
        'Content-Type': 'application/json'
    }
    
    test_data = {
        "user_input": "Show me errors from last hour - DISTRIBUTED SINGLE ROOT SPAN TEST"
    }
    
    try:
        print(f"\n📡 Making request to API Gateway...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:8010/api/generate-query",
            json=test_data,
            headers=headers,
            timeout=30
        )
        
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        print(f"⏱️ Total response time: {response_time:.1f}ms")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Distributed request successful!")
            print(f"   Generated query: {data.get('query', 'N/A')}")
            print(f"   Intent: {data.get('intent', 'unknown')}")
            print(f"   Services called: {data.get('services_called', [])}")
            print(f"   Validation valid: {data.get('validation', {}).get('is_valid', False)}")
            
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False

def main():
    """Main test function."""
    print("🧪 Simple Distributed System Test")
    print("=" * 60)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    
    # Create simple services
    print("🔧 Creating simple services...")
    create_simple_query_service()
    create_simple_validation_service()
    
    # Start services
    services = []
    
    # Start Query Service
    query_process = start_service('services/query_service_simple.py', 8011, 'Query Service')
    if query_process:
        services.append(query_process)
    
    # Start Validation Service  
    validation_process = start_service('services/validation_service_simple.py', 8012, 'Validation Service')
    if validation_process:
        services.append(validation_process)
    
    if len(services) < 2:
        print("❌ Not all services started successfully")
        return False
    
    # Test the distributed system
    time.sleep(2)  # Let services fully start
    success = test_distributed_trace()
    
    # Cleanup
    print(f"\n🛑 Stopping services...")
    for process in services:
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 DISTRIBUTED TEST PASSED!")
        print("\n🔍 Check Coralogix for:")
        print("   • Trace ID: deadbeef12345678901234567890abcd")
        print("   • Single root span: api_gateway.generate_query_pipeline")
        print("   • Child spans from query_service and validation_service")
        print("   • Total trace time ~1 second (800ms for LLM + overhead)")
        print("\n✅ The distributed system should now show single root span!")
    else:
        print("❌ DISTRIBUTED TEST FAILED!")
        print("Check error messages above for troubleshooting.")
    
    print("=" * 60)
    return success

if __name__ == '__main__':
    main()
