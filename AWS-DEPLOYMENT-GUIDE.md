# E-commerce Platform - AWS Deployment Guide 🚀

## Overview

This guide covers deploying the **E-commerce Platform** to AWS using:
- **EC2 t3.small instance** (2 vCPU, 2GB RAM, 30GB storage)
- **K3s** (lightweight Kubernetes) running on the EC2 instance
- **Docker images built on the instance** during bootstrap
- **8 microservices** with PostgreSQL and Redis
- **Coralogix OpenTelemetry Collector** for traces/metrics
- **Automated deployment** via Terraform

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     AWS EC2 Instance                     │
│                    (t3.small - 2GB)                      │
│ ┌─────────────────────────────────────────────────────┐ │
│ │                    K3s Cluster                       │ │
│ │                                                       │ │
│ │  ┌──────────────┐  ┌──────────────┐                 │ │
│ │  │ PostgreSQL   │  │    Redis     │                 │ │
│ │  └──────────────┘  └──────────────┘                 │ │
│ │                                                       │ │
│ │  ┌────────────────── Microservices ─────────────────┐│ │
│ │  │ • Load Generator    (8010)                      ││ │
│ │  │ • Product Catalog   (8014)                      ││ │
│ │  │ • Checkout          (8016)                      ││ │
│ │  │ • Cart              (8013)                      ││ │
│ │  │ • Recommendation    (8011)                      ││ │
│ │  │ • Currency          (8018)                      ││ │
│ │  │ • Shipping          (8019)                      ││ │
│ │  │ • Ad Service        (8017)                      ││ │
│ │  └───────────────────────────────────────────────────│ │
│ │                                                       │ │
│ │  ┌──────────────────────────────────────────────┐   │ │
│ │  │  Coralogix OpenTelemetry Collector          │   │ │
│ │  └──────────────────────────────────────────────┘   │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
             Coralogix EU2 Region
          https://eu2.coralogix.com
```

---

## Prerequisites

### 1. Tools Required
```bash
# Terraform
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads

# AWS CLI
brew install awscli  # macOS
# or: https://aws.amazon.com/cli/

# jq (JSON processor)
brew install jq  # macOS
```

### 2. AWS Credentials
Configure AWS CLI with your credentials:
```bash
aws configure
# AWS Access Key ID: YOUR_KEY
# AWS Secret Access Key: YOUR_SECRET
# Default region: us-east-1
# Default output format: json
```

Verify:
```bash
aws sts get-caller-identity
```

### 3. Coralogix Information
- **Token**: `cxtp_CukMevyNl9E9ukwf7A3PpwHw4cU5E6`
- **Region**: EU2
- **Application Name**: `ecommerce-platform`

---

## Deployment Steps

### Step 1: Setup Terraform Backend (One-Time)

Create S3 bucket and DynamoDB table for Terraform state:

```bash
cd /Users/andrescott/dataprime-assistant-1
./scripts/setup-terraform-backend.sh
```

This creates:
- S3 bucket: `dataprime-demo-terraform-state-<random>`
- DynamoDB table: `dataprime-demo-terraform-locks`

**Important**: Note the bucket name and update `infrastructure/terraform/main.tf` if needed.

### Step 2: Deploy to AWS

Run the automated deployment script:

```bash
./scripts/deploy-aws.sh
```

The script will:
1. ✅ Check prerequisites (Terraform, AWS CLI, jq)
2. ✅ Verify AWS credentials
3. ✅ Prompt for required variables:
   - Coralogix Token: `cxtp_CukMevyNl9E9ukwf7A3PpwHw4cU5E6`
   - Your IP for SSH: `YOUR_IP/32`
   - Coralogix RUM Key: (optional)
4. ✅ Create `terraform.tfvars`
5. ✅ Run `terraform init`
6. ✅ Run `terraform plan`
7. ✅ Ask for confirmation
8. ✅ Run `terraform apply`
9. ✅ Save SSH private key to `~/.ssh/ecommerce-platform-key.pem`
10. ✅ Display instance information

**Expected output:**
```
====================================================================
🎉 Deployment Complete!
====================================================================

Instance Information:
  ID:         i-0123456789abcdef
  Public IP:  54.123.45.67

Access Points:
  Load Generator: http://54.123.45.67:8010

SSH Access:
  ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.123.45.67

⏱️  Bootstrap Status:
The instance is currently:
  1. Installing Docker and K3s
  2. Building Docker images for 8 microservices
  3. Deploying PostgreSQL, Redis, and services
  4. Installing Coralogix OpenTelemetry Collector

