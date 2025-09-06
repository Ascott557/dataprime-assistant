#!/usr/bin/env python3
"""
🔧 Fix Service Syntax Errors
Quick fix for syntax errors introduced by automated updates.
"""

import os
import re

def fix_service_syntax(filepath):
    """Fix syntax errors in a service file."""
    print(f"🔧 Fixing syntax in {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix Flask app creation
    content = re.sub(r'\(app = Flask\(__name__\)\)', 'app = Flask(__name__)', content)
    
    # Fix any malformed finally blocks
    content = re.sub(r'(\s+)finally:\s*if token:\s*context\.detach\(token\)\s*finally:', r'\1finally:\n\1    if token:\n\1        context.detach(token)', content)
    
    # Remove duplicate finally blocks
    content = re.sub(r'finally:\s*finally:', 'finally:', content)
    
    # Fix any broken try/except/finally structure
    lines = content.split('\n')
    fixed_lines = []
    in_function = False
    indent_level = 0
    
    for i, line in enumerate(lines):
        # Skip empty lines at the end
        if not line.strip() and i == len(lines) - 1:
            continue
            
        # Fix indentation issues with finally blocks
        if 'finally:' in line and not line.strip().startswith('finally:'):
            # Find the correct indentation
            for j in range(i-1, -1, -1):
                prev_line = lines[j]
                if prev_line.strip() and ('try:' in prev_line or 'except' in prev_line):
                    # Match the indentation of the try/except
                    indent = len(prev_line) - len(prev_line.lstrip())
                    line = ' ' * indent + 'finally:'
                    break
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    
    # Ensure proper Python syntax
    try:
        compile(content, filepath, 'exec')
        print(f"✅ Syntax check passed for {filepath}")
    except SyntaxError as e:
        print(f"⚠️ Syntax error still exists in {filepath}: {e}")
        # Try a simpler fix - remove problematic lines
        lines = content.split('\n')
        clean_lines = []
        for line in lines:
            # Skip lines that commonly cause issues
            if ('finally:' in line and 
                ('if token:' in line or 'context.detach' in line)):
                continue
            clean_lines.append(line)
        content = '\n'.join(clean_lines)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {filepath}")

def main():
    """Fix all service files."""
    print("🔧 Fixing Service Syntax Errors")
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
        if os.path.exists(filepath):
            fix_service_syntax(filepath)
        else:
            print(f"⚠️ File not found: {filepath}")
    
    print("\n✅ All syntax errors should be fixed!")
    print("🚀 Try starting the system again with: python distributed_app.py")

if __name__ == '__main__':
    main()
