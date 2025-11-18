#!/usr/bin/env python3
"""
Simple Demo Injector - Minimal version for quick testing

Following OpenTelemetry Semantic Conventions v1.38.0 for database spans:
https://opentelemetry.io/docs/specs/semconv/database/database-spans/
"""

import os
import time
import random
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

OTEL_ENDPOINT = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'coralogix-opentelemetry-collector.dataprime-demo.svc.cluster.local:4317')
if OTEL_ENDPOINT.startswith('http://'):
    OTEL_ENDPOINT = OTEL_ENDPOINT.replace('http://', '')

def inject_fast():
    """
    Inject 43 database spans following OTel semantic conventions.
    
    Key changes from previous version:
    - Using server.address/server.port (NOT deprecated net.peer.*)
    - Using db.operation.name (NOT db.operation)
    - Using db.collection.name (NOT db.sql.table)
    - Setting proper Status for failures
    - Adding db.query.text for better visibility
    """
    print("🚀 Quick injection of 43 database spans (OTel v1.38.0 semantic conventions)...")
    
    services = ["product-service", "order-service", "inventory-service"]
    counts = [15, 15, 13]
    
    # Different query patterns for each service
    queries = {
        "product-service": "SELECT id, name, category, price, description FROM products WHERE category = $1",
        "order-service": "SELECT product_id, COUNT(*) as order_count FROM orders GROUP BY product_id ORDER BY order_count DESC LIMIT 10",
        "inventory-service": "SELECT id, name, stock_quantity FROM products WHERE id = $1"
    }
    
    for service_name, count in zip(services, counts):
        # Create provider for this service
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": "production"
        })
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True, timeout=10)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        tracer = provider.get_tracer(service_name)
        
        print(f"  {service_name}: {count} spans")
        
        for i in range(count):
            # OTel convention: span name = "{db.operation.name} {db.collection.name}"
            # Example: "SELECT products"
            
            # Calculate latency (2600-3200ms range for P95: 2800ms, P99: 3200ms)
            latency_ms = random.randint(2600, 3200)
            
            # Set start time (now - latency to make it look like it already happened)
            start_time = time.time_ns() - (int(latency_ms * 1_000_000))
            end_time = time.time_ns()
            
            # Create span manually (not using context manager) to control end time
            span = tracer.start_span(
                "SELECT products",
                kind=SpanKind.CLIENT,  # REQUIRED for database operations
                start_time=start_time
            )
            # REQUIRED: Database system identifier
            span.set_attribute("db.system", "postgresql")
            
            # REQUIRED: Database name
            span.set_attribute("db.name", "productcatalog")
            
            # REQUIRED: Operation name (v1.38.0 - NOT db.operation!)
            span.set_attribute("db.operation.name", "SELECT")
            
            # REQUIRED: Collection/table name (v1.38.0 - NOT db.sql.table!)
            span.set_attribute("db.collection.name", "products")
            
            # REQUIRED: Server address (v1.38.0 - REPLACES net.peer.name)
            span.set_attribute("server.address", "postgres.dataprime-demo.svc.cluster.local")
            
            # REQUIRED: Server port (v1.38.0 - REPLACES net.peer.port)
            span.set_attribute("server.port", 5432)
            
            # RECOMMENDED: Query text (sanitized)
            span.set_attribute("db.query.text", queries[service_name])
            
            # RECOMMENDED: Number of rows returned
            span.set_attribute("db.response.returned_rows", random.randint(1, 50))
            
            # Custom performance attributes (for demo purposes)
            span.set_attribute("db.query.duration_ms", latency_ms)
            span.set_attribute("db.connection_pool.active", random.randint(40, 95))
            span.set_attribute("db.connection_pool.max", 100)
            span.set_attribute("db.connection_pool.utilization_percent", random.randint(85, 98))
            
            # Simulate some failures (10% failure rate for ~8% overall after rounding)
            if random.random() < 0.10:
                # REQUIRED: Set span status to ERROR
                span.set_status(Status(StatusCode.ERROR, "connection pool exhausted: timeout acquiring connection"))
                span.set_attribute("error.type", "ConnectionPoolTimeoutError")
                span.set_attribute("db.operation.success", False)
            else:
                # SUCCESS: Set span status to OK
                span.set_status(Status(StatusCode.OK))
                span.set_attribute("db.operation.success", True)
            
            # CRITICAL: Set span end time to match the calculated latency
            span.end(end_time=end_time)
        
        provider.force_flush()
        time.sleep(0.5)  # Small delay between services
    
    print("✅ Done! Check Coralogix in 10-15 seconds")
    print("   APM → Database Monitoring → productcatalog")
    print("")
    print("Expected:")
    print("  • Calling Services: 3 (product-service, order-service, inventory-service)")
    print("  • Query Duration P95: ~2800ms")
    print("  • Query Duration P99: ~3200ms")
    print("  • Total Queries: 43")
    print("  • Failure Rate: ~8%")

if __name__ == "__main__":
    inject_fast()

