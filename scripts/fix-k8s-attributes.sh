#!/bin/bash
set -euo pipefail

echo "=========================================="
echo "Fixing Kubernetes Attributes in Traces"
echo "=========================================="
echo ""

# Get instance IP
cd "$(dirname "$0")/../infrastructure/terraform"
INSTANCE_IP=$(terraform output -raw instance_public_ip 2>/dev/null || echo "")

if [ -z "$INSTANCE_IP" ]; then
    echo "❌ Could not get instance IP from Terraform"
    echo "Please provide the instance IP manually"
    exit 1
fi

echo "✓ Instance IP: $INSTANCE_IP"
echo ""

# Copy updated manifests to instance
echo "Step 1: Copying updated manifests..."
scp -i ~/.ssh/dataprime-demo-key.pem \
    ../deployment/kubernetes/configmap.yaml \
    ubuntu@$INSTANCE_IP:/tmp/

scp -i ~/.ssh/dataprime-demo-key.pem \
    -r ../deployment/kubernetes/deployments/ \
    ubuntu@$INSTANCE_IP:/tmp/

echo ""
echo "Step 2: Applying configuration changes..."
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$INSTANCE_IP bash <<'EOF'
set -euo pipefail

# Apply updated ConfigMap
echo "Applying ConfigMap..."
kubectl apply -f /tmp/configmap.yaml

# Apply updated deployments
echo "Applying deployments..."
kubectl apply -f /tmp/deployments/

echo ""
echo "Step 3: Verifying agent daemonset has hostPort enabled..."
kubectl get daemonset coralogix-opentelemetry-agent -n dataprime-demo -o jsonpath='{.spec.template.spec.containers[0].ports[?(@.name=="otlp")]}' | jq '.'

echo ""
echo "Step 4: Restarting application deployments..."
kubectl rollout restart deployment -n dataprime-demo

echo ""
echo "Step 5: Waiting for rollout..."
sleep 15

echo ""
echo "Step 6: Verifying HOST_IP is set in pods..."
kubectl wait --for=condition=ready pod -l app=api-gateway -n dataprime-demo --timeout=60s
echo "api-gateway HOST_IP:"
kubectl exec -n dataprime-demo deployment/api-gateway -- env | grep HOST_IP || echo "Not set"

echo ""
echo "OTEL_EXPORTER_OTLP_ENDPOINT:"
kubectl exec -n dataprime-demo deployment/api-gateway -- env | grep OTEL_EXPORTER_OTLP_ENDPOINT

echo ""
echo "Step 7: Checking if agent is receiving traces..."
sleep 10
AGENT_POD=$(kubectl get pods -n dataprime-demo -l app.kubernetes.io/component=agent -o jsonpath='{.items[0].metadata.name}')
echo "Agent pod: $AGENT_POD"
echo "Recent agent logs:"
kubectl logs -n dataprime-demo $AGENT_POD --tail=20

echo ""
echo "=========================================="
echo "✅ Configuration applied!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Use the application to generate traces"
echo "2. Wait 2-3 minutes for data to flow"
echo "3. Check Coralogix trace POD tab for k8s metadata"

EOF

echo ""
echo "Complete!"

