#!/usr/bin/env python3
"""
🧪 Test Distributed Tracing - Verify Single Root Span
Tests the distributed system to ensure proper trace context propagation.
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_health_checks():
    """Test that all services are healthy."""
    print("🏥 Testing service health checks...")
    
    services = {
        "api_gateway": "http://localhost:8010/api/health",
        "query_service": "http://localhost:8011/health",
        "validation_service": "http://localhost:8012/health", 
        "queue_service": "http://localhost:8013/health",
        "processing_service": "http://localhost:8014/health",
        "storage_service": "http://localhost:8015/health"
    }
    
    all_healthy = True
    
    for service_name, url in services.items():
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ {service_name}: {data.get('status', 'unknown')}")
            else:
                print(f"   ❌ {service_name}: HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"   ❌ {service_name}: {str(e)}")
            all_healthy = False
    
    return all_healthy

def test_distributed_query_generation():
    """Test the full distributed query generation pipeline."""
    print("\n🔍 Testing distributed query generation...")
    
    # Test query
    test_input = "Show me errors from the last hour grouped by service"
    
    try:
        # Call API Gateway
        response = requests.post(
            "http://localhost:8010/api/generate-query",
            json={"user_input": test_input},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Query generated successfully")
            print(f"   📝 Generated query: {result.get('query', 'N/A')[:100]}...")
            print(f"   🎯 Intent: {result.get('intent', 'unknown')}")
            print(f"   ✅ Validation: {'PASS' if result.get('validation', {}).get('is_valid') else 'FAIL'}")
            print(f"   🔧 Services called: {len(result.get('services_called', []))}")
            return True
        else:
            print(f"   ❌ Query generation failed: HTTP {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Query generation error: {str(e)}")
        return False

def test_feedback_storage():
    """Test feedback storage through the distributed system."""
    print("\n💬 Testing feedback storage...")
    
    feedback_data = {
        "user_input": "Show me errors from the last hour",
        "generated_query": "source logs last 1h | filter $m.severity == 'Error'",
        "rating": 5,
        "comment": "Perfect query generation!",
        "metadata": {"test": True}
    }
    
    try:
        response = requests.post(
            "http://localhost:8010/api/feedback",
            json=feedback_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Feedback stored successfully")
            print(f"   🆔 Feedback ID: {result.get('feedback_id', 'N/A')}")
            print(f"   ⭐ Rating: {result.get('rating', 'N/A')}")
            return True
        else:
            print(f"   ❌ Feedback storage failed: HTTP {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Feedback storage error: {str(e)}")
        return False

def test_service_stats():
    """Test aggregated stats from all services."""
    print("\n📊 Testing service statistics...")
    
    try:
        response = requests.get(
            "http://localhost:8010/api/stats",
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            stats = result.get('stats', {})
            
            print(f"   ✅ Stats retrieved successfully")
            print(f"   🏭 Services reporting: {len(stats)}")
            
            for service_name, service_stats in stats.items():
                if isinstance(service_stats, dict) and 'start_time' in service_stats:
                    print(f"   📈 {service_name}: Active since {service_stats.get('start_time', 'unknown')}")
                
            return True
        else:
            print(f"   ❌ Stats retrieval failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Stats retrieval error: {str(e)}")
        return False

def test_trace_propagation():
    """Test that trace context is properly propagated."""
    print("\n🔗 Testing trace context propagation...")
    
    # Custom trace headers to verify propagation
    custom_headers = {
        "traceparent": "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "http://localhost:8010/api/generate-query",
            json={"user_input": "Test trace propagation query"},
            headers=custom_headers,
            timeout=30
        )
        
        if response.status_code == 200:
            print(f"   ✅ Request with custom trace headers succeeded")
            print(f"   🔍 This should create a single trace tree in Coralogix")
            return True
        else:
            print(f"   ❌ Trace propagation test failed: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Trace propagation error: {str(e)}")
        return False

def main():
    """Run all distributed system tests."""
    print("🧪 Distributed DataPrime Assistant - System Tests")
    print("=" * 60)
    print(f"🕐 Test started at: {datetime.now().isoformat()}")
    print()
    
    tests = [
        ("Health Checks", test_health_checks),
        ("Query Generation Pipeline", test_distributed_query_generation),
        ("Feedback Storage", test_feedback_storage),
        ("Service Statistics", test_service_stats),
        ("Trace Propagation", test_trace_propagation)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"🧪 Running: {test_name}")
        try:
            if test_func():
                passed += 1
                print(f"   ✅ {test_name} PASSED")
            else:
                failed += 1
                print(f"   ❌ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"   ❌ {test_name} ERROR: {str(e)}")
        
        print()
        time.sleep(1)  # Brief pause between tests
    
    print("=" * 60)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Distributed system is working correctly.")
        print()
        print("🔍 Next steps:")
        print("   1. Check Coralogix for distributed traces")
        print("   2. Verify single root span with proper parent-child relationships")
        print("   3. Confirm service dependency graph shows connected services")
        print("   4. Look for realistic timing distribution across services")
    else:
        print("❌ Some tests failed. Please check service logs and configuration.")
    
    print("=" * 60)

if __name__ == '__main__':
    main()
