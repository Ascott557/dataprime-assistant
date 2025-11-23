#!/bin/bash
# Test demo endpoints locally before deployment

echo "=== Testing E-commerce Demo Locally ==="
echo ""

# Set up environment
export OTEL_EXPORTER_OTLP_ENDPOINT="otel-collector.dataprime-demo.svc.cluster.local:4317"
export OTEL_SERVICE_NAME="test-service"
export CX_APPLICATION_NAME="ecommerce-recommendation"
export CX_SUBSYSTEM_NAME="test"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="productcatalog"
export DB_USER="dbadmin"
export DB_PASSWORD="postgres_secure_pass_2024"

echo "Starting services locally..."
echo ""

# Check if PostgreSQL is running
echo "1. Checking PostgreSQL..."
if ! command -v psql &> /dev/null; then
    echo "   ⚠️  PostgreSQL not installed locally. Using Docker?"
    echo "   To start PostgreSQL in Docker:"
    echo "   docker run -d --name postgres-test -p 5432:5432 \\"
    echo "     -e POSTGRES_USER=dbadmin \\"
    echo "     -e POSTGRES_PASSWORD=postgres_secure_pass_2024 \\"
    echo "     -e POSTGRES_DB=productcatalog \\"
    echo "     postgres:15"
else
    echo "   ✅ PostgreSQL found"
fi

echo ""
echo "2. Starting Product Service on port 8014..."
cd coralogix-dataprime-demo/services
python3 product_service.py &
PRODUCT_PID=$!
echo "   Product Service PID: $PRODUCT_PID"

sleep 5

echo ""
echo "3. Testing endpoints..."
echo ""

# Test health
echo "   Testing /health:"
curl -s http://localhost:8014/health | jq .

echo ""
echo "   Testing /demo/enable-slow-queries:"
curl -s -X POST http://localhost:8014/demo/enable-slow-queries \
  -H 'Content-Type: application/json' \
  -d '{"delay_ms": 2800}' | jq .

echo ""
echo "   Testing /demo/enable-pool-exhaustion:"
curl -s -X POST http://localhost:8014/demo/enable-pool-exhaustion | jq .

echo ""
echo "   Testing /demo/reset:"
curl -s -X POST http://localhost:8014/demo/reset | jq .

echo ""
echo "=== Local Test Complete ==="
echo "To stop the service: kill $PRODUCT_PID"


