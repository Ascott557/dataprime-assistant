# DataPrime Demo - k3s Deployment Guide

This guide walks you through migrating your DataPrime Demo from Docker Compose to k3s with Coralogix Operator integration.

## Overview

This migration will:
- ✅ Stop existing Docker Compose services (data will be backed up)
- ✅ Install k3s (lightweight Kubernetes) on your EC2 instance
- ✅ Build and deploy all services as Kubernetes pods
- ✅ Install Coralogix Operator for enhanced observability
- ✅ Enable Kubernetes host metrics in Coralogix Infrastructure Explorer
- ✅ Enrich traces with pod, namespace, and node metadata

## Prerequisites

Before starting the migration, ensure you have:

1. **Terraform-deployed EC2 instance** (t3.small or larger)
2. **SSH access** to the instance
3. **Coralogix API token** (in `infrastructure/terraform/terraform.tfvars`)
4. **OpenAI API key** (in `infrastructure/terraform/terraform.tfvars`)
5. **Local terminal** with SSH client

## Quick Start

### Option 1: Automated Deployment (Recommended)

Run the deployment script from your local machine:

```bash
cd /Users/andrescott/dataprime-assistant
./scripts/deploy-k3s.sh
```

This script will:
1. Connect to your EC2 instance
2. Stop Docker Compose services
3. Install k3s
4. Build Docker images
5. Deploy all services to Kubernetes
6. Install Coralogix Operator
7. Verify the deployment

**Estimated time:** 15-20 minutes

### Option 2: Manual Deployment

If you prefer to deploy manually or the script fails, follow these steps:

#### Step 1: Connect to EC2 Instance

```bash
# Get your instance IP from Terraform
cd infrastructure/terraform
INSTANCE_IP=$(terraform output -raw instance_public_ip)

# Extract SSH key
terraform output -raw ssh_private_key > ~/.ssh/dataprime-demo-key.pem
chmod 600 ~/.ssh/dataprime-demo-key.pem

# Connect
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$INSTANCE_IP
```

#### Step 2: Stop Docker Compose

```bash
cd /opt/dataprime-assistant/deployment/docker
docker compose --env-file .env.vm -f docker-compose.vm.yml down

# Backup data
sudo cp -r sqlite-data /tmp/sqlite-backup-$(date +%Y%m%d)
```

#### Step 3: Install k3s

```bash
# Install k3s with optimized settings for t3.small
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="server \
  --write-kubeconfig-mode 644 \
  --kubelet-arg=eviction-hard=memory.available<100Mi \
  --kubelet-arg=eviction-soft=memory.available<300Mi \
  --kubelet-arg=eviction-soft-grace-period=memory.available=2m" sh -

# Configure kubectl
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown ubuntu:ubuntu ~/.kube/config
chmod 600 ~/.kube/config

# Verify
kubectl get nodes
```

#### Step 4: Install Helm

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version
```

#### Step 5: Build Docker Images

```bash
cd /opt/dataprime-assistant/coralogix-dataprime-demo

# Build all images
docker build -t dataprime-api-gateway:latest -f services/api-gateway/Dockerfile .
docker build -t dataprime-query-service:latest -f services/query-service/Dockerfile .
docker build -t dataprime-validation-service:latest -f services/validation-service/Dockerfile .
docker build -t dataprime-queue-service:latest -f services/queue-service/Dockerfile .
docker build -t dataprime-processing-service:latest -f services/processing-service/Dockerfile .
docker build -t dataprime-storage-service:latest -f services/storage-service/Dockerfile .
docker build -t dataprime-external-api-service:latest -f services/external-api-service/Dockerfile .
docker build -t dataprime-queue-worker-service:latest -f services/queue-worker-service/Dockerfile .
docker build -t dataprime-frontend:latest -f app/Dockerfile.frontend .

# Import to k3s
for img in dataprime-api-gateway dataprime-query-service dataprime-validation-service \
           dataprime-queue-service dataprime-processing-service dataprime-storage-service \
           dataprime-external-api-service dataprime-queue-worker-service dataprime-frontend; do
  docker save "$img:latest" | sudo k3s ctr images import -
done
```

#### Step 6: Deploy Application

```bash
cd /opt/dataprime-assistant/deployment/kubernetes

# Apply manifests in order
kubectl apply -f namespace.yaml

