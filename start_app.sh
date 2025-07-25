#!/bin/bash

echo "🚀 DataPrime Assistant - Fresh Startup"
echo "======================================"

# Step 1: Navigate to project directory
cd "$(dirname "$0")"

# Step 2: Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Step 3: Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Step 4: Install/update dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Step 5: Load environment variables
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create a .env file with:"
    echo "OPENAI_API_KEY=your-openai-key-here"
    echo "CX_TOKEN=your-coralogix-token-here" 
    echo "CX_ENDPOINT=https://ingress.eu2.coralogix.com:443"
    exit 1
fi

echo "🔑 Loading environment variables..."
set -a
source .env
set +a

# Step 6: Validate required environment variables
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY not found in .env file"
    exit 1
fi

if [ -z "$CX_TOKEN" ]; then
    echo "❌ CX_TOKEN not found in .env file"
    exit 1
fi

# Step 7: Show environment status
echo ""
echo "🔍 Environment Status:"
echo "- OpenAI Key: ${OPENAI_API_KEY:0:10}...${OPENAI_API_KEY: -4} (length: ${#OPENAI_API_KEY})"
echo "- CX Token: ${CX_TOKEN:0:10}...${CX_TOKEN: -4}"
echo "- CX Endpoint: $CX_ENDPOINT"
echo ""

# Step 8: Clean up any existing processes on port 8000
echo "🧹 Cleaning up any existing processes on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
pkill -f "python.*minimal_dataprime_app" 2>/dev/null || true
sleep 1

# Step 9: Start the application
echo "🌐 Starting DataPrime Assistant..."
echo "App will be available at: http://localhost:8000"
echo "Health check: http://localhost:8000/api/health"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

python3 minimal_dataprime_app.py 