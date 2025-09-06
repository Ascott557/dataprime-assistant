#!/usr/bin/env python3
"""
🔧 Update Services with Shared Telemetry
Updates all services to use the shared telemetry configuration.
"""

import os
import re

def update_service_telemetry(filepath, service_name):
    """Update a service to use shared telemetry."""
    print(f"🔧 Updating {service_name} telemetry...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Remove old telemetry imports and setup
    old_imports = [
        "from opentelemetry.instrumentation.flask import FlaskInstrumentor",
        "from opentelemetry.instrumentation.requests import RequestsInstrumentor", 
        "from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor"
    ]
    
    for old_import in old_imports:
        content = content.replace(old_import, "")
    
    # Remove old instrumentation calls
    old_instrumentations = [
        "FlaskInstrumentor().instrument_app(app)",
        "RequestsInstrumentor().instrument()",
        "SQLite3Instrumentor().instrument()"
    ]
    
    for old_instr in old_instrumentations:
        content = content.replace(old_instr, "")
    
    # Add shared telemetry import
    if "from services.shared_telemetry import" not in content:
        # Find the imports section
        import_pattern = r"(from opentelemetry import trace, context)"
        replacement = r"\1\nfrom services.shared_telemetry import initialize_service_telemetry, get_service_tracer"
        content = re.sub(import_pattern, replacement, content)
    
    # Replace tracer initialization
    old_tracer = "tracer = trace.get_tracer(__name__)"
    service_key = service_name.lower().replace(" ", "_")
    new_tracer = f'tracer = get_service_tracer("{service_key}")'
    content = content.replace(old_tracer, new_tracer)
    
    # Add telemetry initialization after app creation
    app_pattern = r"(app = Flask\(__name__\))"
    if re.search(app_pattern, content):
        replacement = f"""{app_pattern}

# Initialize shared telemetry configuration
initialize_service_telemetry("{service_key}", app)"""
        content = re.sub(app_pattern, replacement, content)
    
    # Remove old __main__ instrumentation
    main_pattern = r"if __name__ == '__main__':\s*# Initialize instrumentation[^#]*FlaskInstrumentor\(\)\.instrument_app\(app\)[^#]*"
    content = re.sub(main_pattern, "if __name__ == '__main__':", content, flags=re.MULTILINE | re.DOTALL)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Updated {service_name}")

def main():
    """Update all services with shared telemetry."""
    print("🔧 Updating Services with Shared Telemetry")
    print("=" * 50)
    
    services = [
        ("services/api_gateway.py", "api_gateway"),
        ("services/query_service.py", "query_service"),
        ("services/validation_service.py", "validation_service"),
        ("services/queue_service.py", "queue_service"),
        ("services/processing_service.py", "processing_service"),
        ("services/storage_service.py", "storage_service")
    ]
    
    for filepath, service_name in services:
        if os.path.exists(filepath):
            try:
                update_service_telemetry(filepath, service_name)
            except Exception as e:
                print(f"❌ Failed to update {service_name}: {e}")
        else:
            print(f"⚠️ File not found: {filepath}")
    
    print("\n🎯 Changes Made:")
    print("✅ Added shared telemetry configuration")
    print("✅ Consistent service naming for traces")
    print("✅ Proper instrumentation initialization order")
    print("✅ Removed duplicate instrumentation calls")
    
    print("\n🚀 This should fix the root span issue!")
    print("   All services now use the same telemetry configuration")

if __name__ == '__main__':
    main()
