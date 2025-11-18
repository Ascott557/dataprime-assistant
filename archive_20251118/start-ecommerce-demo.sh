#!/bin/bash
#
# E-commerce Recommendation System - Quick Start Script
# Starts all services with Docker Compose
#

set -e

echo "=============================================="
echo "E-commerce Recommendation System - Coralogix Demo"
echo "=============================================="
echo ""

# Check if .env file exists
if [ ! -f "coralogix-dataprime-demo/.env.example" ]; then
    echo "❌ Error: .env.example file not found"
    echo "   Please ensure you're running this script from the project root"
    exit 1
fi

# Check for .env file
if [ ! -f "coralogix-dataprime-demo/.env" ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp coralogix-dataprime-demo/.env.example coralogix-dataprime-demo/.env
    echo "✅ Created .env file"
    echo ""
    echo "📝 IMPORTANT: Edit coralogix-dataprime-demo/.env to configure:"
    echo "   - CX_RUM_PUBLIC_KEY (get from Coralogix UI: Data Flow → RUM)"
    echo "   - Verify OPENAI_API_KEY is correct"
    echo "   - Verify CX_TOKEN is correct"
    echo ""
    read -p "Press Enter to continue once you've updated .env..."
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    echo "   Please start Docker Desktop and try again"
    exit 1
fi

# Check if Docker Compose is available
if ! docker-compose --version > /dev/null 2>&1; then
    echo "❌ Error: docker-compose not found"
    echo "   Please install Docker Compose"
    exit 1
fi

echo "🐳 Docker is running"
echo "📦 Starting services..."
echo ""

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
cd coralogix-dataprime-demo
docker-compose -f docker/docker-compose-ecommerce.yml down 2>/dev/null || true

# Build and start services
echo ""
echo "🏗️  Building and starting services (this may take a few minutes)..."
docker-compose -f docker/docker-compose-ecommerce.yml up --build -d

# Wait for services to be healthy
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo ""
echo "🔍 Checking service health..."
echo ""

check_service() {
    local name=$1
    local url=$2
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "✅ $name is healthy"
        return 0
    else
        echo "⚠️  $name is starting..."
        return 1
    fi
}

# Give services time to start
max_retries=30
retry_count=0

while [ $retry_count -lt $max_retries ]; do
    all_healthy=true
    
    check_service "PostgreSQL" "http://localhost:5432" || all_healthy=false
    check_service "Product Service" "http://localhost:8014/health" || all_healthy=false
    check_service "Recommendation AI" "http://localhost:8011/health" || all_healthy=false
    check_service "API Gateway" "http://localhost:8010/api/health" || all_healthy=false
    check_service "Frontend" "http://localhost:8020" || all_healthy=false
    
    if [ "$all_healthy" = true ]; then
        break
    fi
    
    retry_count=$((retry_count + 1))
    if [ $retry_count -lt $max_retries ]; then
        echo ""
        echo "⏳ Waiting for all services... (attempt $retry_count/$max_retries)"
        sleep 2
    fi
done

echo ""
echo "=============================================="
echo "🚀 E-commerce Recommendation System is running!"
echo "=============================================="
echo ""
echo "📍 Access Points:"
echo "   Frontend:        http://localhost:8020"
echo "   API Gateway:     http://localhost:8010"
echo "   Product Service: http://localhost:8014"
echo ""
echo "📊 Coralogix:"
echo "   Dashboard:       https://eu2.coralogix.com"
echo "   Application:     ecommerce-recommendation"
echo ""
echo "🎯 Quick Start:"
echo "   1. Open http://localhost:8020 in your browser"
echo "   2. Enter: 'Looking for wireless headphones, budget \$50-150'"
echo "   3. Click 'Get AI Recommendations'"
echo "   4. Check Coralogix UI for traces and AI Center data"
echo ""
echo "🧪 Demo Scenarios:"
echo "   - Normal flow: Get recommendations (should succeed)"
echo "   - Slow DB: Click 'Simulate Slow Database' button"
echo "   - Pool exhaustion: Click 'Simulate Connection Pool Exhaustion'"
echo ""
echo "📖 Documentation:"
echo "   - Setup: CORALOGIX-SETUP.md"
echo "   - Usage: README-ECOMMERCE.md"
echo "   - Plan: e-commerce-ai-demo.plan.md"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs:    docker-compose -f docker/docker-compose-ecommerce.yml logs -f"
echo "   Stop:         docker-compose -f docker/docker-compose-ecommerce.yml down"
echo "   Restart:      docker-compose -f docker/docker-compose-ecommerce.yml restart"
echo "   Test:         python ../test_demo_scenarios.py"
echo ""
echo "=============================================="
echo ""

# Offer to tail logs
read -p "Would you like to view live logs? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "📜 Showing live logs (Ctrl+C to exit)..."
    echo ""
    docker-compose -f docker/docker-compose-ecommerce.yml logs -f
fi


