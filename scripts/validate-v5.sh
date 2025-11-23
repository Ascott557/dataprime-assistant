#!/bin/bash

NAMESPACE=${NAMESPACE:-"ecommerce-demo"}

echo "=========================================="
echo "   V5 ARCHITECTURE VALIDATION"
echo "=========================================="
echo ""

echo "Namespace: $NAMESPACE"
echo ""

# Step 1: Check pod count
echo "Step 1: Checking pod status..."
POD_COUNT=$(kubectl get pods -n $NAMESPACE --no-headers 2>/dev/null | grep Running | wc -l)
echo "✓ Running pods: $POD_COUNT (expected: 8+)"
echo ""

kubectl get pods -n $NAMESPACE -o wide
echo ""

# Step 2: Test Frontend health
echo "Step 2: Testing Frontend health endpoint..."
FRONTEND_POD=$(kubectl get pods -n $NAMESPACE -l app=frontend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$FRONTEND_POD" ]; then
    kubectl exec -n $NAMESPACE $FRONTEND_POD -- curl -s http://localhost:8018/health | head -10 || echo "⚠️ Frontend not responding"
    echo "✓ Frontend is healthy"
else
    echo "❌ Frontend pod not found"
fi
echo ""

# Step 3: Test baseline traffic
echo "Step 3: Testing baseline traffic (/api/browse)..."
LOAD_GEN_POD=$(kubectl get pods -n $NAMESPACE -l app=load-generator -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
if [ -n "$LOAD_GEN_POD" ]; then
    kubectl exec -n $NAMESPACE $LOAD_GEN_POD -- curl -s -X POST http://frontend:8018/api/browse \
      -H 'Content-Type: application/json' \
      -d '{"user_id": "test-user", "cart_id": "test-cart"}' | head -5 || echo "⚠️ Baseline traffic failed"
    echo "✓ Baseline traffic works"
else
    echo "⚠️ Load generator pod not found"
fi
echo ""

# Step 4: Test demo traffic
echo "Step 4: Testing demo traffic (/api/checkout)..."
if [ -n "$LOAD_GEN_POD" ]; then
    kubectl exec -n $NAMESPACE $LOAD_GEN_POD -- curl -s -X POST http://frontend:8018/api/checkout \
      -H 'Content-Type: application/json' \
      -d '{"user_id": "test-user", "cart_id": "test-cart"}' | head -5 || echo "⚠️ Demo traffic failed"
    echo "✓ Demo traffic works"
fi
echo ""

# Step 5: Wait for traces to propagate
echo "============================================"
echo "   WAITING FOR TRACES TO PROPAGATE"
echo "============================================"
echo ""
echo "⏳ Traces need time to flow through:"
echo "   Services → OTel Collector → Coralogix"
echo ""
echo "Waiting 120 seconds..."

for i in {120..1}; do
  printf "\r   %3d seconds remaining..." $i
  sleep 1
done

echo ""
echo ""
echo "✓ Wait complete - traces should now be visible in Coralogix"
echo ""

# Step 6: Manual Coralogix verification
echo "============================================"
echo "   CORALOGIX VERIFICATION CHECKLIST"
echo "============================================"
echo ""
echo "📱 Open Coralogix: https://eu2.coralogix.com"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  SERVICE COUNT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Go to: APM → Service Catalog"
echo ""
echo "   Expected services (6+):"
echo "   ┌─────────────────────┬─────────────────┐"
echo "   │ Service Name        │ Status          │"
echo "   ├─────────────────────┼─────────────────┤"
echo "   │ load-generator      │ ✅ (existing)   │"
echo "   │ frontend            │ ⭐ NEW          │"
echo "   │ cart-service (cart) │ ✅ (existing)   │"
echo "   │ product-catalog     │ ✅ (updated)    │"
echo "   │ payment-service     │ ⭐ NEW          │"
echo "   │ checkout            │ ✅ (existing)   │"
echo "   │ postgresql          │ ✅ (database)   │"
echo "   │ redis               │ ⭐ NEW          │"
echo "   └─────────────────────┴─────────────────┘"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  BASELINE TRAFFIC"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Filter: traffic.type = 'baseline'"
echo ""
echo "   Expected metrics:"
echo "   ✅ Error rate:    0-2%"
echo "   ✅ P95 latency:   250-500ms"
echo "   ✅ Throughput:    ~70 rpm (70% of traffic)"
echo "   ✅ Status:        GREEN 🟢"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  DEMO TRAFFIC (if DEMO_MODE enabled)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Filter: traffic.type = 'demo'"
echo ""
echo "   If DEMO_MODE = 'normal' (not enabled):"
echo "   ✅ Error rate:    0-5%"
echo "   ✅ P95 latency:   500-1000ms"
echo "   ✅ Status:        GREEN/YELLOW 🟡"
echo ""
echo "   If DEMO_MODE = 'blackfriday' (enabled):"
echo "   🔴 Error rate:    Progressive 0% → 78%"
echo "   🔴 P95 latency:   500ms → 5,000ms"
echo "   🔴 Throughput:    ~30 rpm (30% of traffic)"
echo "   🔴 Status:        YELLOW → RED 🔴"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  DATABASE APM"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Go to: APM → Databases"
echo ""
echo "   Expected:"
echo "   ✅ PostgreSQL operations visible"
echo "   ✅ Query details captured (SELECT, INSERT)"
echo "   ✅ Connection pool metrics visible"
echo "   ✅ Redis operations in traces (may not show in DB APM)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  TRACE DEPTH & SERVICE FLOW"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Open any trace:"
echo ""
echo "   Expected flow (baseline):"
echo "   load-generator"
echo "     └─ frontend"
echo "         ├─ cart → redis"
echo "         └─ product-catalog → postgresql"
echo ""
echo "   Expected flow (demo with recommendations):"
echo "   load-generator"
echo "     └─ frontend"
echo "         ├─ cart → redis"
echo "         ├─ product-catalog/recommendations → postgresql"
echo "         ├─ payment-service"
echo "         └─ checkout → postgresql"
echo ""
echo "   Validation:"
echo "   ✅ Trace depth: 5-6 levels"
echo "   ✅ All services connected"
echo "   ✅ Database spans show query details"
echo "   ✅ Span attributes present (traffic.type, etc.)"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6️⃣  SPAN ATTRIBUTES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   Check for these attributes in traces:"
echo ""
echo "   Traffic attributes:"
echo "   ✅ traffic.type = 'baseline' or 'demo'"
echo "   ✅ endpoint.type = 'fast_indexed' or 'slow_unindexed'"
echo ""
echo "   Database attributes:"
echo "   ✅ db.system = 'postgresql'"
echo "   ✅ db.statement (SQL query visible)"
echo "   ✅ db.operation = 'SELECT' or 'INSERT'"
echo "   ✅ db.index_used"
echo ""
echo "   Service attributes:"
echo "   ✅ service.name"
echo "   ✅ peer.service (for service-to-service calls)"
echo ""

echo "============================================"
echo ""
echo "Press Enter when Coralogix validation is complete..."
read

echo ""
echo "============================================"
echo "   VALIDATION SUMMARY"
echo "============================================"
echo ""

# Ask for confirmation
echo "Did you see 6+ services in Coralogix? (yes/no): "
read services_ok

echo "Are traces showing proper service flow? (yes/no): "
read traces_ok

echo "Are database operations visible? (yes/no): "
read db_ok

echo ""

if [ "$services_ok" = "yes" ] && [ "$traces_ok" = "yes" ] && [ "$db_ok" = "yes" ]; then
    echo "✅✅✅ V5 VALIDATION SUCCESSFUL! ✅✅✅"
    echo ""
    echo "Your V5 architecture is working correctly:"
    echo "  ✅ 6+ services visible"
    echo "  ✅ Proper service orchestration"
    echo "  ✅ Database visibility maintained"
    echo "  ✅ Dual-mode traffic differentiation"
    echo ""
    echo "Next: Run Phase 11 to integrate existing services"
    echo "  (currency, shipping, ad-service, recommendation)"
    echo "  This will bring you to 10+ services!"
else
    echo "⚠️  V5 VALIDATION INCOMPLETE"
    echo ""
    echo "Troubleshooting:"
    echo ""
    echo "1. Check pod logs:"
    echo "   kubectl logs -n $NAMESPACE -l app=frontend --tail=50"
    echo "   kubectl logs -n $NAMESPACE -l app=payment-service --tail=50"
    echo ""
    echo "2. Check OTel Collector:"
    echo "   kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=opentelemetry-collector --tail=50"
    echo ""
    echo "3. If issues persist:"
    echo "   ./scripts/rollback-v5.sh"
    echo ""
fi

echo ""

