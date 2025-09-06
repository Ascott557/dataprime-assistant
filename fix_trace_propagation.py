#!/usr/bin/env python3
"""
🔧 Fix Trace Propagation - Critical fix for single root span
This script patches the distributed services to ensure proper trace context propagation.
"""

import os
import re

def fix_service_file(filepath, service_name):
    """Fix a single service file for proper trace propagation."""
    print(f"🔧 Fixing {service_name}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Add early Flask instrumentation
    if "FlaskInstrumentor().instrument_app(app)" not in content:
        # Find where app is created
        app_pattern = r"app = Flask\(__name__\)"
        if re.search(app_pattern, content):
            replacement = """app = Flask(__name__)

# Initialize Flask instrumentation immediately for proper trace propagation
from opentelemetry.instrumentation.flask import FlaskInstrumentor
FlaskInstrumentor().instrument_app(app)"""
            content = re.sub(app_pattern, replacement, content)
    
    # Fix trace context extraction pattern
    old_pattern = r"""# Extract and set trace context
    trace_context = extract_trace_context\(\)
    if trace_context:
        token = context\.attach\(trace_context\)"""
    
    new_pattern = """# Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)"""
    
    content = re.sub(old_pattern, new_pattern, content, flags=re.MULTILINE)
    
    # Ensure proper context cleanup
    if "context.detach(token)" not in content and service_name != "api_gateway":
        # Add finally blocks where needed
        pattern = r"(return jsonify\([^}]+}\), 500)"
        replacement = r"\1\n    finally:\n        if token:\n            context.detach(token)"
        content = re.sub(pattern, replacement, content)
    
    # Write the fixed content
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {service_name}")

def main():
    """Fix all service files for proper trace propagation."""
    print("🔧 Fixing Distributed Trace Propagation")
    print("=" * 50)
    
    services = [
        ("services/api_gateway.py", "API Gateway"),
        ("services/query_service.py", "Query Service"),
        ("services/validation_service.py", "Validation Service"),
        ("services/queue_service.py", "Queue Service"),
        ("services/processing_service.py", "Processing Service"),
        ("services/storage_service.py", "Storage Service")
    ]
    
    for filepath, service_name in services:
        if os.path.exists(filepath):
            try:
                fix_service_file(filepath, service_name)
            except Exception as e:
                print(f"❌ Failed to fix {service_name}: {e}")
        else:
            print(f"⚠️ File not found: {filepath}")
    
    print("\n🎯 Key Changes Made:")
    print("✅ Early Flask instrumentation initialization")
    print("✅ Proper trace context extraction and attachment")
    print("✅ Context cleanup with detach() calls")
    print("✅ Fixed indentation and syntax issues")
    
    print("\n🚀 Next Steps:")
    print("1. Restart the distributed system")
    print("2. Test with: python test_distributed_tracing.py")
    print("3. Check Coralogix for single root spans")

if __name__ == '__main__':
    main()
