# DataPrime Demo - Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the DataPrime Demo application on k3s.

## Architecture

The deployment consists of:

- **8 Microservices**: API Gateway, Query Service, Validation Service, Queue Service, Processing Service, Storage Service, External API Service, Queue Worker Service
- **Frontend**: Web UI for the demo
- **Redis**: StatefulSet for caching and session management
- **OpenTelemetry Collector**: DaemonSet for collecting host and application metrics
- **Traefik Ingress**: k3s built-in ingress controller for HTTPS access

## Prerequisites

- k3s installed on target host
- Docker images built locally from the `coralogix-dataprime-demo` directory
- Coralogix API token
- OpenAI API key

## Directory Structure

```
deployment/kubernetes/
├── namespace.yaml                    # Namespace definition
├── configmap.yaml                    # Configuration (non-sensitive)
├── secret.yaml.template              # Secret template (fill with actual values)
├── persistent-volumes.yaml           # PVCs for SQLite data
├── redis-statefulset.yaml           # Redis StatefulSet with persistent storage
├── otel-collector-daemonset.yaml    # OpenTelemetry Collector for metrics
├── services.yaml                     # Service definitions for all components
├── ingress.yaml                      # Traefik ingress rules
├── deployments/                      # Deployment manifests for each service
│   ├── api-gateway.yaml
│   ├── query-service.yaml
│   ├── validation-service.yaml
│   ├── queue-service.yaml
│   ├── processing-service.yaml
│   ├── storage-service.yaml
│   ├── external-api-service.yaml
│   ├── queue-worker-service.yaml
│   └── frontend.yaml
└── README.md                         # This file
```

## Resource Requirements

Optimized for **t3.small (2 vCPU, 2GB RAM)**:

- **k3s overhead**: ~500MB
- **System overhead**: ~100MB
- **Available for pods**: ~1.4GB

### Resource Allocation

| Component | Replicas | Memory Request | Memory Limit | CPU Request | CPU Limit |
|-----------|----------|----------------|--------------|-------------|-----------|
| API Gateway | 1 | 64Mi | 128Mi | 50m | 500m |
| Query Service | 1 | 64Mi | 128Mi | 50m | 500m |
| Validation Service | 1 | 64Mi | 128Mi | 50m | 250m |
| Queue Service | 1 | 64Mi | 128Mi | 50m | 250m |
| Processing Service | 1 | 64Mi | 128Mi | 50m | 250m |
| Storage Service | 1 | 64Mi | 128Mi | 50m | 500m |
| External API Service | 1 | 64Mi | 128Mi | 50m | 250m |
| Queue Worker Service | 1 | 64Mi | 128Mi | 50m | 250m |
| Frontend | 1 | 64Mi | 128Mi | 50m | 250m |
| Redis | 1 | 64Mi | 128Mi | 50m | 250m |
| OTel Collector | 1 (DaemonSet) | 128Mi | 256Mi | 100m | 500m |
| **Total** | **11** | **768Mi** | **1536Mi** | **600m** | **4000m** |

## Deployment Order

The `deploy-k3s.sh` script will deploy in this order:

1. **Namespace** - Create the `dataprime-demo` namespace
2. **Secrets** - API keys and tokens
3. **ConfigMap** - Environment configuration
4. **PersistentVolumeClaims** - Storage for SQLite and Redis
5. **Redis StatefulSet** - Start Redis with persistent storage
6. **OpenTelemetry Collector** - Start metrics collection
7. **Microservices Deployments** - Deploy all backend services
8. **Frontend Deployment** - Deploy web UI
9. **Services** - Expose services internally and externally
10. **Ingress** - Configure Traefik for external access

## Manual Deployment

If you prefer to deploy manually:

### 1. Build Docker Images

From the project root:

```bash
cd coralogix-dataprime-demo

# Build all service images
docker build -t dataprime-api-gateway:latest -f services/api-gateway/Dockerfile .
docker build -t dataprime-query-service:latest -f services/query-service/Dockerfile .
docker build -t dataprime-validation-service:latest -f services/validation-service/Dockerfile .
docker build -t dataprime-queue-service:latest -f services/queue-service/Dockerfile .
docker build -t dataprime-processing-service:latest -f services/processing-service/Dockerfile .
docker build -t dataprime-storage-service:latest -f services/storage-service/Dockerfile .
docker build -t dataprime-external-api-service:latest -f services/external-api-service/Dockerfile .
docker build -t dataprime-queue-worker-service:latest -f services/queue-worker-service/Dockerfile .
docker build -t dataprime-frontend:latest -f app/Dockerfile.frontend .
```

### 2. Create Secret

```bash
cd deployment/kubernetes

# Copy template and fill in values
cp secret.yaml.template secret.yaml

# Edit secret.yaml with your actual credentials
# IMPORTANT: Do not commit secret.yaml to git!
nano secret.yaml
```