# Create secret with your credentials
cat > secret.yaml <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: dataprime-secrets
  namespace: dataprime-demo
type: Opaque
stringData:
  CX_TOKEN: "YOUR_CORALOGIX_TOKEN"
  OPENAI_API_KEY: "YOUR_OPENAI_KEY"
EOF

kubectl apply -f secret.yaml
rm -f secret.yaml  # Remove file with secrets

kubectl apply -f configmap.yaml
kubectl apply -f persistent-volumes.yaml
kubectl apply -f redis-statefulset.yaml
kubectl apply -f otel-collector-daemonset.yaml

# Wait for Redis
kubectl wait --for=condition=ready pod -l app=redis -n dataprime-demo --timeout=120s

# Deploy services
kubectl apply -f deployments/
kubectl apply -f services.yaml
kubectl apply -f ingress.yaml

# Check status
kubectl get pods -n dataprime-demo
```

#### Step 7: Install Coralogix Operator

```bash
# Add Coralogix Helm repo
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual
helm repo update

# Install operator
helm install coralogix-operator coralogix/coralogix-operator \
  --create-namespace \
  --namespace coralogix-operator-system \
  --set secret.data.apiKey="YOUR_CORALOGIX_TOKEN" \
  --set coralogixOperator.region="US1" \
  --set coralogixOperator.prometheusRules.enabled=false \
  --set serviceMonitor.create=false \
  --wait

# Verify
kubectl get pods -n coralogix-operator-system
```

## Verification

### 1. Check Pod Status

```bash
kubectl get pods -n dataprime-demo
```

All pods should show `Running` status with `1/1` ready.

### 2. Check Services

```bash
kubectl get svc -n dataprime-demo
```

You should see NodePort services for frontend (30020) and api-gateway (30010).

### 3. Access Application

**Frontend:** `http://YOUR_INSTANCE_IP:30020`
**API Gateway:** `http://YOUR_INSTANCE_IP:30010`

### 4. Run Health Check (From Local Machine)

```bash
./scripts/health-check-k3s.sh
```

### 5. Verify Coralogix Integration

