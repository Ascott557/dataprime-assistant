#!/usr/bin/env python3
"""
🔧 Fix Import Issues in Service Files
Remove the problematic shared_telemetry imports and use simple telemetry setup.
"""

import os
import re

def fix_service_imports(filepath):
    """Fix import issues in a service file."""
    if not os.path.exists(filepath):
        return
    
    print(f"🔧 Fixing imports in {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Remove problematic imports
    content = re.sub(r'from services\.shared_telemetry import.*\n', '', content)
    
    # Replace get_service_tracer calls with simple trace.get_tracer
    content = re.sub(r'tracer = get_service_tracer\([^)]+\)', 'tracer = trace.get_tracer(__name__)', content)
    
    # Remove initialize_service_telemetry calls
    content = re.sub(r'initialize_service_telemetry\([^)]+\)\n?', '', content)
    
    # Add basic Flask instrumentation back
    if 'app = Flask(__name__)' in content and 'FlaskInstrumentor' not in content:
        content = content.replace(
            'app = Flask(__name__)',
            '''app = Flask(__name__)

# Initialize Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass'''
        )
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"   ✅ Fixed {filepath}")

def main():
    """Fix all service import issues."""
    print("🔧 Fixing Service Import Issues")
    print("=" * 40)
    
    service_files = [
        "services/api_gateway.py",
        "services/query_service.py",
        "services/validation_service.py", 
        "services/queue_service.py",
        "services/processing_service.py",
        "services/storage_service.py"
    ]
    
    for filepath in service_files:
        fix_service_imports(filepath)
    
    print("\n✅ All import issues fixed!")
    print("🚀 Services should now start without import errors.")

if __name__ == '__main__':
    main()
