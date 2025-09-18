#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


"""
🚀 Distributed DataPrime Assistant - Enterprise Architecture
Main orchestrator for the distributed system with proper OpenTelemetry tracing.
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def validate_environment():
    """Validate required environment variables are set."""
    required_vars = ['OPENAI_API_KEY', 'CX_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   • {var}")
        print("\n🔧 Quick fix:")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your API keys")
        print("   3. Restart the application")
        return False
    
    print("✅ All required environment variables are set")
    return True

def initialize_telemetry():
    """Initialize telemetry using the working shared telemetry approach."""
    try:
        print("🔧 Initializing distributed system telemetry using shared approach...")
        
        # Use the same approach as the working services
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        from shared_telemetry import ensure_telemetry_initialized
        
        result = ensure_telemetry_initialized()
        if result:
            print("✅ Shared telemetry initialized successfully")
            os.environ['DISTRIBUTED_TELEMETRY_INITIALIZED'] = 'true'
            return True
        else:
            print("❌ Shared telemetry initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Telemetry setup failed: {e}")
        import traceback
        print(f"📋 Full error trace: {traceback.format_exc()}")
        print("⚠️  Services will continue without telemetry...")
        return False

class ServiceManager:
    """Manages the lifecycle of all microservices."""
    
    def __init__(self):
        self.services = {}
        self.running = False
        
        # Service definitions: (name, script_path, port, dependencies)
        self.service_definitions = [
            ("storage_service", "services/storage_service.py", 8015, []),
            ("external_api_service", "services/external_api_service.py", 8016, []),
            ("queue_worker_service", "services/queue_worker_service.py", 8017, ["external_api_service", "storage_service"]),
            ("processing_service", "services/processing_service.py", 8014, ["storage_service"]),
            ("queue_service", "services/queue_service.py", 8013, ["processing_service"]),
            ("validation_service", "services/validation_service.py", 8012, []),
            ("query_service", "services/query_service.py", 8011, []),
            ("api_gateway", "services/api_gateway.py", 8010, ["query_service", "validation_service", "queue_worker_service"]),
            ("distributed_frontend", "app/distributed_frontend.py", 8020, ["api_gateway"])
        ]
    
    def start_service(self, name, script_path, port):
        """Start a single service."""
        try:
            print(f"🚀 Starting {name} on port {port}...")
            
            # Start service process
            process = subprocess.Popen([
                sys.executable, script_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            self.services[name] = {
                "process": process,
                "port": port,
                "started_at": datetime.now()
            }
            
            # Give service time to start
            time.sleep(2)
            
            # Check if service is still running
            if process.poll() is None:
                print(f"✅ {name} started successfully")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"❌ {name} failed to start")
                print(f"   stdout: {stdout}")
                print(f"   stderr: {stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start {name}: {e}")
            return False
    
    def stop_service(self, name):
        """Stop a single service."""
        if name in self.services:
            service = self.services[name]
            process = service["process"]
            
            try:
                print(f"🛑 Stopping {name}...")
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=5)
                    print(f"✅ {name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    print(f"⚠️ Force killing {name}...")
                    process.kill()
                    process.wait()
                    print(f"✅ {name} force stopped")
                
                del self.services[name]
                
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")
    
    def start_all_services(self):
        """Start all services in dependency order."""
        print("🚀 Starting distributed DataPrime system...")
        print("=" * 60)
        
        self.running = True
        
        for name, script_path, port, dependencies in self.service_definitions:
            # Wait for dependencies to be ready
            for dep in dependencies:
                if dep not in self.services:
                    print(f"⚠️ Dependency {dep} not running, starting it first...")
                    # Find and start dependency
                    for dep_name, dep_script, dep_port, _ in self.service_definitions:
                        if dep_name == dep:
                            if not self.start_service(dep_name, dep_script, dep_port):
                                print(f"❌ Failed to start dependency {dep}")
                                return False
                            break
            
            # Start the service
            if not self.start_service(name, script_path, port):
                print(f"❌ Failed to start {name}, stopping all services...")
                self.stop_all_services()
                return False
        
        print("=" * 60)
        print("✅ All services started successfully!")
        print(f"🌐 API Gateway available at: http://localhost:8010")
        print(f"📊 Service count: {len(self.services)}")
        print("=" * 60)
        
        return True
    
    def stop_all_services(self):
        """Stop all services."""
        print("🛑 Stopping all services...")
        
        self.running = False
        
        # Stop services in reverse order
        service_names = list(self.services.keys())
        for name in reversed(service_names):
            self.stop_service(name)
        
        print("✅ All services stopped")
    
    def monitor_services(self):
        """Monitor service health and restart if needed."""
        while self.running:
            try:
                time.sleep(10)  # Check every 10 seconds
                
                failed_services = []
                for name, service in self.services.items():
                    process = service["process"]
                    if process.poll() is not None:  # Process has terminated
                        print(f"❌ Service {name} has stopped unexpectedly")
                        failed_services.append(name)
                
                # Restart failed services
                for name in failed_services:
                    print(f"🔄 Restarting {name}...")
                    # Find service definition
                    for sname, script, port, deps in self.service_definitions:
                        if sname == name:
                            self.stop_service(name)  # Clean up
                            self.start_service(name, script, port)
                            break
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Monitor error: {e}")
                time.sleep(5)
    
    def print_status(self):
        """Print current status of all services."""
        print("\n📊 Service Status:")
        print("-" * 50)
        for name, service in self.services.items():
            process = service["process"]
            status = "🟢 RUNNING" if process.poll() is None else "🔴 STOPPED"
            uptime = datetime.now() - service["started_at"]
            print(f"{name:<20} {status} (Port: {service['port']}, Uptime: {uptime})")
        print("-" * 50)

def main():
    """Main entry point for the distributed system."""
    print("🤖 DataPrime Assistant - Distributed Enterprise Architecture")
    print(f"🕐 Started at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Initialize telemetry
    initialize_telemetry()
    
    # Create service manager
    manager = ServiceManager()
    
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        print(f"\n🛑 Received signal {signum}, shutting down...")
        manager.stop_all_services()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start all services
        if not manager.start_all_services():
            print("❌ Failed to start distributed system")
            sys.exit(1)
        
        print("📋 Available endpoints:")
        print("   🌐 Main API: http://localhost:8010/api/generate-query")
        print("   📊 Health: http://localhost:8010/api/health")
        print("   📈 Stats: http://localhost:8010/api/stats")
        print("   💬 Feedback: http://localhost:8010/api/feedback")
        print()
        print("🔍 Individual services:")
        for name, _, port, _ in manager.service_definitions:
            print(f"   {name}: http://localhost:{port}/health")
        print()
        print("Press Ctrl+C to stop all services")
        print("=" * 60)
        
        # Monitor services
        manager.monitor_services()
        
    except KeyboardInterrupt:
        print("\n🛑 Shutdown requested by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        manager.stop_all_services()

if __name__ == '__main__':
    main()
