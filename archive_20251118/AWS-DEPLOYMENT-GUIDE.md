# AWS K3s Deployment Guide
## E-commerce Recommendation System with Full Coralogix Observability

This guide walks you through deploying the E-commerce Recommendation System to AWS EC2 with K3s Kubernetes and complete Coralogix observability.

## 🎯 What's Been Implemented

All Kubernetes manifests and deployment scripts have been updated for the e-commerce architecture:

### ✅ Completed Infrastructure Updates

1. **Kubernetes Manifests**
   - PostgreSQL StatefulSet with 100 products across 5 categories
   - Product Service deployment (with DB connection pooling)
   - Recommendation AI Service deployment (with OpenAI GPT-4)
   - API Gateway deployment (with e-commerce endpoints)
   - Frontend deployment (with Coralogix RUM)
   - Updated ConfigMap with all service URLs and DB config
   - Updated Secrets template with DB password and RUM key

2. **Docker Images**
   - Unified Dockerfile for all Python services
   - Build script (`build-images-k8s.sh`) for K8s deployment

3. **Telemetry Configuration**
   - Removed duplicate telemetry export from `recommendation_ai_service.py`
   - All services now use `shared_telemetry.py` for OTLP export
   - OpenTelemetry Collector configured to receive from apps and forward to Coralogix

4. **Terraform Updates**
   - Added `cx_rum_public_key` variable
   - Added `db_password` variable
   - Updated `bootstrap.sh.tpl` to use K3s instead of Docker Compose
   - Created `terraform.tfvars` with all credentials

5. **Deployment Scripts**
   - Updated `deploy-k3s.sh` to build unified image and deploy e-commerce services

## 📋 Prerequisites

Before deploying, ensure you have:

- [ ] AWS CLI installed and configured (`aws configure`)
- [ ] Terraform installed (v1.0+)
- [ ] SSH client
- [ ] Your local machine's public IP (for SSH access)
- [ ] Valid credentials:
  - Coralogix API Token: `cxtp_CukMevyNl9E9ukwf7A3PpwHw4cU5E6`
  - OpenAI API Key: `sk-proj-h_xytTBCXjyMYcVCUdQ7r...`
  - Coralogix RUM Public Key: `cxtp_QzPXW7tHbocr85GRJQYeeTR8NaxMGF`

## 🚀 Deployment Steps

### Step 1: Update Terraform Variables

Edit `infrastructure/terraform/terraform.tfvars` and update:

```hcl
# Change this to your IP address for security
allowed_ssh_cidr = "YOUR_IP_ADDRESS/32"  # Get your IP: curl ifconfig.me
```

### Step 2: Initialize Terraform Backend (First Time Only)

```bash
cd infrastructure/terraform/backend-setup
terraform init
terraform apply
```

### Step 3: Deploy Infrastructure

```bash
cd infrastructure/terraform
terraform init
terraform plan   # Review what will be created
terraform apply  # Type 'yes' to confirm
```

This creates:
- VPC with public subnet
- EC2 t3.small instance (2 vCPU, 2GB RAM)
- Security groups (SSH, HTTP, NodePorts)
- IAM roles for Coralogix integration
- SSH key pair (saved to `~/.ssh/dataprime-demo-key.pem`)

**Expected time**: 5-10 minutes

**Output**: You'll see the instance public IP address.

### Step 4: Wait for Bootstrap to Complete

The EC2 instance runs a bootstrap script that:
1. Installs K3s and Helm
2. Clones the repository
3. Creates Kubernetes namespace and secrets
4. Deploys PostgreSQL with 100 products
5. Installs Coralogix OpenTelemetry Collector
6. Deploys all application services

**Monitor bootstrap progress**:

```bash
# Get instance IP from Terraform output
INSTANCE_IP=$(cd infrastructure/terraform && terraform output -raw instance_public_ip)

# SSH into instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$INSTANCE_IP

# Check bootstrap log
tail -f /var/log/ecommerce-bootstrap.log
```

**Expected time**: 8-12 minutes

### Step 5: Verify Deployment

Once bootstrap completes, verify the deployment:

```bash
# Check K3s cluster
kubectl get nodes

# Check all pods are running
kubectl get pods -n dataprime-demo

# Check services
kubectl get svc -n dataprime-demo

# Check OTel Collector
kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=50
```

**Expected output**:
- 1 node in Ready state
- 6+ pods in Running state
- Services with ClusterIP and NodePort
- OTel Collector logs showing successful export to Coralogix

