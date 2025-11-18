#!/bin/bash
#
# Test Scene 9: Database APM Demo
#

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🧪 Testing Scene 9: Database APM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📍 Endpoint: http://$EC2_HOST:30010/api/demo/inject-telemetry"
echo ""

# Test locally
echo "Running telemetry injection..."
curl -X POST \
  -H "Content-Type: application/json" \
  -m 30 \
  "http://$EC2_HOST:30010/api/demo/inject-telemetry" \
  2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Request sent (check response above)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 Next: Check Coralogix"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. Wait 10-15 seconds for telemetry to propagate"
echo ""
echo "2. Navigate to: APM → Database Monitoring → productcatalog"
echo ""
echo "3. Set time range: Last 15 minutes"
echo ""
echo "4. Expected to see:"
echo "   ✓ 3 calling services (product-service, order-service, inventory-service)"
echo "   ✓ Query Duration P95: ~2800ms"
echo "   ✓ Query Duration P99: ~3200ms"
echo "   ✓ 43 total spans"
echo "   ✓ ~8% failure rate"
echo ""

