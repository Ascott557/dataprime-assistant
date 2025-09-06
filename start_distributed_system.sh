#!/bin/bash

# 🚀 Start Distributed DataPrime Assistant System
# This script starts all microservices for the enterprise distributed architecture

echo "🤖 Starting Distributed DataPrime Assistant System"
echo "=================================================="

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if required environment variables are set
if [ -z "$OPENAI_API_KEY" ] || [ -z "$CX_TOKEN" ]; then
    echo "❌ Missing required environment variables:"
    echo "   OPENAI_API_KEY and CX_TOKEN must be set"
    echo "   Please check your .env file"
    exit 1
fi

# Install additional dependencies if needed
echo "📦 Installing additional dependencies..."
pip install opentelemetry-instrumentation-requests>=0.48b0 --quiet

# Clean up any existing processes on our ports
echo "🧹 Cleaning up existing processes..."
for port in 8010 8011 8012 8013 8014 8015; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

# Start the distributed system
echo "🚀 Starting distributed system..."
python distributed_app.py

echo "✅ Distributed system startup complete"
