#!/usr/bin/env python3
"""
Load Generator for re:Invent 2025 Database Monitoring Demo

Simulates realistic traffic to demonstrate:
- Connection pool exhaustion
- Query queuing
- Database performance under load

Copyright (c) 2024 Coralogix Ltd.
"""

import argparse
import random
import requests
import sys
import time
import threading
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple

# Disable SSL warnings for self-signed certificates
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LoadGenerator:
    """Generate load against multiple database-backed services."""
    
    def __init__(self, host: str, threads: int, rps: int, duration: int, enable_slow_queries: bool = False):
        self.host = host
        self.threads = threads
        self.target_rps = rps
        self.duration = duration
        self.enable_slow_queries = enable_slow_queries
        
        # Statistics
        self.stats_lock = threading.Lock()
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'trace_ids': [],
            'errors': defaultdict(int),
            'requests_by_service': defaultdict(int)
        }
        
        # Control
        self.stop_event = threading.Event()
        self.start_time = None
        
        # Service endpoints
        self.endpoints = [
            ('product-service', f'http://{host}:30010/products?category=Wireless%20Headphones&price_min=0&price_max=100'),
            ('inventory-service', f'http://{host}:30015/inventory/check/1'),
            ('inventory-service', f'http://{host}:30015/inventory/check/2'),
            ('inventory-service', f'http://{host}:30015/inventory/check/3'),
            ('order-service', f'http://{host}:30016/orders/popular-products?limit=5'),
        ]
    
    def enable_slow_query_mode(self):
        """Enable slow query simulation on all services."""
        print("🐌 Enabling slow query mode (2900ms delays)...")
        
        services = [
            (f'http://{self.host}:30010/demo/enable-slow-queries', 'product-service'),
            (f'http://{self.host}:30015/demo/enable-slow-queries', 'inventory-service'),
            (f'http://{self.host}:30016/demo/enable-slow-queries', 'order-service'),
        ]
        
        for url, name in services:
            try:
                response = requests.post(
                    url,
                    json={'delay_ms': 2900},
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"   ✅ {name}: slow queries enabled")
                else:
                    print(f"   ⚠️ {name}: failed ({response.status_code})")
            except Exception as e:
                print(f"   ❌ {name}: {e}")
        
        print("   Waiting 2 seconds for changes to take effect...")
        time.sleep(2)
    
    def reset_demo_mode(self):
        """Reset all demo modes."""
        print("\n♻️ Resetting demo modes...")
        
        services = [
            (f'http://{self.host}:30010/demo/reset', 'product-service'),
            (f'http://{self.host}:30015/demo/reset', 'inventory-service'),
            (f'http://{self.host}:30016/demo/reset', 'order-service'),
        ]
        
        for url, name in services:
            try:
                response = requests.post(url, timeout=5)
                if response.status_code == 200:
                    print(f"   ✅ {name}: reset")
            except:
                pass
    
    def make_request(self, service_name: str, url: str) -> Tuple[bool, float, str, str]:
        """
        Make a single request and return (success, response_time, trace_id, error).
        """
        start = time.time()
        trace_id = None
        error = None
        
        try:
            response = requests.get(url, timeout=10, verify=False)
            duration = time.time() - start
            
            if response.status_code == 200:
                # Try to extract trace_id from response
                try:
                    data = response.json()
                    if 'trace_id' in data:
                        trace_id = data['trace_id']
                except:
                    pass
                
                return True, duration, trace_id, None
            else:
                error = f"HTTP {response.status_code}"
                return False, duration, None, error
                
        except requests.exceptions.Timeout:
            duration = time.time() - start
            return False, duration, None, "Timeout"
        except requests.exceptions.ConnectionError:
            duration = time.time() - start
            return False, duration, None, "ConnectionError"
        except Exception as e:
            duration = time.time() - start
            return False, duration, None, str(e)
    
    def worker_thread(self, thread_id: int):
        """Worker thread that continuously makes requests."""
        print(f"   Thread {thread_id} started")
        
        # Calculate delay between requests for this thread
        delay = len(self.endpoints) * self.threads / self.target_rps
        
        while not self.stop_event.is_set():
            # Pick a random endpoint
            service_name, url = random.choice(self.endpoints)
            
            # Make request
            success, duration, trace_id, error = self.make_request(service_name, url)
            
            # Update stats
            with self.stats_lock:
                self.stats['total_requests'] += 1
                self.stats['requests_by_service'][service_name] += 1
                self.stats['response_times'].append(duration)
                
                if success:
                    self.stats['successful_requests'] += 1
                    if trace_id:
                        self.stats['trace_ids'].append(trace_id)
                else:
                    self.stats['failed_requests'] += 1
                    if error:
                        self.stats['errors'][error] += 1
            
            # Rate limiting
            time.sleep(delay)
    
    def print_stats(self):
        """Print current statistics."""
        with self.stats_lock:
            elapsed = time.time() - self.start_time
            total = self.stats['total_requests']
            successful = self.stats['successful_requests']
            failed = self.stats['failed_requests']
            
            if total == 0:
                return
            
            success_rate = (successful / total * 100) if total > 0 else 0
            actual_rps = total / elapsed if elapsed > 0 else 0
            
            # Calculate average response time
            response_times = self.stats['response_times']
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 20 else avg_response_time
            else:
                avg_response_time = 0
                p95_response_time = 0
            
            print(f"\n📊 Stats (t={int(elapsed)}s):")
            print(f"   Requests: {total} total, {successful} success, {failed} failed")
            print(f"   Success Rate: {success_rate:.1f}%")
            print(f"   Actual RPS: {actual_rps:.1f}")
            print(f"   Response Time: avg={avg_response_time*1000:.0f}ms, p95={p95_response_time*1000:.0f}ms")
            
            # Show requests by service
            print(f"   By Service:")
            for service, count in sorted(self.stats['requests_by_service'].items()):
                print(f"      {service}: {count} requests")
            
            # Show errors if any
            if self.stats['errors']:
                print(f"   Errors:")
                for error, count in sorted(self.stats['errors'].items(), key=lambda x: x[1], reverse=True):
                    print(f"      {error}: {count}")
    
    def monitor_thread(self):
        """Monitor thread that prints stats every 5 seconds."""
        while not self.stop_event.is_set():
            time.sleep(5)
            if not self.stop_event.is_set():
                self.print_stats()
    
    def run(self):
        """Run the load test."""
        print("=" * 70)
        print("🚀 re:Invent 2025 Database Load Generator")
        print("=" * 70)
        print(f"\nConfiguration:")
        print(f"   Target Host: {self.host}")
        print(f"   Threads: {self.threads}")
        print(f"   Target RPS: {self.target_rps}")
        print(f"   Duration: {self.duration}s")
        print(f"   Slow Queries: {'Enabled' if self.enable_slow_queries else 'Disabled'}")
        print()
        
        # Enable slow queries if requested
        if self.enable_slow_queries:
            self.enable_slow_query_mode()
            print()
        
        # Start worker threads
        print(f"🔧 Starting {self.threads} worker threads...")
        self.start_time = time.time()
        
        workers = []
        for i in range(self.threads):
            t = threading.Thread(target=self.worker_thread, args=(i,), daemon=True)
            t.start()
            workers.append(t)
        
        # Start monitor thread
        monitor = threading.Thread(target=self.monitor_thread, daemon=True)
        monitor.start()
        
        print(f"✅ Load test running for {self.duration} seconds...")
        print("   Press Ctrl+C to stop early\n")
        
        try:
            # Wait for duration
            time.sleep(self.duration)
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
        
        # Stop all threads
        print("\n🛑 Stopping load test...")
        self.stop_event.set()
        
        # Wait for workers to finish (max 5 seconds)
        for t in workers:
            t.join(timeout=5)
        
        # Print final stats
        print("\n" + "=" * 70)
        print("📈 FINAL RESULTS")
        print("=" * 70)
        self.print_stats()
        
        # Print trace IDs
        if self.stats['trace_ids']:
            print(f"\n🔍 Generated Trace IDs ({len(self.stats['trace_ids'])} total):")
            # Print first 10 and last 10
            trace_ids = self.stats['trace_ids']
            if len(trace_ids) <= 20:
                for trace_id in trace_ids:
                    print(f"   {trace_id}")
            else:
                print("   First 10:")
                for trace_id in trace_ids[:10]:
                    print(f"   {trace_id}")
                print(f"   ... ({len(trace_ids) - 20} more) ...")
                print("   Last 10:")
                for trace_id in trace_ids[-10:]:
                    print(f"   {trace_id}")
        
        # Reset demo mode if we enabled it
        if self.enable_slow_queries:
            self.reset_demo_mode()
        
        print("\n✅ Load test complete!")
        print("=" * 70)
        print()
        
        # Return exit code based on success rate
        with self.stats_lock:
            if self.stats['total_requests'] == 0:
                return 1
            success_rate = self.stats['successful_requests'] / self.stats['total_requests']
            return 0 if success_rate > 0.8 else 1


