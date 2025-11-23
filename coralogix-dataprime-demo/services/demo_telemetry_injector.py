#!/usr/bin/env python3
"""
Demo Telemetry Injector - Scene 9: Database APM

Directly injects realistic database telemetry into Coralogix without needing real queries.
This is more reliable for demos as it doesn't depend on service orchestration.
"""

import os
import time
import random
from datetime import datetime
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

# Configuration
OTEL_ENDPOINT = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'coralogix-opentelemetry-collector.dataprime-demo.svc.cluster.local:4317')
if OTEL_ENDPOINT.startswith('http://'):
    OTEL_ENDPOINT = OTEL_ENDPOINT.replace('http://', '')

def create_tracer_provider(service_name):
    """Create a tracer provider for a specific service."""
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "production",
    })
    
    provider = TracerProvider(resource=resource)
    
    otlp_exporter = OTLPSpanExporter(
        endpoint=OTEL_ENDPOINT,
        insecure=True,
        timeout=10
    )
    
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    return provider

def inject_database_query_span(tracer, service_name, query_type, duration_ms, success=True):
    """
    Create a database query span following OpenTelemetry semantic conventions.
    
    This mimics what a real database query span looks like in Coralogix.
    """
    start_time = time.time_ns()
    
    with tracer.start_as_current_span(
        f"SELECT productcatalog.products",  # OTel convention: OPERATION db.table
        kind=SpanKind.CLIENT,
        start_time=start_time
    ) as span:
        # Required OTel semantic convention attributes
        span.set_attribute("db.system", "postgresql")
        span.set_attribute("db.name", "productcatalog")
        span.set_attribute("db.operation", "SELECT")
        span.set_attribute("db.sql.table", "products")
        span.set_attribute("net.peer.name", "postgres")
        span.set_attribute("net.peer.port", 5432)
        
        # Query details
        if query_type == "product":
            span.set_attribute("db.statement", "SELECT id, name, category, price, description, image_url, stock_quantity FROM products WHERE category = $1")
        elif query_type == "order":
            span.set_attribute("db.statement", "SELECT o.product_id, p.name, COUNT(*) as order_count FROM orders o JOIN products p ON o.product_id = p.id GROUP BY o.product_id, p.name ORDER BY order_count DESC LIMIT 10")
        else:  # inventory
            span.set_attribute("db.statement", "SELECT id, name, stock_quantity FROM products WHERE id = $1")
        
        # Connection pool metrics (showing exhaustion)
        pool_utilization = random.randint(85, 98)
        active_connections = random.randint(40, 95)
        span.set_attribute("db.connection_pool.active", active_connections)
        span.set_attribute("db.connection_pool.utilization_percent", pool_utilization)
        span.set_attribute("db.connection_pool.max", 100)
        
        # Query performance
        span.set_attribute("db.query.duration_ms", duration_ms)
        span.set_attribute("db.rows_returned", random.randint(1, 20))
        
        # Service context
        span.set_attribute("service.name", service_name)
        span.set_attribute("operation.type", "database_read")
        
        # Simulate query duration
        time.sleep(duration_ms / 1000.0)
        
        if not success:
            span.set_status(Status(StatusCode.ERROR, "ConnectionError: Could not acquire connection within 3000ms"))
            span.set_attribute("error", "ConnectionError")
            span.set_attribute("error.type", "pool_exhaustion")
        else:
            span.set_status(Status(StatusCode.OK))
        
        # Set end time to match duration
        end_time = start_time + (int(duration_ms * 1_000_000))

def inject_scene9_telemetry():
    """
    Inject Scene 9: Database APM telemetry.
    
    Creates 43 database query spans across 3 services:
    - 15 from product-service
    - 15 from order-service  
    - 13 from inventory-service
    
    With realistic latencies (P95: 2800ms, P99: 3200ms) and ~8% failure rate.
    """
    print("🔥 Injecting Scene 9: Database APM Telemetry")
    print("=" * 60)
    
    # Create tracer providers for each service
    services = {
        "product-service": create_tracer_provider("product-service"),
        "order-service": create_tracer_provider("order-service"),
        "inventory-service": create_tracer_provider("inventory-service")
    }
    
    # Set trace providers and get tracers
    tracers = {}
    for service_name, provider in services.items():
        trace.set_tracer_provider(provider)
        tracers[service_name] = provider.get_tracer(service_name)
    
    # Define query distribution
    query_plan = []
    
    # Product service: 15 queries
    for i in range(15):
        latency = random.randint(2600, 3200)  # 2600-3200ms
        success = random.random() > 0.08  # 92% success rate
        query_plan.append(("product-service", "product", latency, success))
    
    # Order service: 15 queries
    for i in range(15):
        latency = random.randint(2700, 3100)  # 2700-3100ms
        success = random.random() > 0.08
        query_plan.append(("order-service", "order", latency, success))
    
    # Inventory service: 13 queries
    for i in range(13):
        latency = random.randint(2650, 3000)  # 2650-3000ms
        success = random.random() > 0.08
        query_plan.append(("inventory-service", "inventory", latency, success))
    
    # Shuffle to simulate concurrent execution
    random.shuffle(query_plan)
    
    print(f"📊 Injecting {len(query_plan)} database query spans...")
    print(f"   Services: product-service(15), order-service(15), inventory-service(13)")
    print(f"   Latency: 2600-3200ms (P95: ~2800ms, P99: ~3200ms)")
    print(f"   Failure rate: ~8%")
    print()
    
    # Inject spans
    start_time = time.time()
    success_count = 0
    failure_count = 0
    
    for i, (service_name, query_type, latency, success) in enumerate(query_plan, 1):
        if success:
            success_count += 1
            status = "✓"
        else:
            failure_count += 1
            status = "✗"
        
        print(f"  [{i:2d}/43] {status} {service_name:20s} {query_type:10s} {latency:4d}ms")
        
        # Use the correct tracer for this service
        inject_database_query_span(
            tracers[service_name],
            service_name,
            query_type,
            latency,
            success
        )
    
    # Force flush all providers
    print()
    print("📤 Flushing spans to Coralogix...")
    for service_name, provider in services.items():
        provider.force_flush()
    
    duration = time.time() - start_time
    
    print()
    print("=" * 60)
    print("✅ Scene 9 Telemetry Injection Complete!")
    print("=" * 60)
    print()
    print(f"Summary:")
    print(f"  Total queries: {len(query_plan)}")
    print(f"  Successful: {success_count} ({success_count/len(query_plan)*100:.1f}%)")
    print(f"  Failed: {failure_count} ({failure_count/len(query_plan)*100:.1f}%)")
    print(f"  Execution time: {duration:.1f}s")
    print()
    print("Expected in Coralogix Database APM:")
    print("  • Calling Services: 3 (product, order, inventory)")
    print("  • Query Duration P95: ~2800ms")
    print("  • Query Duration P99: ~3200ms")
    print("  • Active Queries: 43")
    print("  • Failure Rate: ~8%")
    print("  • Pool Utilization: 85-98%")
    print()
    print("Navigate to: APM → Database Monitoring → productcatalog")
    print("Time Range: Last 5 minutes")
    print()

if __name__ == "__main__":
    try:
        inject_scene9_telemetry()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


