#!/bin/bash

# 🎬 Complete Distributed System Demo
# This script starts the entire distributed system and runs a comprehensive demo

echo "🎬 Complete Distributed DataPrime Assistant Demo"
echo "=================================================="

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Cleaning up processes..."
    
    # Kill all Python processes we started
    pkill -f "distributed_app.py" 2>/dev/null || true
    pkill -f "distributed_frontend.py" 2>/dev/null || true
    
    # Kill processes on our ports
    for port in 8010 8011 8012 8013 8014 8015 8000; do
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
    done
    
    echo "✅ Cleanup completed"
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup EXIT INT TERM

# Check prerequisites
echo "🔧 Checking prerequisites..."

if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Check environment variables
if [ -z "$OPENAI_API_KEY" ] || [ -z "$CX_TOKEN" ]; then
    echo "❌ Missing required environment variables:"
    echo "   OPENAI_API_KEY and CX_TOKEN must be set"
    echo "   Please check your .env file"
    exit 1
fi

echo "✅ Prerequisites checked"

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install additional dependencies
echo "📦 Installing additional dependencies..."
pip install opentelemetry-instrumentation-requests>=0.48b0 --quiet

# Clean up existing processes
echo "🧹 Cleaning up existing processes..."
for port in 8010 8011 8012 8013 8014 8015 8000; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

# Start the distributed system in background
echo "🚀 Starting distributed system..."
python distributed_app.py &
DISTRIBUTED_PID=$!

# Wait for services to start
echo "⏳ Waiting for services to initialize..."
sleep 8

# Check if distributed system started successfully
if ! kill -0 $DISTRIBUTED_PID 2>/dev/null; then
    echo "❌ Distributed system failed to start"
    exit 1
fi

# Start the frontend in background
echo "🌐 Starting web frontend..."
python distributed_frontend.py &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "❌ Frontend failed to start"
    exit 1
fi

echo "✅ All services started successfully!"
echo ""
echo "🌐 Access Points:"
echo "   • Web Interface: http://localhost:8020"
echo "   • API Gateway: http://localhost:8010/api/health"
echo "   • Individual services: localhost:5001-5005"
echo ""

# Run the comprehensive demo
echo "🎬 Running comprehensive demo..."
echo "=================================================="
python demo_distributed_system.py

echo ""
echo "🎯 Demo completed! Services are still running for manual testing."
echo ""
echo "📝 Manual Testing Commands:"
echo "   # Test query generation"
echo "   curl -X POST http://localhost:8010/api/generate-query \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"user_input\": \"Show me errors from last hour\"}'"
echo ""
echo "   # Test system health"
echo "   curl http://localhost:8010/api/health"
echo ""
echo "   # Test system stats"
echo "   curl http://localhost:8010/api/stats"
echo ""
echo "🔍 Check Coralogix for distributed traces!"
echo "   Look for single root spans with 6 connected services"
echo ""
echo "Press Ctrl+C to stop all services and exit"

# Keep script running until user interrupts
while true; do
    sleep 1
    
    # Check if processes are still running
    if ! kill -0 $DISTRIBUTED_PID 2>/dev/null; then
        echo "❌ Distributed system stopped unexpectedly"
        break
    fi
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo "❌ Frontend stopped unexpectedly"
        break
    fi
done