This takes approximately 10-15 minutes.
```

### Step 3: Monitor Bootstrap Progress

SSH into the instance and tail the bootstrap log:

```bash
# Replace with your instance IP
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.123.45.67

# On the instance:
tail -f /var/log/ecommerce-bootstrap.log
```

**Bootstrap stages:**
1. [1/10] System updates and dependencies
2. [2/10] Docker installation
3. [3/10] K3s and Helm installation
4. [4/10] Clone application code
5. [5/10] **Build Docker images** (8 services) - takes 5-7 minutes
6. [6/10] Create K8s namespace and secrets
7. [7/10] Apply ConfigMap
8. [8/10] Deploy PostgreSQL and Redis
9. [9/10] Install Coralogix OTel Collector
10. [10/10] Deploy microservices
11. [11/11] Configure firewall

### Step 4: Verify Deployment

Check that all pods are running:

```bash
# SSH into instance
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@PUBLIC_IP

# Check pods
kubectl get pods -n ecommerce-demo

# Expected output:
# NAME                              READY   STATUS    RESTARTS   AGE
# load-generator-xxx                1/1     Running   0          2m
# product-catalog-xxx               1/1     Running   0          2m
# checkout-xxx                      1/1     Running   0          2m
# cart-xxx                          1/1     Running   0          2m
# recommendation-xxx                1/1     Running   0          2m
# currency-xxx                      1/1     Running   0          2m
# shipping-xxx                      1/1     Running   0          2m
# ad-service-xxx                    1/1     Running   0          2m
# postgresql-primary-0              1/1     Running   0          3m
# redis-0                           1/1     Running   0          3m
# coralogix-otel-xxx                1/1     Running   0          3m

# Check services
kubectl get svc -n ecommerce-demo
```

### Step 5: Generate Traffic

From your local machine:

```bash
# Replace with your instance public IP
PUBLIC_IP="54.123.45.67"

# Generate 60 seconds of traffic at 30 requests/minute
curl -X POST http://$PUBLIC_IP:8010/admin/generate-traffic \
  -H 'Content-Type: application/json' \
  -d '{"duration_seconds": 60, "requests_per_minute": 30}'
```

**Expected response:**
```json
{
  "status": "complete",
  "requests_generated": 30,
  "errors": 0,
  "duration_seconds": 60
}
```

### Step 6: View Traces in Coralogix

1. Open Coralogix EU2: https://eu2.coralogix.com
2. Navigate to **APM → Traces**
3. Filter by:
   - Application: `ecommerce-platform`
   - Subsystem: `ecommerce-services`
4. You should see distributed traces across:
   - load-generator → product-catalog
   - load-generator → checkout
   - product-catalog → PostgreSQL
   - checkout → PostgreSQL

---

## Docker Image Sizes

All images are built during bootstrap on the EC2 instance. Expected sizes:

| Service           | Size (MB) | Base Image          |
|-------------------|-----------|---------------------|
| load-generator    | ~450      | python:3.11-slim    |
| product-catalog   | ~450      | python:3.11-slim    |
| checkout          | ~450      | python:3.11-slim    |
| cart              | ~450      | python:3.11-slim    |
| recommendation    | ~450      | python:3.11-slim    |
| currency          | ~450      | python:3.11-slim    |
| shipping          | ~450      | python:3.11-slim    |
| ad-service        | ~450      | python:3.11-slim    |

**All images are under 1GB** ✅

---

## Cost Breakdown

**Monthly estimate (us-east-1):**
- EC2 t3.small (on-demand): ~$15.00/month
- EBS 30GB gp3: ~$2.40/month
- Data transfer (minimal): ~$1.00/month
- **Total: ~$18.40/month**

---

## Troubleshooting

### Bootstrap is taking too long
```bash
# SSH into instance
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@PUBLIC_IP

# Check bootstrap log
tail -f /var/log/ecommerce-bootstrap.log

# Check Docker build progress
docker ps
docker images | grep ecommerce-
```

### Pods are not starting
```bash
# Check pod status
kubectl get pods -n ecommerce-demo

# Check pod logs
kubectl logs -n ecommerce-demo <pod-name>

# Describe pod for events
kubectl describe pod -n ecommerce-demo <pod-name>

# Check if images were built
docker images | grep ecommerce-
```

### Database connection errors
```bash
# Check PostgreSQL pod
kubectl get pod -n ecommerce-demo -l app=postgresql

# Check PostgreSQL logs
kubectl logs -n ecommerce-demo postgresql-primary-0

