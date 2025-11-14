#!/bin/bash
set -euo pipefail

echo "==========================================="
echo "Coralogix Infrastructure Explorer Setup"
echo "==========================================="
echo ""

# Get EC2 instance IP from Terraform
cd /Users/andrescott/dataprime-assistant/infrastructure/terraform
INSTANCE_IP=$(terraform output -raw instance_public_ip 2>/dev/null)

if [ -z "$INSTANCE_IP" ]; then
    echo "❌ Error: Could not get instance IP from Terraform"
    exit 1
fi

echo "✓ EC2 Instance: $INSTANCE_IP"

# Get Coralogix API key
CX_TOKEN=$(grep '^coralogix_token' terraform.tfvars | cut -d'"' -f2)

if [ -z "$CX_TOKEN" ]; then
    echo "❌ Error: Could not retrieve Coralogix token from terraform.tfvars"
    exit 1
fi

echo "✓ Coralogix API key loaded"
echo ""

# SSH and deploy
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@${INSTANCE_IP} bash <<EOF
set -euo pipefail

echo "Step 1: Removing old OTel Collector..."
kubectl delete daemonset otel-collector -n dataprime-demo --ignore-not-found=true
kubectl delete service otel-collector -n dataprime-demo --ignore-not-found=true
kubectl delete configmap otel-collector-config -n dataprime-demo --ignore-not-found=true
kubectl delete clusterrole otel-collector --ignore-not-found=true
kubectl delete clusterrolebinding otel-collector --ignore-not-found=true
kubectl delete serviceaccount otel-collector -n dataprime-demo --ignore-not-found=true

echo ""
echo "Step 2: Creating/updating Coralogix API key secret..."
kubectl delete secret coralogix-keys -n dataprime-demo --ignore-not-found=true
kubectl create secret generic coralogix-keys \\
  --from-literal=PRIVATE_KEY="${CX_TOKEN}" \\
  -n dataprime-demo

echo ""
echo "Step 3: Adding Coralogix Helm repository..."
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual || true
helm repo update

echo ""
echo "Step 4: Installing Coralogix Complete Observability..."
# Copy values file
cat > /tmp/coralogix-values.yaml <<'YAML'
global:
  domain: "eu2.coralogix.com"
  clusterName: "dataprime-demo"
  defaultApplicationName: "dataprime-demo"
  defaultSubsystemName: "k3s"

resourceCatalog:
  enabled: true

presets:
  hostmetrics:
    enabled: true
  kubeletstats:
    enabled: true
  kubernetesAttributes:
    enabled: true
  kubernetesMetrics:
    enabled: true
  loadBalancing:
    enabled: true

opentelemetry-collector:
  mode: daemonset
  
  presets:
    hostMetrics:
      enabled: true
    kubeletMetrics:
      enabled: true
    kubernetesAttributes:
      enabled: true
  
  resources:
    limits:
      memory: 512Mi
      cpu: 500m
    requests:
      memory: 256Mi
      cpu: 100m
  
  ports:
    otlp:
      enabled: true
      containerPort: 4317
      servicePort: 4317
      protocol: TCP
    otlp-http:
      enabled: true
      containerPort: 4318
      servicePort: 4318
      protocol: TCP

kube-state-metrics:
  enabled: true
YAML

# Install or upgrade
helm upgrade --install coralogix-otel \\
  coralogix/otel-integration \\
  -f /tmp/coralogix-values.yaml \\
  -n dataprime-demo \\
  --wait \\
  --timeout 5m

echo ""
echo "Step 5: Waiting for pods to be ready..."
sleep 30

echo ""
echo "Step 6: Checking deployment status..."
kubectl get pods -n dataprime-demo | grep coralogix || echo "No Coralogix pods found yet"

echo ""
echo "Step 7: Checking OTel Collector service..."
kubectl get svc -n dataprime-demo | grep otel || echo "No OTel service found"

echo ""
echo "✅ Coralogix Infrastructure Explorer deployed!"
echo ""
echo "Next steps:"
echo "1. Wait 5-10 minutes for data to populate"
echo "2. Go to Coralogix > Infrastructure > Infrastructure Explorer"
echo "3. Select your cluster: dataprime-demo"
echo ""
EOF

echo ""
echo "==========================================="
echo "✅ Deployment Complete!"
echo "==========================================="
echo ""
echo "🔗 Access your application at: http://${INSTANCE_IP}:30020"
echo ""
echo "📊 View Infrastructure Explorer:"
echo "   1. Login to Coralogix (eu2.coralogix.com)"
echo "   2. Go to Infrastructure > Infrastructure Explorer"
echo "   3. Select cluster: dataprime-demo"
echo ""
echo "⏱️  Allow 5-10 minutes for data to populate"