### Step 6: Access the Application

```bash
# Get instance IP
echo "Frontend: http://$INSTANCE_IP:30020"
echo "API Gateway: http://$INSTANCE_IP:30010"
```

Open the frontend URL in your browser.

### Step 7: Test AI Recommendations

1. Open the frontend at `http://<INSTANCE_IP>:30020`
2. Enter a query, e.g., "Looking for wireless headphones under $100"
3. Click "Get AI Recommendations"
4. Observe the AI-powered product recommendations

### Step 8: Verify Telemetry in Coralogix

#### Infrastructure Explorer
1. Go to https://eu2.coralogix.com
2. Navigate to **Infrastructure → Explorer**
3. Look for:
   - K3s cluster node
   - All pods with CPU/Memory metrics
   - Network traffic visualization

#### AI Center
1. Navigate to **AI Center → Applications**
2. Select "ecommerce-recommendation"
3. You should see:
   - LLM calls with prompt and response content
   - Automatic evaluations:
     - Context Adherence
     - Tool Parameter Correctness
     - Issue Rate
   - Tool call success/failure metrics

#### APM (Traces)
1. Navigate to **APM → Services**
2. Select "recommendation-ai"
3. Click on a trace
4. Verify:
   - Complete trace from Frontend → API Gateway → Recommendation AI → Product Service → PostgreSQL
   - W3C trace context propagation
   - Kubernetes metadata (pod name, namespace, etc.)
   - Span attributes for tool calls

#### APM Pod & Host
1. In APM, select "recommendation-ai" service
2. Click **Pod & Host** tab
3. Verify:
   - Pod metrics (CPU, Memory)
   - Host metrics (Node performance)
   - Correlation between application performance and infrastructure

## 🧪 Testing Demo Scenarios

### Scenario 1: Normal Flow
Test successful AI recommendation with product data.

**Steps**:
1. Open frontend
2. Query: "Looking for wireless headphones under $100"
3. Click "Get AI Recommendations"

**Verify in Coralogix**:
- ✅ Trace shows: Frontend → API Gateway → Recommendation AI → Tool Call → Product Service → PostgreSQL
- ✅ AI Center shows LLM call with high Context Adherence score
- ✅ Tool call successful

### Scenario 2: Database Slowdown
Simulate slow database queries to see P95/P99 latency.

**Steps**:
1. In frontend, click "Simulate Slow Queries (2.8s)"
2. Make a recommendation request
3. Observe increased response time

**Verify in Coralogix**:
- ✅ Histogram metrics show increased query duration
- ✅ P95 latency > 2800ms
- ✅ Traces show span duration in Product Service > 2.8s

### Scenario 3: Connection Pool Exhaustion
Simulate database connection issues.

**Steps**:
1. In frontend, click "Simulate Pool Exhaustion"
2. Make multiple requests quickly

**Verify in Coralogix**:
- ✅ Error rate increases
- ✅ Database connection pool metrics show 100% utilization
- ✅ Some requests fail with timeout errors

## 🔧 Troubleshooting

### Issue: Pods not starting

**Debug**:
```bash
kubectl describe pod <pod-name> -n dataprime-demo
kubectl logs <pod-name> -n dataprime-demo --previous
```

**Common causes**:
- Image pull issues: Check if images were built and imported to K3s
- Resource limits: t3.small may be at capacity
- ConfigMap/Secret missing: Verify secrets are created

### Issue: No telemetry in Coralogix

**Debug**:
```bash
# Check OTel Collector logs
kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=100

# Check if services are exporting traces
kubectl logs -n dataprime-demo -l app=recommendation-ai --tail=50 | grep "OTLP"

# Verify endpoint configuration
kubectl exec -n dataprime-demo deployment/recommendation-ai -- env | grep OTEL
```

**Common causes**:
- OTel Collector not running
- Wrong endpoint URL in app config
- Coralogix token invalid
- Network policy blocking egress

### Issue: OpenAI API errors

**Debug**:
```bash
kubectl logs -n dataprime-demo -l app=recommendation-ai --tail=50 | grep "OpenAI"
```

**Common causes**:
- Invalid API key
- Rate limit exceeded
- Network connectivity to OpenAI

### Issue: PostgreSQL not ready