def main():
    parser = argparse.ArgumentParser(
        description='Generate load for re:Invent database monitoring demo',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal traffic (10% pool utilization)
  python generate-demo-load.py --host 54.235.171.176 --threads 10 --rps 10 --duration 60
  
  # Heavy load (80-90% pool utilization)
  python generate-demo-load.py --host 54.235.171.176 --threads 50 --rps 30 --duration 120
  
  # Demo scenario with slow queries
  python generate-demo-load.py --host 54.235.171.176 --threads 50 --rps 30 --duration 120 --enable-slow-queries
  
  # Quick test
  python generate-demo-load.py --host 54.235.171.176 --threads 5 --rps 5 --duration 30
        """
    )
    
    parser.add_argument('--host', required=True, help='Target host IP or hostname')
    parser.add_argument('--threads', type=int, default=20, help='Number of concurrent threads (default: 20)')
    parser.add_argument('--rps', type=int, default=20, help='Target requests per second (default: 20)')
    parser.add_argument('--duration', type=int, default=120, help='Duration in seconds (default: 120)')
    parser.add_argument('--enable-slow-queries', action='store_true', help='Enable slow query mode (2900ms delays)')
    
    args = parser.parse_args()
    
    # Validation
    if args.threads < 1 or args.threads > 200:
        print("❌ Error: threads must be between 1 and 200")
        return 1
    
    if args.rps < 1 or args.rps > 1000:
        print("❌ Error: rps must be between 1 and 1000")
        return 1
    
    if args.duration < 10 or args.duration > 3600:
        print("❌ Error: duration must be between 10 and 3600 seconds")
        return 1
    
    # Run load test
    generator = LoadGenerator(
        host=args.host,
        threads=args.threads,
        rps=args.rps,
        duration=args.duration,
        enable_slow_queries=args.enable_slow_queries
    )
    
    return generator.run()


if __name__ == '__main__':
    sys.exit(main())


