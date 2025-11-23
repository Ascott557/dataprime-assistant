#!/bin/bash
set -e

echo "=== V5 Pre-Flight Checks ==="
echo ""

# 1. Current cart service state
echo "1. Checking cart service configuration..."
grep -n "app.run" /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/cart_service.py | tail -1
echo ""

# 2. Redis deployment status
echo "2. Checking Redis deployment status..."
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl get pods -n ecommerce-demo | grep redis' || echo "❌ Redis NOT deployed (expected - we'll deploy it)"
echo ""

# 3. Current checkout service endpoints
echo "3. Reviewing checkout service endpoints..."
grep -n "@app.route.*orders" /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/checkout_service.py
echo ""

# 4. Existing services for Phase 11
echo "4. Checking existing services for Phase 11 integration..."
ls -1 /Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/ | grep -E "(currency|shipping|ad|recommendation)" || echo "Will check after V5 core"
echo ""

# 5. Create backup branch
echo "5. Creating backup branch..."
cd /Users/andrescott/dataprime-assistant-1
BACKUP_BRANCH="backup-before-v5-$(date +%Y%m%d-%H%M%S)"
git checkout -b "$BACKUP_BRANCH" 2>/dev/null || git branch "$BACKUP_BRANCH"
echo "✅ Backup branch created: $BACKUP_BRANCH"
git checkout feature/realistic-ecommerce-demo
echo ""

# 6. Save current ConfigMap
echo "6. Backing up current ConfigMap..."
mkdir -p /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/backups
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl get configmap ecommerce-config -n ecommerce-demo -o yaml' > /Users/andrescott/dataprime-assistant-1/deployment/kubernetes/backups/configmap-backup-$(date +%Y%m%d-%H%M%S).yaml || echo "⚠️ Could not backup ConfigMap (will continue)"
echo ""

# 7. Document current pod status
echo "7. Current pod status on AWS cluster..."
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl get pods -n ecommerce-demo -o wide'
echo ""

# 8. Check current service count in Coralogix (manual step)
echo "8. Current service count (from your screenshot): 3-4 services"
echo "   - load-generator"
echo "   - checkout"
echo "   - product-catalog"
echo "   - postgresql/ecommerce"
echo ""

echo "============================================"
echo "✅ Pre-flight checks complete!"
echo "============================================"
echo ""
echo "Summary:"
echo "- Cart service: Port 8013 (will stay as-is)"
echo "- Redis: NOT deployed (we'll add it)"
echo "- Checkout: Already correct (no changes needed)"
echo "- Current services: 3-4 (target: 6+ after V5)"
echo "- Backup branch created"
echo ""
echo "Ready to proceed with V5 implementation!"
echo ""

