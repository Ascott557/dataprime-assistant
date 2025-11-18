# AWS Deployment Checklist
## E-commerce Recommendation System with Coralogix Observability

This checklist guides you through deploying the e-commerce recommendation system to AWS with full Coralogix observability.

---

## Prerequisites

Before starting, ensure you have:

- [ ] AWS account with administrator access
- [ ] AWS CLI configured (`aws configure`)
- [ ] Terraform >= 1.5 installed (`terraform version`)
- [ ] kubectl installed (`kubectl version --client`)
- [ ] jq installed (`jq --version`)
- [ ] Coralogix account (https://eu2.coralogix.com)
- [ ] OpenAI API key (https://platform.openai.com/api-keys)
- [ ] Your public IP address (`curl ifconfig.me`)

**Get your credentials ready**:
- Coralogix Token: `cxtp_CukMevyNl9E9ukwf7A3PpwHw4cU5E6`
- Coralogix RUM Public Key: `cxtp_QzPXW7tHbocr85GRJQYeeTR8NaxMGF`
- OpenAI API Key: `sk-proj-h_xytTBCXjyMYcVCUdQ7r...`

---

## Step 1: Terraform Backend Setup (One-time)

This creates the S3 bucket and DynamoDB table for Terraform state management.

```bash
cd /Users/andrescott/dataprime-assistant-1
./scripts/setup-terraform-backend.sh
```

**What it does**:
- Creates S3 bucket: `ecommerce-demo-terraform-state-XXXXXXXX`
- Creates DynamoDB table: `ecommerce-demo-terraform-locks`
- Enables versioning and encryption
- Outputs bucket name for next step

**Expected time**: 2-3 minutes

**Action required**: Note the S3 bucket name from the output!

---

## Step 2: Update Terraform Backend Configuration

Edit `infrastructure/terraform/main.tf` and update lines 36-42:

```hcl
backend "s3" {
  bucket         = "ecommerce-demo-terraform-state-XXXXXXXX"  # Use bucket name from Step 1
  key            = "ecommerce-demo/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "ecommerce-demo-terraform-locks"
  encrypt        = true
}
```

**Important**: Replace `XXXXXXXX` with the actual bucket name from Step 1 output.

---

## Step 3: Deploy Infrastructure

Deploy EC2, VPC, security groups, and bootstrap K3s:

```bash
./scripts/deploy-aws.sh
```

**What it does**:
1. Checks prerequisites (Terraform, AWS CLI, jq)
2. Prompts for secrets if `terraform.tfvars` doesn't exist:
   - Coralogix Token (`CX_TOKEN`)
   - OpenAI API Key
   - Your IP address for SSH (format: `x.x.x.x/32`)
3. Runs `terraform init`, `plan`, `apply`
4. Saves SSH key to `~/.ssh/dataprime-demo-key.pem`
5. Displays instance IP and access information

**Expected time**: 5-7 minutes for Terraform, then 10-15 minutes for bootstrap

**Note**: The bootstrap script runs automatically on the EC2 instance and:
- Installs K3s and Helm
- Deploys PostgreSQL with 100 products
- Installs Coralogix OpenTelemetry Collector
- Deploys all application services

---

## Step 4: Monitor Bootstrap Progress

Watch the bootstrap script to see when it completes:

```bash
# Replace <INSTANCE_IP> with the IP from Step 3 output
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@<INSTANCE_IP> \
  "tail -f /var/log/ecommerce-bootstrap.log"
```

**Wait for**: `"Bootstrap Complete!"` message

**Bootstrap stages**:
1. System update and dependencies
2. K3s installation
3. Namespace and secrets creation
4. PostgreSQL deployment
5. Coralogix OTel Collector installation
6. Application services deployment
7. Firewall configuration

**Expected time**: 10-15 minutes

**Tip**: Press `Ctrl+C` to exit log tailing (services continue running).

---

## Step 5: Verify Deployment

Run the health check script to verify everything is working:

```bash
./scripts/health-check-aws.sh
```

**What it checks**:
- ✅ EC2 instance is running
- ✅ SSH connectivity works
- ✅ K3s pods are running
- ✅ API Gateway endpoint is healthy
- ✅ Frontend endpoint is accessible

**Expected output**:
```
✓ All health checks passed (2/2)
```

**If health checks fail**: Wait a few more minutes for pods to fully start, then run again.

---

## Step 6: Access the Application

Open your browser and navigate to:

- **Frontend**: `http://<INSTANCE_IP>:30020`
- **API Gateway**: `http://<INSTANCE_IP>:30010`

**Test the application**:
1. Open the frontend
2. Enter a query: `"Looking for wireless headphones under $100"`
3. Click "Get AI Recommendations"
4. Observe AI-powered product recommendations

**Demo Controls** (bottom of page):
- "Simulate Slow Queries" - Triggers 2.8s database delays
- "Simulate Pool Exhaustion" - Exhausts database connections
- "Reset Simulations" - Returns to normal operation

---

## Step 7: Verify Coralogix Integration

### 7.1 Infrastructure Explorer

1. Go to https://eu2.coralogix.com
2. Navigate to **Infrastructure → Explorer**
3. Look for cluster: `ecommerce-demo`
4. Verify you see:
   - K3s node with CPU, memory, disk metrics
   - All pods listed
   - Network traffic visualization

### 7.2 AI Center

1. Navigate to **AI Center → Applications**
2. Select: `ecommerce-recommendation`
3. Make a recommendation request in the app
4. Verify you see:
   - LLM call with prompt and response content
   - Automatic evaluations:
     - Context Adherence score
     - Tool Parameter Correctness
     - Issue Rate percentage
   - Tool call success/failure indicators

### 7.3 APM (Traces)

1. Navigate to **APM → Services**
2. Select `recommendation-ai`
3. Click on a trace
4. Verify:
   - Complete trace: Frontend → API Gateway → Recommendation AI → Product Service → PostgreSQL
   - W3C trace context propagation
   - Kubernetes metadata (pod name, namespace)
   - Span attributes for tool calls

### 7.4 APM Pod & Host

1. In APM, select `recommendation-ai` service
2. Click **Pod & Host** tab
3. Verify:
   - Pod metrics (CPU, Memory usage)
   - Host metrics (Node performance)
   - Correlation between app performance and infrastructure

**Expected**: All four sections should show data within 2-3 minutes of deployment.

---

## Step 8: Run Demo Scenarios

Test the three built-in failure scenarios:

### Scenario 1: Normal Flow ✅
**Action**: Make a standard recommendation request
**Expected**: 
- Fast response (~500ms)
- High Context Adherence score in AI Center
- Tool call successful

### Scenario 2: Database Slowdown 🐌
**Action**: Click "Simulate Slow Queries (2.8s)"
**Expected**:
- Response time increases to ~3 seconds
- Histogram metrics show increased query duration
- P95 latency > 2800ms in Coralogix

### Scenario 3: Connection Pool Exhaustion 💥
**Action**: Click "Simulate Pool Exhaustion"
**Expected**:
- Some requests fail with timeout errors
- Database connection pool shows 100% utilization
- Error rate increases in traces

**Reset**: Click "Reset Simulations" to return to normal operation.

---

## Step 9: View Logs and Metrics

### SSH into the instance:
```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@<INSTANCE_IP>
```

### Check pod status:
```bash
kubectl get pods -n dataprime-demo
```

### View application logs:
```bash
# Recommendation AI service
kubectl logs -n dataprime-demo -l app=recommendation-ai --tail=50

# Product Service
kubectl logs -n dataprime-demo -l app=product-service --tail=50

# OpenTelemetry Collector
kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=50
```

### Check PostgreSQL:
```bash
kubectl exec -n dataprime-demo postgres-0 -- psql -U dbadmin -d productcatalog -c "SELECT COUNT(*) FROM products;"
```

**Expected**: 100 products

---

## Step 10: Cleanup (When Done)

When you're finished testing, destroy all resources:

```bash
./scripts/teardown-aws.sh
```

**What it does**:
1. Prompts for double confirmation (safety!)
2. Cleans up K3s resources (Helm releases, namespace)
3. Runs `terraform destroy`
4. Removes SSH key from local machine

**Prompts**:
- First: `Are you sure you want to destroy everything? (yes/no)`
- Second: `Type 'destroy' to confirm`

**Expected time**: 3-5 minutes

**Note**: This does NOT destroy the Terraform backend (S3 bucket and DynamoDB table). To remove those:
```bash
cd infrastructure/terraform/backend-setup
terraform destroy
```

---

## Troubleshooting

### Issue: Pods not starting

**Check pod status**:
```bash
kubectl get pods -n dataprime-demo
kubectl describe pod <pod-name> -n dataprime-demo
```

**Common causes**:
- Image pull issues: Verify images were built and imported
- Resource limits: t3.small may be at capacity
- PostgreSQL not ready: Wait for postgres-0 to be Running

### Issue: No telemetry in Coralogix

**Check OTel Collector**:
```bash
kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=100 | grep -i error
```

**Verify endpoint**:
```bash
kubectl exec -n dataprime-demo deployment/recommendation-ai -- env | grep OTEL
```

**Expected**: `OTEL_EXPORTER_OTLP_ENDPOINT=http://coralogix-opentelemetry-collector:4317`

**Common causes**:
- OTel Collector not running
- Invalid Coralogix token
- Network policy blocking egress

### Issue: OpenAI errors

**Check API key**:
```bash
kubectl exec -n dataprime-demo deployment/recommendation-ai -- env | grep OPENAI
```

**View logs**:
```bash
kubectl logs -n dataprime-demo -l app=recommendation-ai --tail=50 | grep -i openai
```

**Common causes**:
- Invalid or expired API key
- Rate limit exceeded
- Network connectivity to OpenAI

### Issue: Frontend not accessible

**Check service**:
```bash
kubectl get svc -n dataprime-demo frontend
```

**Expected**: NodePort 30020

**Check security group**:
```bash
aws ec2 describe-security-groups --filters "Name=tag:Name,Values=ecommerce-demo-sg" --query 'SecurityGroups[0].IpPermissions'
```

**Verify NodePort 30020 is allowed**.

---

## Cost Management

**Monthly Costs** (us-east-1):
- EC2 t3.small (730 hours): ~$15
- EBS 30GB gp3: ~$2.40
- Data transfer: ~$5
- **Total**: ~$22-25/month

**To minimize costs**:
1. Stop EC2 instance when not demoing:
   ```bash
   aws ec2 stop-instances --instance-ids <INSTANCE_ID>
   ```
2. Start it again when needed:
   ```bash
   aws ec2 start-instances --instance-ids <INSTANCE_ID>
   ```
3. Or destroy completely: `./scripts/teardown-aws.sh`

**Stopped instance cost**: ~$2.40/month (EBS storage only)

---

## Quick Reference

### Access URLs
- Frontend: `http://<INSTANCE_IP>:30020`
- API Gateway: `http://<INSTANCE_IP>:30010`
- Coralogix: `https://eu2.coralogix.com`

### Important Files
- Terraform state: `infrastructure/terraform/terraform.tfstate`
- SSH key: `~/.ssh/dataprime-demo-key.pem`
- Config: `infrastructure/terraform/terraform.tfvars`

### Useful Commands
```bash
# Get instance IP
cd infrastructure/terraform && terraform output instance_public_ip

# SSH to instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@<INSTANCE_IP>

# Check all pods
kubectl get pods -n dataprime-demo

# View logs
kubectl logs -n dataprime-demo -l app=<service-name> --tail=50

# Restart a service
kubectl rollout restart deployment/<deployment-name> -n dataprime-demo
```

---

## Success Criteria

Your deployment is successful when:

- [x] EC2 instance running and accessible via SSH
- [x] All K3s pods in Running state
- [x] Frontend accessible and functional
- [x] AI recommendations working with OpenAI
- [x] PostgreSQL has 100 products
- [x] Traces flowing to Coralogix with complete propagation
- [x] AI Center showing LLM calls with evaluations
- [x] Infrastructure Explorer showing K3s cluster
- [x] APM Pod & Host showing correlation
- [x] RUM tracking user sessions

---

## Support

If you encounter issues:

1. Check this troubleshooting section
2. Review logs: `kubectl logs -n dataprime-demo <pod-name>`
3. Verify secrets: `kubectl get secrets -n dataprime-demo`
4. Check the `AWS-DEPLOYMENT-GUIDE.md` for detailed information

---

**Ready to deploy?** Start with Step 1! 🚀


