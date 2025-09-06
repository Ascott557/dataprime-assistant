#!/usr/bin/env python3
"""
🔧 Update All Service Ports to 8010+ Range
Updates all distributed service ports and fixes syntax issues.
"""

import os
import re
import glob

# Port mapping
PORT_MAPPING = {
    "5000": "8010",  # API Gateway
    "5001": "8011",  # Query Service
    "5002": "8012",  # Validation Service
    "5003": "8013",  # Queue Service
    "5004": "8014",  # Processing Service
    "5005": "8015",  # Storage Service
    "8000": "8020"   # Frontend (if conflicts)
}

def update_ports_in_file(filepath):
    """Update all port references in a file."""
    if not os.path.exists(filepath):
        return False
    
    print(f"🔧 Updating ports in {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Track changes
    changes_made = False
    
    # Update localhost URLs
    for old_port, new_port in PORT_MAPPING.items():
        old_url = f"http://localhost:{old_port}"
        new_url = f"http://localhost:{new_port}"
        if old_url in content:
            content = content.replace(old_url, new_url)
            changes_made = True
            print(f"   ✅ {old_url} → {new_url}")
    
    # Update app.run port assignments
    for old_port, new_port in PORT_MAPPING.items():
        old_run = f"app.run(host='0.0.0.0', port={old_port}"
        new_run = f"app.run(host='0.0.0.0', port={new_port}"
        if old_run in content:
            content = content.replace(old_run, new_run)
            changes_made = True
            print(f"   ✅ app.run port {old_port} → {new_port}")
        
        # Also check other app.run formats
        old_run2 = f"port={old_port}"
        new_run2 = f"port={new_port}"
        if old_run2 in content and f"localhost:{old_port}" not in content:
            content = content.replace(old_run2, new_run2)
            changes_made = True
            print(f"   ✅ port parameter {old_port} → {new_port}")
    
    # Update port ranges in cleanup scripts
    old_range = "5000 5001 5002 5003 5004 5005"
    new_range = "8010 8011 8012 8013 8014 8015"
    if old_range in content:
        content = content.replace(old_range, new_range)
        changes_made = True
        print(f"   ✅ Port range updated")
    
    # Update individual port references in loops
    old_range2 = "for port in 5000 5001 5002 5003 5004 5005"
    new_range2 = "for port in 8010 8011 8012 8013 8014 8015"
    if old_range2 in content:
        content = content.replace(old_range2, new_range2)
        changes_made = True
    
    # Write back if changes were made
    if changes_made:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"   ✅ Updated {filepath}")
        return True
    else:
        print(f"   ℹ️ No changes needed in {filepath}")
        return False

def fix_syntax_errors():
    """Fix syntax errors in service files."""
    print("\n🔧 Fixing syntax errors in service files...")
    
    service_files = glob.glob("services/*.py")
    
    for filepath in service_files:
        print(f"🔧 Fixing syntax in {filepath}...")
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Fix Flask app creation syntax errors
        content = re.sub(r'\(app = Flask\(__name__\)\)', 'app = Flask(__name__)', content)
        
        # Remove broken finally blocks and context management
        lines = content.split('\n')
        clean_lines = []
        skip_next = False
        
        for i, line in enumerate(lines):
            if skip_next:
                skip_next = False
                continue
                
            # Skip problematic finally blocks that cause syntax errors
            if ('finally:' in line and 
                i < len(lines) - 1 and 
                ('if token:' in lines[i+1] or 'context.detach' in lines[i+1])):
                # Skip this and next few lines that cause issues
                j = i + 1
                while j < len(lines) and ('context.detach' in lines[j] or lines[j].strip() == ''):
                    j += 1
                # Skip to after the problematic block
                continue
            
            clean_lines.append(line)
        
        content = '\n'.join(clean_lines)
        
        # Remove any remaining syntax issues
        content = re.sub(r'finally:\s*finally:', 'finally:', content)
        content = re.sub(r'(\s+)finally:\s*if token:\s*context\.detach\(token\)\s*$', '', content, flags=re.MULTILINE)
        
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"   ✅ Fixed {filepath}")

def main():
    """Update all ports across the distributed system."""
    print("🔧 Updating All Service Ports to 8010+ Range")
    print("=" * 50)
    
    # Files to update
    files_to_update = [
        # Service files
        "services/api_gateway.py",
        "services/query_service.py", 
        "services/validation_service.py",
        "services/queue_service.py",
        "services/processing_service.py",
        "services/storage_service.py",
        
        # Main orchestrator
        "distributed_app.py",
        "distributed_frontend.py",
        
        # Scripts
        "start_distributed_system.sh",
        "run_complete_demo.sh",
        "cleanup_port.sh",
        
        # Test files
        "test_distributed_tracing.py",
        "demo_distributed_system.py",
        "test_single_root_span.py",
        
        # Documentation
        "README_DISTRIBUTED.md",
        "TRANSFORMATION_SUMMARY.md"
    ]
    
    # First fix syntax errors
    fix_syntax_errors()
    
    print("\n🔧 Updating port references...")
    
    # Update ports in each file
    total_updated = 0
    for filepath in files_to_update:
        if update_ports_in_file(filepath):
            total_updated += 1
    
    print(f"\n✅ Updated ports in {total_updated} files")
    
    print("\n🎯 Port Mapping Applied:")
    for old_port, new_port in PORT_MAPPING.items():
        print(f"   {old_port} → {new_port}")
    
    print("\n🚀 New Service URLs:")
    print("   🌐 API Gateway: http://localhost:8010")
    print("   🧠 Query Service: http://localhost:8011")
    print("   ✅ Validation Service: http://localhost:8012")
    print("   📬 Queue Service: http://localhost:8013")
    print("   ⚙️ Processing Service: http://localhost:8014")
    print("   💾 Storage Service: http://localhost:8015")
    print("   🌐 Frontend: http://localhost:8020")
    
    print("\n✅ All ports updated! Ready to test distributed system.")

if __name__ == '__main__':
    main()
