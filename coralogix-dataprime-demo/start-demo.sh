#!/bin/bash
# 🚀 Coralogix DataPrime Demo Startup Script

set -e

echo "🚀 Starting Coralogix DataPrime Demo..."
echo "======================================="

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Please create .env from .env.example:"
    echo "   cp .env.example .env"
    echo "   # Then edit .env with your API keys"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "🐳 Please start Docker and try again."
    exit 1
fi

# Check required environment variables
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo "❌ OPENAI_API_KEY not configured!"
    echo "🔑 Please set your OpenAI API key in .env"
    exit 1
fi

if [ -z "$CX_TOKEN" ] || [ "$CX_TOKEN" = "your_coralogix_send_data_key_here" ]; then
    echo "❌ CX_TOKEN not configured!"
    echo "🔑 Please set your Coralogix token in .env"
    exit 1
fi

echo "✅ Configuration validated"
echo ""

# Start services
echo "🐳 Starting Docker services..."
cd docker
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start..."
sleep 15

# Health check
echo "🔍 Checking service health..."
if curl -s http://localhost:8010/api/health > /dev/null; then
    echo "✅ API Gateway is healthy"
else
    echo "⚠️  API Gateway not responding yet (may need more time)"
fi

echo ""
echo "🎉 Demo is starting up!"
echo "======================================="
echo "🌐 Frontend:     http://localhost:8020"
echo "🔌 API Gateway:  http://localhost:8010"
echo "📊 Health Check: http://localhost:8010/api/health"
echo ""
echo "📖 Try these example queries:"
echo "   • Show me errors from the last hour"
echo "   • Find slow database queries"
echo "   • Count logs by service"
echo "   • What are the top error messages?"
echo ""
echo "🔍 Monitor in Coralogix:"
echo "   • APM → Traces (for distributed tracing)"
echo "   • AI Center → Evaluations (for content analysis)"
echo "   • Logs (for structured application logs)"
echo ""
echo "To stop: docker-compose down"
echo "======================================="
