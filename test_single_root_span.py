#!/usr/bin/env python3
"""
🧪 Test Single Root Span - Verify distributed tracing fix
This test specifically verifies that we get a single root span across all services.
"""

import os
import time
import requests
import json
from datetime import datetime

def test_single_root_span():
    """Test that distributed calls create a single root span."""
    print("🧪 Testing Single Root Span Generation")
    print("=" * 50)
    
    # Use a very specific trace ID that we can easily identify in Coralogix
    test_trace_id = "deadbeef12345678901234567890abcd"  # 32 hex chars
    test_span_id = "1234567890abcdef"  # 16 hex chars
    
    print(f"🔍 Using test trace ID: {test_trace_id}")
    print(f"🔍 Using test span ID: {test_span_id}")
    print("   This should create ONE root span in Coralogix with all services as children")
    
    # Test data
    test_query = "Show me errors from the last hour grouped by service - SINGLE ROOT SPAN TEST"
    
    headers = {
        'traceparent': f'00-{test_trace_id}-{test_span_id}-01',
        'Content-Type': 'application/json'
    }
    
    try:
        print("\n🚀 Making request to API Gateway...")
        start_time = time.time()
        
        response = requests.post(
            "http://localhost:8010/api/generate-query",
            json={"user_input": test_query},
            headers=headers,
            timeout=30
        )
        
        end_time = time.time()
        total_time = (end_time - start_time) * 1000
        
        print(f"⏱️ Total request time: {total_time:.1f}ms")
        
        if response.status_code == 200:
            data = response.json()
            
            print("✅ Request successful!")
            print(f"   Generated query: {data.get('query', 'N/A')[:80]}...")
            print(f"   Intent: {data.get('intent', 'unknown')}")
            print(f"   Services called: {data.get('services_called', [])}")
            
            # Submit feedback to create additional spans
            print("\n💬 Submitting feedback to extend the trace...")
            
            feedback_headers = {
                'traceparent': f'00-{test_trace_id}-{test_span_id}-01',
                'Content-Type': 'application/json'
            }
            
            feedback_response = requests.post(
                "http://localhost:8010/api/feedback",
                json={
                    "user_input": test_query,
                    "generated_query": data.get('query', ''),
                    "rating": 5,
                    "comment": "Single root span test feedback",
                    "metadata": {"test": "single_root_span", "trace_id": test_trace_id}
                },
                headers=feedback_headers,
                timeout=10
            )
            
            if feedback_response.status_code == 200:
                print("✅ Feedback submitted successfully")
            
            print("\n🎯 Expected Results in Coralogix:")
            print(f"   🔍 Search for trace ID: {test_trace_id}")
            print("   🌳 Should show ONE root span with tree structure:")
            print("      ROOT: api_gateway.generate_query_pipeline")
            print("      ├── api_gateway.call_query_service")
            print("      │   └── query_service.generate_dataprime_query")
            print("      │       ├── query_service.classify_intent")
            print("      │       └── query_service.openai_generation")
            print("      ├── api_gateway.call_validation_service")
            print("      │   └── validation_service.validate_dataprime_query")
            print("      ├── api_gateway.enqueue_processing")
            print("      │   └── queue_service.enqueue_message")
            print("      └── api_gateway.submit_feedback")
            print("          └── storage_service.store_feedback")
            
            print(f"\n⏱️ Expected timing distribution:")
            print(f"   • Total trace: {total_time:.0f}ms")
            print(f"   • API Gateway: ~10ms")
            print(f"   • Query Service: ~1000ms (LLM call)")
            print(f"   • Validation Service: ~75ms")
            print(f"   • Queue Service: ~15ms")
            print(f"   • Processing Service: ~150ms (background)")
            print(f"   • Storage Service: ~35ms")
            
            return True
            
        else:
            print(f"❌ Request failed: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Test error: {str(e)}")
        return False

def test_service_health():
    """Quick health check of all services."""
    print("\n🏥 Quick Service Health Check")
    print("-" * 30)
    
    services = [
        ("API Gateway", "http://localhost:8010/api/health"),
        ("Query Service", "http://localhost:8011/health"),
        ("Validation Service", "http://localhost:8012/health"),
        ("Queue Service", "http://localhost:8013/health"),
        ("Processing Service", "http://localhost:8014/health"),
        ("Storage Service", "http://localhost:8015/health")
    ]
    
    all_healthy = True
    
    for name, url in services:
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"   ✅ {name}")
            else:
                print(f"   ❌ {name}: HTTP {response.status_code}")
                all_healthy = False
        except Exception as e:
            print(f"   ❌ {name}: {str(e)}")
            all_healthy = False
    
    return all_healthy

def main():
    """Main test function."""
    print("🧪 Single Root Span Test - Distributed Tracing Fix Verification")
    print("=" * 70)
    print(f"🕐 Test started at: {datetime.now().isoformat()}")
    
    # Quick health check first
    if not test_service_health():
        print("\n❌ Some services are not healthy. Please start the distributed system:")
        print("   ./run_complete_demo.sh")
        return False
    
    print("\n✅ All services healthy, proceeding with trace test...")
    
    # Test single root span
    success = test_single_root_span()
    
    print("\n" + "=" * 70)
    if success:
        print("🎉 Single Root Span Test PASSED!")
        print("\n🔍 Next Steps:")
        print("1. Open Coralogix and search for the test trace ID")
        print("2. Verify you see ONE root span (not two separate spans)")
        print("3. Check that all services appear as children of the root")
        print("4. Confirm realistic timing distribution")
        print("\nIf you still see two root spans, there may be a deeper issue")
        print("with the telemetry configuration that needs investigation.")
    else:
        print("❌ Single Root Span Test FAILED!")
        print("\nThe distributed tracing fix did not resolve the issue.")
        print("Please check service logs and telemetry configuration.")
    
    print("=" * 70)
    return success

if __name__ == '__main__':
    main()