### 3. Apply Manifests

```bash
# Apply in order
kubectl apply -f namespace.yaml
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f persistent-volumes.yaml
kubectl apply -f redis-statefulset.yaml
kubectl apply -f otel-collector-daemonset.yaml
kubectl apply -f deployments/
kubectl apply -f services.yaml
kubectl apply -f ingress.yaml
```

### 4. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n dataprime-demo

# Check services
kubectl get svc -n dataprime-demo

# Check ingress
kubectl get ingress -n dataprime-demo

# View logs
kubectl logs -n dataprime-demo -l app=api-gateway --tail=50
```

## Accessing the Application

### Via NodePort (Direct Access)

- **Frontend**: `http://<NODE_IP>:30020`
- **API Gateway**: `http://<NODE_IP>:30010`

### Via Ingress (Recommended)

- **Frontend**: `https://<NODE_IP>` or `http://<NODE_IP>`
- **API**: `https://<NODE_IP>/api` or `http://<NODE_IP>/api`

## Coralogix Integration

The deployment includes:

1. **OpenTelemetry Collector DaemonSet**: Collects host metrics (CPU, memory, disk, network) and forwards to Coralogix
2. **Kubernetes Attributes Processor**: Enriches all telemetry with pod, namespace, and node metadata
3. **Service Instrumentation**: Each service sends traces and logs to OTel Collector

### Expected Coralogix Data

After deployment, you should see in Coralogix:

- **Infrastructure Explorer**: Host metrics from the k3s node
- **Traces**: Distributed traces with Kubernetes metadata (pod name, namespace, node)
- **Logs**: Structured logs from all services
- **HOST Tab**: In trace details, you'll see pod and node information

## Coralogix Operator

The Coralogix Operator is installed separately via Helm (see `scripts/deploy-k3s.sh`):

```bash
# Add Coralogix Helm repository
helm repo add coralogix https://cgx.jfrog.io/artifactory/coralogix-charts-virtual
helm repo update

# Install operator
helm install coralogix-operator coralogix/coralogix-operator \
  --create-namespace \
  --namespace coralogix-operator-system \
  --set secret.data.apiKey="YOUR_CORALOGIX_TOKEN" \
  --set coralogixOperator.region="US1" \
  --set coralogixOperator.prometheusRules.enabled=false \
  --set serviceMonitor.create=false
```

## Troubleshooting

### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n dataprime-demo

# Describe pod for events
kubectl describe pod <POD_NAME> -n dataprime-demo

# Check logs
kubectl logs <POD_NAME> -n dataprime-demo
```

### Out of Memory Issues

If pods are being OOMKilled:

```bash
# Check resource usage
kubectl top pods -n dataprime-demo

# Consider scaling down replicas or increasing instance size
```

### Images Not Found

If using `imagePullPolicy: Never`, ensure images are built on the k3s node:

```bash
# SSH to k3s node
ssh ubuntu@<NODE_IP>

# Import images from Docker
sudo k3s ctr images import <image.tar>

# Or build directly on node
cd /opt/dataprime-assistant/coralogix-dataprime-demo
docker build -t dataprime-api-gateway:latest -f services/api-gateway/Dockerfile .
```

### No Metrics in Coralogix

1. Check OTel Collector logs:
   ```bash
   kubectl logs -n dataprime-demo -l app=otel-collector --tail=100
   ```

2. Verify secret is correct:
   ```bash
   kubectl get secret dataprime-secrets -n dataprime-demo -o jsonpath='{.data.CX_TOKEN}' | base64 -d
   ```

3. Check Coralogix Operator:
   ```bash
   kubectl get pods -n coralogix-operator-system
   kubectl logs -n coralogix-operator-system -l app.kubernetes.io/name=coralogix-operator
   ```

## Cleanup

To remove the deployment:

```bash
# Delete all resources in namespace
kubectl delete namespace dataprime-demo

# Delete Coralogix Operator
helm uninstall coralogix-operator -n coralogix-operator-system
kubectl delete namespace coralogix-operator-system
```

## Performance Tuning

For better performance on t3.small:

1. **Reduce replica counts** (already set to 1 for all services)
2. **Increase node size** to t3.medium (4GB RAM)
3. **Disable unused services** temporarily
4. **Adjust OTel Collector batch size** for less frequent exports

## Production Recommendations

For production deployments:

1. **Use a managed Kubernetes service** (EKS, GKE, AKS)
2. **Increase resource limits** based on actual usage
3. **Add HorizontalPodAutoscaler** for auto-scaling
4. **Use real TLS certificates** (Let's Encrypt via cert-manager)
5. **Add NetworkPolicies** for security
6. **Enable persistent storage** with cloud provider storage classes
7. **Set up monitoring and alerting** via Coralogix
8. **Implement proper secret management** (AWS Secrets Manager, Vault)



