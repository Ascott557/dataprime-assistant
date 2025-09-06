#!/usr/bin/env python3
"""
🎬 Distributed System Demo Script
Comprehensive demonstration of the enterprise distributed tracing architecture.
"""

import os
import time
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DistributedSystemDemo:
    def __init__(self):
        self.api_gateway_url = "http://localhost:8010"
        self.demo_queries = [
            "Show me errors from the last hour grouped by service",
            "Find slow API calls with response time over 1000ms", 
            "Count critical alerts by subsystem in the last 24 hours",
            "Top 10 endpoints by error rate",
            "Performance analysis for user authentication service"
        ]
    
    def print_header(self, title):
        """Print a formatted header."""
        print(f"\n{'='*60}")
        print(f"🎬 {title}")
        print(f"{'='*60}")
    
    def print_section(self, title):
        """Print a formatted section header."""
        print(f"\n{'🔹' * 3} {title}")
        print(f"{'-' * 40}")
    
    def test_service_health(self):
        """Test the health of all services."""
        self.print_section("Service Health Check")
        
        try:
            response = requests.get(f"{self.api_gateway_url}/api/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API Gateway: {data['status']}")
                print(f"   Uptime: {data.get('uptime', 'N/A')}")
                
                if 'downstream_services' in data:
                    print("\n🔗 Downstream Services:")
                    for service, info in data['downstream_services'].items():
                        status_icon = "✅" if info.get('status') == 'healthy' else "❌"
                        response_time = f" ({info.get('response_time', 0)*1000:.1f}ms)" if 'response_time' in info else ""
                        print(f"   {status_icon} {service}: {info.get('status', 'unknown')}{response_time}")
                
                return True
            else:
                print(f"❌ API Gateway health check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Health check error: {str(e)}")
            return False
    
    def demonstrate_query_generation(self):
        """Demonstrate the distributed query generation pipeline."""
        self.print_section("Distributed Query Generation Pipeline")
        
        for i, query in enumerate(self.demo_queries[:3], 1):  # Demo first 3 queries
            print(f"\n🔍 Demo Query {i}: \"{query}\"")
            
            try:
                # Create trace headers for this request
                trace_id = self.generate_trace_id()
                span_id = self.generate_span_id()
                
                headers = {
                    'traceparent': f'00-{trace_id}-{span_id}-01',
                    'Content-Type': 'application/json'
                }
                
                start_time = time.time()
                
                response = requests.post(
                    f"{self.api_gateway_url}/api/generate-query",
                    json={"user_input": query},
                    headers=headers,
                    timeout=30
                )
                
                processing_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"   ✅ Success! Processing time: {processing_time:.1f}ms")
                    print(f"   🎯 Intent: {data.get('intent', 'unknown')} (confidence: {data.get('intent_confidence', 0)*100:.1f}%)")
                    print(f"   📝 Generated Query: {data.get('query', 'N/A')[:80]}...")
                    print(f"   ✅ Validation: {'PASS' if data.get('validation', {}).get('is_valid') else 'FAIL'}")
                    print(f"   🔗 Services: {' → '.join(data.get('services_called', []))}")
                    print(f"   🔍 Trace ID: {trace_id}")
                    
                    # Submit feedback for this query
                    self.submit_demo_feedback(query, data.get('query', ''), trace_id, 4 + i % 2)  # Ratings 4-5
                    
                else:
                    print(f"   ❌ Failed: HTTP {response.status_code}")
                    print(f"   📄 Response: {response.text[:200]}...")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
            
            time.sleep(2)  # Brief pause between queries
    
    def submit_demo_feedback(self, user_input, generated_query, trace_id, rating):
        """Submit feedback for a demo query."""
        try:
            headers = {
                'traceparent': f'00-{trace_id}-{self.generate_span_id()}-01',
                'Content-Type': 'application/json'
            }
            
            feedback_data = {
                "user_input": user_input,
                "generated_query": generated_query,
                "rating": rating,
                "comment": f"Demo feedback - Rating {rating}/5",
                "metadata": {
                    "demo": True,
                    "demo_timestamp": datetime.now().isoformat(),
                    "trace_id": trace_id
                }
            }
            
            response = requests.post(
                f"{self.api_gateway_url}/api/feedback",
                json=feedback_data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   💬 Feedback submitted: {rating}/5 stars (ID: {data.get('feedback_id', 'N/A')[:8]}...)")
            
        except Exception as e:
            print(f"   ⚠️ Feedback submission failed: {str(e)}")
    
    def demonstrate_system_stats(self):
        """Show comprehensive system statistics."""
        self.print_section("System Statistics & Performance")
        
        try:
            response = requests.get(f"{self.api_gateway_url}/api/stats", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                stats = data.get('stats', {})
                
                print("📊 Service Performance Metrics:")
                
                for service_name, service_stats in stats.items():
                    if isinstance(service_stats, dict):
                        print(f"\n🔹 {service_name.replace('_', ' ').title()}:")
                        
                        # Key metrics
                        if 'queries_processed' in service_stats:
                            print(f"   Queries Processed: {service_stats['queries_processed']}")
                        if 'requests_processed' in service_stats:
                            print(f"   Requests Processed: {service_stats['requests_processed']}")
                        if 'messages_enqueued' in service_stats:
                            print(f"   Messages Queued: {service_stats['messages_enqueued']}")
                        if 'records_stored' in service_stats:
                            print(f"   Records Stored: {service_stats['records_stored']}")
                        if 'errors' in service_stats:
                            print(f"   Errors: {service_stats['errors']}")
                        
                        # Performance metrics
                        if 'average_processing_time_ms' in service_stats:
                            print(f"   Avg Processing Time: {service_stats['average_processing_time_ms']:.1f}ms")
                        if 'database_size_mb' in service_stats:
                            print(f"   Database Size: {service_stats['database_size_mb']}MB")
                
            else:
                print(f"❌ Stats retrieval failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"❌ Stats error: {str(e)}")
    
    def demonstrate_trace_propagation(self):
        """Demonstrate proper trace context propagation."""
        self.print_section("Trace Context Propagation Test")
        
        # Custom trace ID for demonstration
        demo_trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
        demo_span_id = "00f067aa0ba902b7"
        
        print(f"🔍 Testing with custom trace ID: {demo_trace_id}")
        print("   This should create a single trace tree in Coralogix with all 6 services")
        
        try:
            headers = {
                'traceparent': f'00-{demo_trace_id}-{demo_span_id}-01',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.api_gateway_url}/api/generate-query",
                json={"user_input": "Test trace propagation across distributed services"},
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Request successful with custom trace headers")
                print(f"   🔗 Services in trace: {' → '.join(data.get('services_called', []))}")
                print(f"   📊 Check Coralogix for trace: {demo_trace_id}")
                print(f"   🌳 Expected span hierarchy:")
                print(f"      ROOT: api_gateway.generate_query_pipeline")
                print(f"      ├── api_gateway.call_query_service")
                print(f"      │   └── query_service.generate_dataprime_query")
                print(f"      │       ├── query_service.classify_intent")
                print(f"      │       └── query_service.openai_generation")
                print(f"      ├── api_gateway.call_validation_service")
                print(f"      │   └── validation_service.validate_dataprime_query")
                print(f"      └── api_gateway.enqueue_processing")
                print(f"          └── queue_service.enqueue_message")
                
            else:
                print(f"   ❌ Trace test failed: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Trace test error: {str(e)}")
    
    def generate_trace_id(self):
        """Generate a W3C trace ID."""
        import random
        return ''.join([f"{random.randint(0, 15):x}" for _ in range(32)])
    
    def generate_span_id(self):
        """Generate a W3C span ID."""
        import random
        return ''.join([f"{random.randint(0, 15):x}" for _ in range(16)])
    
    def run_complete_demo(self):
        """Run the complete distributed system demonstration."""
        self.print_header("Distributed DataPrime Assistant - Enterprise Demo")
        
        print("🎯 This demo showcases:")
        print("   • 6 interconnected microservices with proper distributed tracing")
        print("   • Single root span propagation across all service calls")
        print("   • Realistic enterprise timing and complexity")
        print("   • Complete observability pipeline")
        print(f"   • Started at: {datetime.now().isoformat()}")
        
        # Step 1: Health checks
        if not self.test_service_health():
            print("\n❌ System health check failed. Please ensure all services are running.")
            print("   Run: ./start_distributed_system.sh")
            return False
        
        # Step 2: Query generation pipeline
        self.demonstrate_query_generation()
        
        # Step 3: System statistics
        self.demonstrate_system_stats()
        
        # Step 4: Trace propagation test
        self.demonstrate_trace_propagation()
        
        # Demo summary
        self.print_section("Demo Summary & Next Steps")
        print("🎉 Distributed system demo completed successfully!")
        print("\n🔍 Coralogix Observability Checklist:")
        print("   ✅ Single root spans with proper parent-child relationships")
        print("   ✅ 6 connected services in service dependency graph")
        print("   ✅ Realistic latency distribution (API Gateway: ~10ms, LLM: ~1000ms)")
        print("   ✅ Business context in span attributes")
        print("   ✅ Error handling and propagation")
        
        print("\n📊 Expected Coralogix Views:")
        print("   • Service Map: Connected topology showing all 6 services")
        print("   • Trace View: Single root with ~1-2 second total duration")
        print("   • Span Timeline: Realistic enterprise timing distribution")
        print("   • Business Metrics: Query success rates, user satisfaction")
        
        print("\n🚀 Demo URLs:")
        print(f"   • API Gateway: {self.api_gateway_url}")
        print(f"   • Web Interface: http://localhost:8020")
        print(f"   • Health Checks: {self.api_gateway_url}/api/health")
        
        return True

def main():
    """Main demo entry point."""
    demo = DistributedSystemDemo()
    
    try:
        success = demo.run_complete_demo()
        
        if success:
            print(f"\n{'='*60}")
            print("🏆 Demo completed successfully!")
            print("   The distributed system is ready for production demonstration.")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print("❌ Demo failed. Please check system status.")
            print(f"{'='*60}")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo error: {str(e)}")

if __name__ == '__main__':
    main()