**Debug**:
```bash
kubectl get pods -n dataprime-demo -l app=postgres
kubectl logs -n dataprime-demo postgres-0
kubectl exec -n dataprime-demo postgres-0 -- psql -U dbadmin -d productcatalog -c "SELECT COUNT(*) FROM products;"
```

**Expected**: Should return 100 products

## 📊 Cost Estimate

**Monthly AWS Costs** (us-east-1):
- EC2 t3.small (730 hours): ~$15
- EBS 30GB gp3: ~$2.40
- Data transfer: ~$5
- **Total**: ~$22-25/month

**Stop instance when not demoing**:
```bash
cd infrastructure/terraform
terraform destroy  # or just stop the EC2 instance
```

## 🎓 Demo Flow for Coralogix Four-Stage Maturity Model

This application demonstrates Coralogix's observability maturity progression:

### Stage 1: Traditional Observability
- Infrastructure metrics (CPU, memory, disk)
- Application logs
- Basic APM traces

**Show**: Infrastructure Explorer, Log view

### Stage 2: Unified Observability
- Correlated metrics, logs, and traces
- Service dependency mapping
- Kubernetes metadata enrichment

**Show**: APM Service Map, Pod & Host correlation

### Stage 3: AI-Powered Workflows
- Natural language querying with DataPrime
- Cora AI for log analysis
- Automated root cause analysis

**Show**: DataPrime queries, Cora AI insights

### Stage 4: Agentic Observability (Olly)
- AI agent that autonomously investigates issues
- Accelerated troubleshooting
- Intelligent alert correlation

**Show**: Olly investigation flow from Flow Alert to resolution

## 📚 Key Files Reference

### Application Code
- `coralogix-dataprime-demo/services/recommendation_ai_service.py` - AI service with OpenAI integration
- `coralogix-dataprime-demo/services/product_service.py` - Product catalog with PostgreSQL
- `coralogix-dataprime-demo/services/api_gateway.py` - API gateway with trace propagation
- `coralogix-dataprime-demo/app/ecommerce_frontend.py` - Frontend with RUM integration
- `coralogix-dataprime-demo/app/shared_telemetry.py` - Unified OpenTelemetry configuration

### Kubernetes Manifests
- `deployment/kubernetes/postgres-statefulset.yaml` - PostgreSQL database
- `deployment/kubernetes/postgres-init-configmap.yaml` - 100 products seed data
- `deployment/kubernetes/deployments/recommendation-ai-service.yaml` - AI service
- `deployment/kubernetes/deployments/product-service.yaml` - Product catalog
- `deployment/kubernetes/configmap.yaml` - Environment configuration
- `deployment/kubernetes/services.yaml` - Kubernetes services

### Infrastructure
- `infrastructure/terraform/main.tf` - AWS infrastructure definition
- `infrastructure/terraform/variables.tf` - Terraform variables
- `infrastructure/terraform/terraform.tfvars` - Your credentials (git-ignored)
- `infrastructure/terraform/user-data/bootstrap.sh.tpl` - EC2 bootstrap script

### Deployment Scripts
- `scripts/deploy-k3s.sh` - K3s deployment automation
- `scripts/build-images-k8s.sh` - Docker image build script

## 🔐 Security Notes

1. **terraform.tfvars contains secrets** - Never commit to git (already in .gitignore)
2. **Update SSH CIDR** - Change `allowed_ssh_cidr` to your IP for security
3. **RUM Public Key** - Safe to expose in browser, used for client-side tracking
4. **Coralogix Token** - Keep private, used for data ingestion
5. **OpenAI API Key** - Keep private, incurs usage costs

## 🎉 Success Criteria

Your deployment is successful when:

- ✅ All pods running in `dataprime-demo` namespace
- ✅ Frontend accessible at `http://<IP>:30020`
- ✅ AI recommendations working with OpenAI GPT-4
- ✅ PostgreSQL has 100 products
- ✅ Traces flowing to Coralogix with complete propagation
- ✅ AI Center showing LLM calls with evaluations
- ✅ Infrastructure Explorer showing K3s cluster
- ✅ APM Pod & Host tab showing correlation
- ✅ RUM tracking user sessions in browser

## 📞 Support

If you encounter issues:

1. Check the logs: `kubectl logs -n dataprime-demo <pod-name>`
2. Verify secrets: `kubectl get secrets -n dataprime-demo`
3. Check OTel Collector: `kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector`
4. Review this guide's Troubleshooting section

---

**Ready to deploy?** Start with Step 1 above! 🚀