1. **Generate some traffic** by using the application
2. **Check Coralogix Infrastructure Explorer:**
   - Go to [https://coralogix.com/infrastructure](https://coralogix.com/infrastructure)
   - Look for your k3s node
   - Verify host metrics (CPU, memory, disk, network)

3. **Check trace enrichment:**
   - Open a trace in Coralogix
   - Click on a span
   - Look for the **HOST** tab
   - Should show:
     - `k8s.pod.name`
     - `k8s.namespace.name`
     - `k8s.node.name`
     - `k8s.deployment.name`

### 6. Check Resource Usage

```bash
kubectl top nodes
kubectl top pods -n dataprime-demo
```

Expected total memory usage: ~1.5GB (leaving 500MB for k3s + system on t3.small)

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n dataprime-demo

# Describe pod for details
kubectl describe pod <POD_NAME> -n dataprime-demo

# Check logs
kubectl logs <POD_NAME> -n dataprime-demo
```

### Images Not Found

If pods show `ImagePullBackOff` or `ErrImagePull`:

```bash
# Check if images exist
sudo k3s ctr images ls | grep dataprime

# Re-import images
docker save dataprime-api-gateway:latest | sudo k3s ctr images import -
```

### OOM (Out of Memory) Issues

If pods are being killed due to memory:

```bash
# Check memory usage
kubectl top pods -n dataprime-demo
free -h

# Consider:
# 1. Reducing replica counts
# 2. Lowering memory limits in deployments
# 3. Upgrading to t3.medium (4GB RAM)
```

### No Metrics in Coralogix

```bash
# Check OTel Collector logs
kubectl logs -n dataprime-demo -l app=otel-collector --tail=100

# Verify secret
kubectl get secret dataprime-secrets -n dataprime-demo -o jsonpath='{.data.CX_TOKEN}' | base64 -d
echo

# Check Coralogix Operator
kubectl logs -n coralogix-operator-system -l app.kubernetes.io/name=coralogix-operator
```

### Service Not Accessible

```bash
# Test from inside cluster
kubectl exec -n dataprime-demo deployment/api-gateway -- curl http://localhost:8010/api/health

# Check if NodePort is accessible
curl http://YOUR_INSTANCE_IP:30010/api/health

# Check security group allows port 30010 and 30020
```

### Traefik Ingress Not Working

k3s comes with Traefik by default, but we disabled it during installation. To re-enable:

```bash
# Check Traefik status
kubectl get pods -n kube-system | grep traefik

# If not running, enable it
sudo systemctl restart k3s
```

## Rollback to Docker Compose

If you need to rollback to Docker Compose:

```bash
# On EC2 instance

# Uninstall k3s
/usr/local/bin/k3s-uninstall.sh

# Restore Docker Compose
cd /opt/dataprime-assistant/deployment/docker
docker compose --env-file .env.vm -f docker-compose.vm.yml up -d

# Restore database backup if needed
sudo cp -r /tmp/sqlite-backup-YYYYMMDD/* sqlite-data/
```

## Performance Tuning

### For t3.small (2GB RAM)

Current configuration is optimized for t3.small. If experiencing issues:

1. **Reduce replica counts** (already at 1 for all services)
2. **Lower memory limits** in deployment manifests
3. **Disable unused services** temporarily

### For t3.medium (4GB RAM)

If you upgrade to t3.medium, you can:

1. **Increase replica counts** for high-traffic services
2. **Raise memory limits** to improve performance
3. **Add HorizontalPodAutoscaler** for auto-scaling

Example for t3.medium resource allocation:

```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "1000m"
```

## Monitoring and Maintenance

### View Logs

```bash
# All pods in namespace
kubectl logs -n dataprime-demo -l app=api-gateway --tail=100

# Follow logs
kubectl logs -n dataprime-demo -l app=api-gateway -f

# Multiple pods
stern -n dataprime-demo api-gateway  # requires stern tool
```

### Update Application

```bash
# Rebuild image
cd /opt/dataprime-assistant/coralogix-dataprime-demo
docker build -t dataprime-api-gateway:latest -f services/api-gateway/Dockerfile .
docker save dataprime-api-gateway:latest | sudo k3s ctr images import -

# Restart deployment
kubectl rollout restart deployment/api-gateway -n dataprime-demo

# Watch rollout
kubectl rollout status deployment/api-gateway -n dataprime-demo
```

### Scale Services

```bash
# Scale replicas
kubectl scale deployment/api-gateway -n dataprime-demo --replicas=2

# Verify
kubectl get pods -n dataprime-demo -l app=api-gateway
```

### Backup Data

```bash
# Backup persistent volumes
kubectl exec -n dataprime-demo -it deployment/storage-service -- tar czf /tmp/backup.tar.gz /app/data
kubectl cp dataprime-demo/storage-service-xxx:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz
```

## Cost Optimization

### Current Setup (t3.small)

- **EC2**: ~$15/month
- **Storage**: ~$2.40/month (30GB)
- **Data Transfer**: ~$1/month
- **Total**: ~$18.40/month

### Recommendations

1. **Use Reserved Instances** for 40% savings
2. **Enable detailed billing** in Coralogix to track data ingestion
3. **Adjust OTel batch sizes** to reduce API calls
4. **Set up metric sampling** for less critical services

## Security Best Practices

1. **Don't commit secrets** - Use Kubernetes Secrets
2. **Enable network policies** for pod-to-pod communication
3. **Use RBAC** for kubectl access
4. **Regular updates** - Keep k3s and images updated
5. **TLS certificates** - Use cert-manager for production

## Production Recommendations

For production deployments:

1. **Use managed Kubernetes** (EKS, GKE, AKS) instead of k3s
2. **Add HorizontalPodAutoscaler** for auto-scaling
3. **Implement proper monitoring** and alerting
4. **Set up CI/CD** for automated deployments
5. **Use external databases** instead of SQLite
6. **Configure backup strategy** for persistent data
7. **Enable high availability** with multiple replicas

## Additional Resources

- [Coralogix Operator Documentation](https://github.com/coralogix/coralogix-operator)
- [k3s Documentation](https://docs.k3s.io/)
- [Kubernetes Best Practices](https://kubernetes.io/docs/concepts/configuration/overview/)
- [OpenTelemetry Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)

## Support

If you encounter issues:

1. Run the health check script: `./scripts/health-check-k3s.sh`
2. Check pod logs: `kubectl logs -n dataprime-demo <POD_NAME>`
3. Review Coralogix Operator logs
4. Check Coralogix documentation and support

---

**Ready to deploy?** Run `./scripts/deploy-k3s.sh` and follow the prompts!



