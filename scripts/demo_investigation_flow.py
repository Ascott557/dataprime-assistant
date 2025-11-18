#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Demo Investigation Flow - Automated Demo Script
Walks through all scenes of the Coralogix observability demo.
"""

import requests
import time
import sys
from datetime import datetime
from typing import Dict, Any

# Configuration
API_GATEWAY_URL = "http://localhost:8010"
PRODUCT_SERVICE_URL = "http://localhost:8014"
FRONTEND_URL = "http://localhost:8020"

class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_scene(number: str, title: str):
    """Print scene header."""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}Scene {number}: {title}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")

def print_action(message: str):
    """Print action message."""
    print(f"{Colors.BLUE}→ {message}{Colors.ENDC}")

def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.ENDC}")

def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")

def print_error(message: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def wait_for_user(message: str = "Press Enter to continue..."):
    """Wait for user input."""
    input(f"\n{Colors.WARNING}{message}{Colors.ENDC}")

def check_service_health(service_url: str, service_name: str) -> bool:
    """Check if a service is healthy."""
    try:
        response = requests.get(f"{service_url}/health", timeout=5)
        if response.status_code == 200:
            print_success(f"{service_name} is healthy")
            return True
        else:
            print_error(f"{service_name} returned status {response.status_code}")
            return False
    except Exception as e:
        print_error(f"{service_name} is unreachable: {e}")
        return False

def scene_0_setup():
    """Scene 0: Setup and Health Checks"""
    print_scene("0", "Setup and Health Checks")
    
    print_action("Checking service health...")
    
    services = [
        (API_GATEWAY_URL, "API Gateway"),
        (PRODUCT_SERVICE_URL, "Product Service"),
    ]
    
    all_healthy = True
    for url, name in services:
        if not check_service_health(url, name):
            all_healthy = False
    
    if not all_healthy:
        print_error("Some services are not healthy. Please check your deployment.")
        return False
    
    print_success("All services are healthy!")
    wait_for_user()
    return True

def scene_1_baseline():
    """Scene 1: Establish Baseline - Normal Operation"""
    print_scene("1", "Establish Baseline - Normal Operation")
    
    print_action("Making a normal recommendation request...")
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/recommendations",
            json={
                "user_id": "demo_user_baseline",
                "user_context": "Looking for wireless headphones, budget $50-150"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Recommendation successful!")
            print(f"  Trace ID: {data.get('trace_id', 'N/A')}")
            print(f"  Tool call success: {data.get('tool_call_success', False)}")
            print(f"  AI fallback used: {data.get('ai_fallback_used', False)}")
        else:
            print_error(f"Request failed with status {response.status_code}")
            
    except Exception as e:
        print_error(f"Request failed: {e}")
    
    wait_for_user()

def scene_9_database_apm():
    """Scene 9: Database APM - Connection Pool Exhaustion"""
    print_scene("9", "Database APM - Connection Pool Exhaustion")
    
    print_action("Triggering database exhaustion scenario...")
    print("  This will generate 43 concurrent queries with 2800ms delays")
    print("  Expected metrics:")
    print("    - Query Duration P95: 2800ms")
    print("    - Query Duration P99: 3200ms")
    print("    - Active Queries: 43")
    print("    - Pool Utilization: 95%")
    print("    - Failure Rate: ~8%")
    
    wait_for_user("Press Enter to trigger the scenario...")
    
    try:
        response = requests.post(
            f"{API_GATEWAY_URL}/api/demo/trigger-database-scenario",
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Database scenario triggered!")
            print(f"  Concurrent queries: {data.get('concurrent_queries', 0)}")
            print(f"  Failures: {data.get('failures', 0)}")
            print(f"  Failure rate: {data.get('failure_rate_percent', 0)}%")
            print(f"  Duration: {data.get('duration_seconds', 0)}s")
            print()
            print_action("Now check Coralogix Database APM:")
            print("  1. Navigate to: APM → Database Monitoring")
            print("  2. Select database: productcatalog")
            print("  3. Observe:")
            print("     - Query Duration P95: ~2800ms")
            print("     - Active Queries: 43 queries spike")
            print("     - Connection Pool: 95% utilized")
            print("     - Multiple services calling database")
        else:
            print_error(f"Failed with status {response.status_code}")
            
    except Exception as e:
        print_error(f"Request failed: {e}")
    
    wait_for_user()

def scene_9_5_continuous_profiling():
    """Scene 9.5: Continuous Profiling - Identify Slow Functions"""
    print_scene("9.5", "Continuous Profiling - Identify Slow Functions")
    
    print_action("Continuous profiling is running in the background")
    print("  The eBPF agent is capturing CPU profiles without code changes")
    print()
    print_action("Check Coralogix Continuous Profiling:")
    print("  1. Navigate to: APM → Continuous Profiling")
    print("  2. Select service: product-service")
    print("  3. Time range: Last 15 minutes")
    print("  4. Look for: search_products_unindexed()")
    print()
    print_action("Expected observations:")
    print("  - Function search_products_unindexed() consumes 99.2% CPU")
    print("  - Stack trace shows PostgreSQL full table scan")
    print("  - Flame graph reveals unindexed LIKE query on description field")
    print()
    print_action("The fix:")
    print("  CREATE INDEX idx_products_description_trgm")
    print("  ON products USING gin(description gin_trgm_ops);")
    
    wait_for_user()

def scene_10_logs_with_cora_ai():
    """Scene 10: Logs with Cora AI - Investigate Errors"""
    print_scene("10", "Logs with Cora AI - Investigate Errors")
    
    print_action("During the database scenario, errors were logged with structured context")
    print("  These logs contain rich metadata for AI analysis")
    print()
    print_action("Check Coralogix Logs:")
    print("  1. Navigate to: Logs → Explore")
    print("  2. Filter: service.name='product-service'")
    print("  3. Look for: 'ConnectionError' or 'Could not acquire connection'")
    print()
    print_action("Use Cora AI to investigate:")
    print("  1. Click on an error log")
    print("  2. Click 'Explain with Cora AI'")
    print("  3. Cora will analyze:")
    print("     - The connection pool exhaustion")
    print("     - Correlation with concurrent queries")
    print("     - Recommendations for mitigation")
    print()
    print_action("Expected Cora AI insights:")
    print("  - 'Connection pool at max capacity (95% utilization)'")
    print("  - '43 concurrent queries detected at 10:47 AM'")
    print("  - 'Recommendation: Increase pool size OR add read replicas'")
    print("  - 'Correlation: Slow queries (2800ms) causing connection buildup'")
    
    wait_for_user()

def scene_11_reset():
    """Scene 11: Reset Demo State"""
    print_scene("11", "Reset Demo State")
    
    print_action("Resetting all demo simulations...")
    
    try:
        response = requests.post(
            f"{PRODUCT_SERVICE_URL}/demo/reset",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Demo reset complete!")
            print(f"  Slow queries disabled: {data.get('slow_queries_disabled', False)}")
            print(f"  Connections released: {data.get('connections_released', 0)}")
        else:
            print_error(f"Reset failed with status {response.status_code}")
            
    except Exception as e:
        print_error(f"Reset failed: {e}")
    
    wait_for_user()

def main():
    """Main demo flow."""
    print(f"\n{Colors.BOLD}{'='*80}")
    print("Coralogix Observability Demo - Investigation Flow")
    print(f"{'='*80}{Colors.ENDC}\n")
    
    print("This script will walk you through the complete demo investigation journey.")
    print("It will:")
    print("  1. Check service health")
    print("  2. Establish baseline operation")
    print("  3. Trigger database exhaustion scenario")
    print("  4. Guide you through Coralogix UI observations")
    print("  5. Reset demo state")
    print()
    
    wait_for_user("Press Enter to start the demo...")
    
    # Scene 0: Setup
    if not scene_0_setup():
        print_error("Setup failed. Exiting.")
        sys.exit(1)
    
    # Scene 1: Baseline
    scene_1_baseline()
    
    # Scene 9: Database APM
    scene_9_database_apm()
    
    # Scene 9.5: Continuous Profiling
    scene_9_5_continuous_profiling()
    
    # Scene 10: Logs with Cora AI
    scene_10_logs_with_cora_ai()
    
    # Scene 11: Reset
    scene_11_reset()
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*80}")
    print("Demo Complete!")
    print(f"{'='*80}{Colors.ENDC}\n")
    
    print("Key Takeaways:")
    print("  1. Database APM revealed query performance degradation (2800ms P95)")
    print("  2. Continuous Profiling pinpointed exact function (search_products_unindexed)")
    print("  3. Structured logs provided context for AI-powered investigation")
    print("  4. Unified observability from infrastructure → application → AI layer")
    print()
    print("Next Steps:")
    print("  - Deploy database index fix")
    print("  - Monitor improvement: 2800ms → 45ms (60x faster)")
    print("  - Add alerting on connection pool utilization > 80%")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Demo interrupted by user{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