# Test PostgreSQL connection
kubectl exec -it -n ecommerce-demo postgresql-primary-0 -- psql -U ecommerce_user -d ecommerce -c "SELECT version();"
```

### No traces in Coralogix
```bash
# Check OTel Collector logs
kubectl logs -n ecommerce-demo -l app.kubernetes.io/name=opentelemetry-collector

# Check service logs for trace IDs
kubectl logs -n ecommerce-demo -l app=product-catalog | grep "trace"

# Verify Coralogix token is set
kubectl get secret -n ecommerce-demo ecommerce-secrets -o json | jq -r '.data.CX_TOKEN' | base64 -d
```

### SSH connection refused
```bash
# Check security group allows your IP
aws ec2 describe-security-groups --group-ids <sg-id>

# Update security group if needed
./scripts/deploy-aws.sh  # Will update with new IP
```

---

## Cleanup

### Destroy All Resources

```bash
cd /Users/andrescott/dataprime-assistant-1
./scripts/teardown-aws.sh
```

Or manually:
```bash
cd infrastructure/terraform
terraform destroy
```

**This will delete:**
- EC2 instance
- Elastic IP
- Security group
- IAM role
- VPC and subnet

**Cost will stop immediately.**

---

## Advanced Operations

### View K3s cluster info
```bash
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@PUBLIC_IP
kubectl cluster-info
kubectl get nodes
kubectl top nodes  # Resource usage
```

### Restart a service
```bash
kubectl rollout restart deployment/product-catalog -n ecommerce-demo
```

### Scale a service
```bash
kubectl scale deployment/product-catalog --replicas=2 -n ecommerce-demo
```

### Update environment variables
```bash
# Edit ConfigMap
kubectl edit configmap ecommerce-config -n ecommerce-demo

# Restart deployments to pick up changes
kubectl rollout restart deployment --all -n ecommerce-demo
```

### Enable demo mode (Black Friday)
```bash
# SSH into instance
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@PUBLIC_IP

# Update ConfigMap
kubectl patch configmap ecommerce-config -n ecommerce-demo \
  -p '{"data":{"DEMO_MODE":"blackfriday"}}'

# Restart services
kubectl rollout restart deployment --all -n ecommerce-demo
```

---

## Files Modified for AWS Deployment

| File | Changes |
|------|---------|
| `infrastructure/terraform/variables.tf` | Updated project name, app name, subsystem, domain |
| `infrastructure/terraform/user-data/bootstrap.sh.tpl` | Complete rewrite for e-commerce services |
| `scripts/deploy-aws.sh` | Updated prompts, removed OpenAI, updated paths |
| `deployment/kubernetes/namespace.yaml` | Changed to `ecommerce-demo` |
| `deployment/kubernetes/configmap.yaml` | Updated for e-commerce services |
| `deployment/kubernetes/services.yaml` | Services for 8 microservices |
| `deployment/kubernetes/deployments/*.yaml` | 8 new deployment files |

---

## Next Steps

1. ✅ Deploy to AWS: `./scripts/deploy-aws.sh`
2. ✅ Wait 10-15 minutes for bootstrap
3. ✅ Generate traffic: `curl -X POST http://$IP:8010/admin/generate-traffic`
4. ✅ View traces in Coralogix: https://eu2.coralogix.com
5. ✅ Demo for re:Invent 2025!

---

## Quick Reference

**Coralogix:**
- Token: `cxtp_CukMevyNl9E9ukwf7A3PpwHw4cU5E6`
- Endpoint: `https://ingress.eu2.coralogix.com:443`
- Application: `ecommerce-platform`
- Region: EU2
- URL: https://eu2.coralogix.com

**AWS:**
- Region: us-east-1
- Instance Type: t3.small
- OS: Ubuntu 22.04 LTS

**K3s:**
- Namespace: `ecommerce-demo`
- ConfigMap: `ecommerce-config`
- Secrets: `ecommerce-secrets`

**Services:**
- Load Generator: 8010
- Product Catalog: 8014
- Checkout: 8016
- Cart: 8013
- Recommendation: 8011
- Currency: 8018
- Shipping: 8019
- Ad Service: 8017

---

## Support

For issues:
1. Check bootstrap log: `/var/log/ecommerce-bootstrap.log`
2. Check pod logs: `kubectl logs -n ecommerce-demo <pod-name>`
3. Verify Coralogix connectivity: Check OTel Collector logs

**Ready for AWS re:Invent 2025! 🎉**

