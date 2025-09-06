#!/usr/bin/env python3
"""
🧪 Simple Local Trace Test
Test the single root span fix locally without complex dependencies.
"""

import os
import sys
import time
import requests
import json
import subprocess
from datetime import datetime

def start_simple_app():
    """Start the original app in a way that works locally."""
    print("🚀 Starting DataPrime Assistant...")
    
    # Start the app in background
    try:
        process = subprocess.Popen([
            sys.executable, "minimal_dataprime_app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Give it time to start
        time.sleep(5)
        
        # Check if it's running
        if process.poll() is None:
            print("✅ App started successfully")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ App failed to start:")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start app: {e}")
        return None

def test_single_root_span():
    """Test the single root span fix."""
    print("\n🧪 Testing Single Root Span Fix")
    print("=" * 40)
    
    # Test trace ID that we can easily find in Coralogix
    test_trace_id = "deadbeef12345678901234567890abcd"
    test_span_id = "1234567890abcdef"
    
    print(f"🔍 Test Trace ID: {test_trace_id}")
    print("   Look for this trace ID in Coralogix to verify single root span")
    
    # Test the app on port 8000 (where it actually runs)
    test_url = "http://localhost:8000/api/generate-query"
    
    headers = {
        'traceparent': f'00-{test_trace_id}-{test_span_id}-01',
        'Content-Type': 'application/json'
    }
    
    test_data = {
        "user_input": "Show me errors from last hour - SINGLE ROOT SPAN TEST"
    }
    
    try:
        print(f"\n📡 Making request to: {test_url}")
        print(f"🔗 With trace header: {headers['traceparent']}")
        
        start_time = time.time()
        response = requests.post(test_url, json=test_data, headers=headers, timeout=30)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000
        
        print(f"⏱️ Response time: {response_time:.1f}ms")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Request successful!")
            print(f"   Generated query: {data.get('query', 'N/A')[:80]}...")
            print(f"   Intent: {data.get('intent', 'unknown')}")
            print(f"   Intent confidence: {data.get('intent_confidence', 0)*100:.1f}%")
            
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - app might not be running on port 8000")
        print("   Try checking if the app started correctly")
        return False
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False

def check_app_health():
    """Quick health check."""
    print("\n🏥 Health Check")
    print("-" * 20)
    
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ App is healthy")
            print(f"   Telemetry: {'Enabled' if data.get('telemetry_enabled') else 'Disabled'}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except:
        print("❌ App not responding on port 8000")
        return False

def main():
    """Main test function."""
    print("🧪 Simple Local Trace Test")
    print("=" * 50)
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    
    # Check if app is already running
    if check_app_health():
        print("✅ App is already running, proceeding with test...")
    else:
        print("🚀 App not running, starting it...")
        app_process = start_simple_app()
        if not app_process:
            print("❌ Failed to start app")
            return False
        
        # Wait a bit more and check again
        time.sleep(3)
        if not check_app_health():
            print("❌ App started but not responding")
            app_process.terminate()
            return False
    
    # Run the trace test
    success = test_single_root_span()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 LOCAL TEST PASSED!")
        print("\n🔍 What to check in Coralogix:")
        print("1. Search for trace ID: deadbeef12345678901234567890abcd")
        print("2. Verify you see ONE root span (not two separate spans)")
        print("3. Check that all operations appear as children of the root")
        print("4. Look for the requests instrumentation working on MCP calls")
        print("\n✅ The fix should resolve the two root spans issue!")
    else:
        print("❌ LOCAL TEST FAILED!")
        print("Check the error messages above for troubleshooting.")
    
    print("=" * 50)
    return success

if __name__ == '__main__':
    main()
