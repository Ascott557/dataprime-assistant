#!/bin/bash
set -e

echo "=========================================="
echo "   ROLLING BACK V5 TO PREVIOUS STATE"
echo "=========================================="
echo ""

# Configuration
NAMESPACE=${NAMESPACE:-"ecommerce-demo"}
CLUSTER_HOST=${CLUSTER_HOST:-"54.235.171.176"}
SSH_KEY=${SSH_KEY:-"~/.ssh/ecommerce-platform-key.pem"}

echo "Namespace: $NAMESPACE"
echo "Cluster: $CLUSTER_HOST"
echo ""

read -p "Are you sure you want to rollback V5? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled."
    exit 0
fi

echo ""
echo "Step 1: Deleting new V5 services..."
kubectl delete deployment frontend -n $NAMESPACE || echo "  Frontend not found (skipping)"
kubectl delete deployment payment-service -n $NAMESPACE || echo "  Payment service not found (skipping)"
kubectl delete deployment redis -n $NAMESPACE || echo "  Redis not found (skipping)"

kubectl delete service frontend -n $NAMESPACE || echo "  Frontend service not found (skipping)"
kubectl delete service payment-service -n $NAMESPACE || echo "  Payment service not found (skipping)"
kubectl delete service redis -n $NAMESPACE || echo "  Redis service not found (skipping)"

echo "✓ New services removed"
echo ""

echo "Step 2: Rolling back modified services..."
kubectl rollout undo deployment/product-catalog -n $NAMESPACE || echo "  Product-catalog rollback failed (continuing)"
kubectl rollout undo deployment/load-generator -n $NAMESPACE || echo "  Load-generator rollback failed (continuing)"

echo "✓ Rollback initiated"
echo ""

echo "Step 3: Restoring previous ConfigMap..."
BACKUP_CONFIGMAP=$(ls -t /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/backups/configmap-backup-*.yaml 2>/dev/null | head -1)
if [ -n "$BACKUP_CONFIGMAP" ]; then
    kubectl apply -f "$BACKUP_CONFIGMAP"
    echo "✓ ConfigMap restored from: $BACKUP_CONFIGMAP"
else
    echo "⚠️  No ConfigMap backup found - manually restore if needed"
fi

echo ""

echo "Step 4: Waiting for rollback to complete..."
kubectl rollout status deployment/product-catalog -n $NAMESPACE --timeout=120s || echo "  Timeout waiting for product-catalog"
kubectl rollout status deployment/load-generator -n $NAMESPACE --timeout=120s || echo "  Timeout waiting for load-generator"

echo "✓ Rollback complete"
echo ""

echo "Step 5: Restarting remaining deployments..."
kubectl rollout restart deployment/checkout -n $NAMESPACE
kubectl rollout status deployment/checkout -n $NAMESPACE --timeout=120s

echo ""
echo "=========================================="
echo "   ROLLBACK COMPLETE"
echo "=========================================="
echo ""

kubectl get pods -n $NAMESPACE

echo ""
echo "✅ Services restored to previous state (3-4 services)"
echo ""
echo "Next steps:"
echo "1. Verify in Coralogix:"
echo "   - Service count: Should be back to 3-4 services"
echo "   - Traces: load-generator → checkout → product-catalog → postgresql"
echo ""
echo "2. If issues persist, check:"
echo "   kubectl logs -n $NAMESPACE -l app=load-generator --tail=50"
echo "   kubectl logs -n $NAMESPACE -l app=product-catalog --tail=50"
echo ""

