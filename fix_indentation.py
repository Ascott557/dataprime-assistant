#!/usr/bin/env python3
"""
🔧 Fix Indentation Issues in Service Files
Fix all indentation problems that prevent services from starting.
"""

import os
import ast

def fix_file_indentation(filepath):
    """Fix indentation issues in a Python file."""
    if not os.path.exists(filepath):
        return False
    
    print(f"🔧 Fixing indentation in {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        # Fix common indentation issues
        if i > 0:
            prev_line = lines[i-1].strip()
            current_line = line.strip()
            
            # If previous line ends with : and current line should be indented
            if (prev_line.endswith(':') and 
                current_line and 
                not line.startswith('    ') and 
                not current_line.startswith('#') and
                not current_line.startswith('"""')):
                
                # Find the indentation level of the previous line
                prev_indent = len(lines[i-1]) - len(lines[i-1].lstrip())
                
                # Add proper indentation (4 spaces more than previous)
                if 'with tracer.start_as_current_span' in prev_line:
                    line = ' ' * (prev_indent + 4) + current_line
                elif 'try:' in prev_line:
                    line = ' ' * (prev_indent + 4) + current_line
                elif 'except' in prev_line or 'finally:' in prev_line:
                    line = ' ' * (prev_indent + 4) + current_line
        
        fixed_lines.append(line)
    
    # Write back the fixed content
    fixed_content = '\n'.join(fixed_lines)
    
    # Test if the fixed content is valid Python
    try:
        ast.parse(fixed_content)
        with open(filepath, 'w') as f:
            f.write(fixed_content)
        print(f"   ✅ Fixed indentation in {filepath}")
        return True
    except SyntaxError as e:
        print(f"   ⚠️ Still has syntax errors in {filepath}: {e}")
        return False

def main():
    """Fix indentation in all service files."""
    print("🔧 Fixing Indentation Issues in Service Files")
    print("=" * 50)
    
    service_files = [
        "services/api_gateway.py",
        "services/query_service.py",
        "services/validation_service.py",
        "services/queue_service.py", 
        "services/processing_service.py",
        "services/storage_service.py"
    ]
    
    for filepath in service_files:
        fix_file_indentation(filepath)
    
    print("\n✅ Indentation fixes applied!")

if __name__ == '__main__':
    main()
