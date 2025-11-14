# Phase 3: AWS VM Deployment - Terraform Automation

**Date:** November 2, 2024  
**Status:** Planning (Local testing complete ✅)  
**Architecture:** SQLite + Redis (simplified, proven working)

---

## Overview

Deploy the **working local stack** to AWS EC2 with Terraform automation, maintaining the simplified SQLite architecture that we've proven works locally.

### Goals
✅ **Single-command deployment** - `./scripts/deploy-aws.sh`  
✅ **Cost optimized** - Under $20/month  
✅ **Production ready** - SSL, monitoring, health checks  
✅ **Infrastructure monitoring** - Coralogix Infrastructure Explorer integration  
✅ **Fully automated** - No manual steps after initial setup  

---

## Cost Strategy (Minimal AWS Resources)

| Resource | Specification | Monthly Cost |
|----------|---------------|--------------|
| EC2 Instance | t3.small (2 vCPU, 2GB RAM) | $15.18 |
| EBS Storage | 30GB gp3 | $2.40 |
| Elastic IP | 1 (attached) | $0.00 |
| Data Transfer | ~5GB/month | ~$0.45 |
| **TOTAL** | | **~$18/month** |

**Key Savings:**
- ❌ No RDS (use containerized SQLite) - Save $15/month
- ❌ No ElastiCache (use containerized Redis) - Save $13/month  
- ❌ No NAT Gateway - Save $32/month
- ❌ No Application Load Balancer - Save $16/month
- ✅ Self-signed SSL - Save $0/month vs paid certs

**Total Savings: ~$76/month (80% reduction from typical setup)**

---

## Architecture on AWS

```
Internet
    ↓
Elastic IP (Public)
    ↓
EC2 t3.small (Ubuntu 22.04)
├─ Docker Compose
│  ├─ NGINX (SSL termination, reverse proxy)
│  ├─ Frontend (Port 8020)
│  ├─ API Gateway (Port 8010)
│  ├─ 7 Microservices (8011-8017)
│  ├─ Redis (Port 6379, persistent volume)
│  ├─ OTel Collector (Host metrics → Coralogix)
│  └─ SQLite (Volume mount at /app/data)
└─ Security Group (SSH, HTTP, HTTPS)
```

**No changes from local setup** - same Docker Compose file works on AWS!

---

## Implementation Plan

### Phase 3.1: Terraform Backend Setup (5 min)

**Purpose:** Store Terraform state in S3 with DynamoDB locking

**Files to create:**
1. `infrastructure/terraform/backend-setup/main.tf`
2. `infrastructure/terraform/backend-setup/variables.tf`
3. `infrastructure/terraform/backend-setup/outputs.tf`

**What it does:**
- Creates S3 bucket: `dataprime-terraform-state-<random>`
- Enables versioning and encryption
- Creates DynamoDB table: `dataprime-terraform-locks`
- Outputs backend config for main Terraform

**Command:**
```bash
cd infrastructure/terraform/backend-setup
terraform init
terraform apply
# Outputs: bucket_name, dynamodb_table
```

---

### Phase 3.2: Main Terraform Infrastructure (30 min)

#### File Structure
```
infrastructure/terraform/
├── main.tf              # Main config, module orchestration
├── variables.tf         # Input variables
├── outputs.tf           # Outputs (IP, SSH command, etc)
├── terraform.tfvars     # Local values (gitignored)
├── modules/
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── security/
│   │   ├── main.tf      # Security group, IAM role, SSH key
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── ec2/
│       ├── main.tf      # EC2 instance, EBS, bootstrap
│       ├── variables.tf
│       └── outputs.tf
└── user-data/
    └── bootstrap.sh.tpl # Bootstrap script template
```

#### Module Details

**VPC Module** (Minimal)
- VPC: 10.0.0.0/16
- 1 public subnet: 10.0.1.0/24 (us-east-1a)
- Internet Gateway
- Public route table
- **No private subnet, no NAT Gateway** (cost savings)

**Security Module**
- Security group rules:
  - SSH (22) from your IP only
  - HTTP (80) from 0.0.0.0/0
  - HTTPS (443) from 0.0.0.0/0
  - API Gateway (8010) from 0.0.0.0/0 (for testing)
- IAM role for Coralogix Infrastructure Explorer:
  - Trust relationship to Coralogix AWS account
  - Read-only EC2 describe permissions
  - Company ID: 4015437
- SSH key pair generation:
  - Generate new RSA key via Terraform
  - Store public key in AWS
  - Output private key (sensitive)

**EC2 Module**
- Instance: t3.small (2 vCPU, 2GB RAM)
- AMI: Latest Ubuntu 22.04 LTS (auto-lookup)
- Root volume: 30GB gp3 (cheaper than gp2)
- Elastic IP attachment
- IAM instance profile (Coralogix role)
- User data: bootstrap script
- Tags for Coralogix metadata enrichment

---

### Phase 3.3: Bootstrap Script (Critical!)

**File:** `infrastructure/terraform/user-data/bootstrap.sh.tpl`

**What it does:**
1. ✅ System update and security patches
2. ✅ Install Docker + Docker Compose plugin
3. ✅ Clone/upload DataPrime Assistant code
4. ✅ Create `.env.vm` from Terraform variables
5. ✅ Start Docker Compose stack
6. ✅ Generate self-signed SSL certificate
7. ✅ Configure firewall (UFW)
8. ✅ Set up systemd service for auto-restart
9. ✅ Create health check cron job

**Key features:**
- **Idempotent** - can be run multiple times safely
- **Logged** - outputs to `/var/log/dataprime-bootstrap.log`
- **Error handling** - exits on any error
- **Health verification** - waits for services to be healthy

**Template variables:**
```bash
#!/bin/bash
set -euxo pipefail

# Templated by Terraform
CX_TOKEN="${coralogix_token}"
CX_DOMAIN="${coralogix_domain}"
OPENAI_API_KEY="${openai_api_key}"
ENVIRONMENT="production"

# Install Docker
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin

# Setup application
mkdir -p /opt/dataprime-assistant
cd /opt/dataprime-assistant

# Clone or copy code (from S3 or Git)
# For now, we'll upload as artifact

# Create environment file
cat > deployment/docker/.env.vm <<EOF
CX_TOKEN=${CX_TOKEN}
CX_DOMAIN=${CX_DOMAIN}
OPENAI_API_KEY=${OPENAI_API_KEY}
# ... etc
EOF

# Start services
cd deployment/docker
docker compose --env-file .env.vm -f docker-compose.vm.yml up -d

# Wait for health checks
sleep 30

# Verify all healthy
docker compose --env-file .env.vm -f docker-compose.vm.yml ps

echo "✅ Bootstrap complete!"
```

---

### Phase 3.4: Automation Scripts (20 min)

**1. Terraform Backend Setup Script**

**File:** `scripts/setup-terraform-backend.sh`
```bash
#!/bin/bash
# One-time setup for Terraform backend
# Creates S3 bucket and DynamoDB table
# Outputs backend config for main.tf
```

**2. AWS Deployment Script**

**File:** `scripts/deploy-aws.sh`
```bash
#!/bin/bash
# Main deployment script
# - Checks AWS credentials
# - Prompts for secrets (CX_TOKEN, OPENAI_API_KEY)
# - Runs Terraform apply
# - Saves SSH key
# - Displays access info
# - Runs health checks
```

**3. Health Check Script**

**File:** `scripts/health-check-aws.sh`
```bash
#!/bin/bash
# Connects to EC2 instance
# Checks all service health endpoints
# Verifies OTel Collector metrics
# Tests frontend accessibility
```

**4. Teardown Script**

**File:** `scripts/teardown-aws.sh`
```bash
#!/bin/bash
# Confirms deletion
# Runs terraform destroy
# Removes SSH key from local machine
# Cleans up local state
```

---

### Phase 3.5: NGINX Configuration (10 min)

**Files:**
- `deployment/docker/nginx/nginx.conf` (already exists, verify)
- `deployment/docker/nginx/conf.d/dataprime.conf` (already exists, verify)
- `deployment/docker/nginx/ssl/generate-certs.sh` (already exists, verify)

**Updates needed:**
- ✅ Ensure SSL paths are correct
- ✅ Add real domain support (optional)
- ✅ Security headers for production
- ✅ Rate limiting configuration

**No major changes needed** - current NGINX config will work!

---

### Phase 3.6: Documentation (15 min)

**File:** `docs/AWS-DEPLOYMENT.md`

**Contents:**
1. Prerequisites (AWS account, credentials, Terraform)
2. Cost breakdown and expectations
3. Step-by-step deployment guide
4. Accessing the application
5. Verifying Coralogix integration
6. Troubleshooting common issues
7. Updating the deployment
8. Destroying resources

**File:** `docs/ARCHITECTURE-AWS.md`

**Contents:**
1. AWS infrastructure diagram
2. Network topology
3. Security model
4. Data persistence strategy (SQLite + EBS)
5. Coralogix integration points
6. Scaling considerations (when to upgrade)

---

## Implementation Order

### Step 1: Terraform Backend (Day 1, Morning)
⏱️ **Time:** ~30 minutes
- [ ] Create `backend-setup/` directory structure
- [ ] Write Terraform configs for S3 + DynamoDB
- [ ] Run `terraform apply` to create backend
- [ ] Note outputs for main config

### Step 2: Terraform Modules (Day 1, Afternoon)
⏱️ **Time:** ~2 hours
- [ ] Create VPC module (minimal, public only)
- [ ] Create Security module (SG + IAM + SSH key)
- [ ] Create EC2 module (t3.small + user data)
- [ ] Write main.tf to orchestrate modules
- [ ] Define variables and outputs

### Step 3: Bootstrap Script (Day 1, Evening)
⏱️ **Time:** ~1 hour
- [ ] Write bootstrap.sh.tpl
- [ ] Add Docker installation
- [ ] Add application setup
- [ ] Add health checks
- [ ] Test locally with `bash -n` (syntax check)

### Step 4: Automation Scripts (Day 2, Morning)
⏱️ **Time:** ~1 hour
- [ ] Write deploy-aws.sh
- [ ] Write health-check-aws.sh
- [ ] Write teardown-aws.sh
- [ ] Make executable: `chmod +x scripts/*.sh`

### Step 5: Testing (Day 2, Afternoon)
⏱️ **Time:** ~2 hours
- [ ] Dry run: `terraform plan`
- [ ] Deploy to AWS: `./scripts/deploy-aws.sh`
- [ ] Wait for bootstrap (~5 min)
- [ ] Run health checks
- [ ] Test application functionality
- [ ] Verify Coralogix metrics

### Step 6: Documentation (Day 2, Evening)
⏱️ **Time:** ~1 hour
- [ ] Write deployment guide
- [ ] Document troubleshooting steps
- [ ] Update main README
- [ ] Create architecture diagrams

### Step 7: Cleanup Test (Day 3)
⏱️ **Time:** ~30 minutes
- [ ] Run `./scripts/teardown-aws.sh`
- [ ] Verify all resources deleted
- [ ] Check AWS billing console
- [ ] Re-deploy to confirm reproducibility

---

## Key Variables for Terraform

**Required (Secrets):**
```hcl
variable "coralogix_token" {
  description = "Coralogix Send-Your-Data API key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key for query generation"
  type        = string
  sensitive   = true
}

variable "allowed_ssh_cidr" {
  description = "Your IP address for SSH access (x.x.x.x/32)"
  type        = string
}
```

**Optional (With Defaults):**
```hcl
variable "aws_region" {
  default = "us-east-1"
}

variable "instance_type" {
  default = "t3.small"  # 2 vCPU, 2GB RAM
}

variable "root_volume_size" {
  default = 30  # GB
}

variable "project_name" {
  default = "dataprime-demo"
}

variable "environment" {
  default = "production"
}

variable "coralogix_domain" {
  default = "coralogix.com"
}

variable "coralogix_company_id" {
  default = "4015437"
}
```

---

## Expected Outputs

After `terraform apply`:
```
Outputs:

instance_id = "i-0123456789abcdef0"
instance_public_ip = "54.123.45.67"
instance_private_ip = "10.0.1.100"
ssh_private_key = <sensitive>
application_url = "https://54.123.45.67"
ssh_command = "ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.123.45.67"

Next steps:
1. Wait 2-3 minutes for bootstrap to complete
2. Access application: https://54.123.45.67
3. Check logs: ssh ubuntu@54.123.45.67 "tail -f /var/log/dataprime-bootstrap.log"
4. Verify Coralogix: https://coralogix.com (Infrastructure Explorer)
```

---

## Success Criteria

### ✅ Infrastructure Deployed
- [ ] Terraform apply completes successfully
- [ ] EC2 instance is running
- [ ] Elastic IP is attached
- [ ] Security group allows HTTP/HTTPS/SSH
- [ ] IAM role attached for Coralogix

### ✅ Application Running
- [ ] All 11 containers healthy
- [ ] Frontend accessible via public IP
- [ ] API Gateway responding
- [ ] SQLite database created on EBS volume
- [ ] Redis persisting data

### ✅ Observability Working
- [ ] OTel Collector scraping host metrics
- [ ] Metrics visible in Coralogix Infrastructure Explorer
- [ ] EC2 metadata attached to telemetry
- [ ] Distributed traces flowing to Coralogix
- [ ] Service map showing all microservices

### ✅ Production Ready
- [ ] SSL/TLS working (self-signed)
- [ ] NGINX reverse proxy configured
- [ ] Health checks passing
- [ ] Auto-restart on failure (systemd)
- [ ] Firewall configured (UFW)

### ✅ Cost Verified
- [ ] AWS billing shows <$1/day
- [ ] Monthly projection <$20
- [ ] No unexpected charges

---

## Differences from Local Setup

| Aspect | Local (Docker Desktop) | AWS (EC2) |
|--------|------------------------|-----------|
| Host | macOS/Windows | Ubuntu 22.04 LTS |
| Networking | Docker bridge | Docker bridge (same) |
| SSL | Self-signed (optional) | Self-signed (required) |
| Access | localhost:8020 | Elastic IP:443 |
| Persistence | Docker volumes | EBS-backed volumes |
| OTel Host Metrics | Mac system | EC2 instance |
| Resource Detection | system detector | ec2 detector |
| Metadata | Local hostname | AWS region, instance ID, tags |

**Key insight:** Same Docker Compose file works on both! 🎉

---

## Risks & Mitigations

### Risk 1: Bootstrap Script Fails
**Mitigation:**
- Comprehensive error handling in script
- Log to `/var/log/dataprime-bootstrap.log`
- SSH access to debug
- Can manually run commands

### Risk 2: Out of Memory on t3.small
**Mitigation:**
- We've tested locally and memory usage is ~1.9GB
- t3.small has 2GB RAM (comfortable margin)
- Resource limits on all containers
- Can upgrade to t3.medium if needed ($30/month)

### Risk 3: EBS Volume Issues with SQLite
**Mitigation:**
- EBS provides persistent block storage
- SQLite works fine on EBS (single-instance)
- Regular snapshots via AWS Backup (optional)
- Can switch to t3.small with local SSD if needed

### Risk 4: Security Group Misconfiguration
**Mitigation:**
- Terraform manages security group
- Only necessary ports exposed
- SSH limited to your IP
- Can update rules via Terraform

### Risk 5: Coralogix Integration Issues
**Mitigation:**
- Test OTel Collector locally first
- Verify CX_TOKEN is valid
- Check Coralogix domain (coralogix.com vs coralogix.eu)
- OTel Collector logs show export attempts

---

## Future Enhancements (Phase 4+)

**Not in scope for Phase 3, but good to plan:**

1. **Kubernetes Deployment**
   - Migrate to EKS
   - Helm charts
   - Auto-scaling

2. **Multi-Language Services**
   - Add Go service (high-performance)
   - Add Node.js service (WebSocket)

3. **Production Database**
   - Migrate to RDS PostgreSQL
   - Connection pooling
   - Read replicas

4. **Advanced Coralogix**
   - Custom dashboards
   - Alert policies
   - SLO monitoring

5. **CI/CD Pipeline**
   - GitHub Actions
   - Automated testing
   - Blue-green deployment

---

## Quick Start (Once Implementation Complete)

```bash
# 1. Setup Terraform backend (one-time)
./scripts/setup-terraform-backend.sh

# 2. Deploy to AWS
./scripts/deploy-aws.sh
# Prompts for: CX_TOKEN, OPENAI_API_KEY, Your IP address

# 3. Wait ~5 minutes for bootstrap

# 4. Access application
# URL will be displayed in terminal output

# 5. Verify Coralogix
# Check Infrastructure Explorer in Coralogix UI

# 6. Destroy when done testing
./scripts/teardown-aws.sh
```

---

## Estimated Effort

| Task | Time | Complexity |
|------|------|------------|
| Terraform Backend | 30 min | Low |
| VPC Module | 30 min | Low |
| Security Module | 1 hour | Medium |
| EC2 Module | 1 hour | Medium |
| Bootstrap Script | 2 hours | High |
| Automation Scripts | 1 hour | Medium |
| Testing | 2 hours | Medium |
| Documentation | 1 hour | Low |
| **TOTAL** | **~9 hours** | **Medium** |

**Recommendation:** Spread over 2-3 days for quality work.

---

## Files to Create

### Terraform (11 files)
- [x] `infrastructure/terraform/backend-setup/main.tf`
- [x] `infrastructure/terraform/backend-setup/variables.tf`
- [x] `infrastructure/terraform/backend-setup/outputs.tf`
- [x] `infrastructure/terraform/main.tf`
- [x] `infrastructure/terraform/variables.tf`
- [x] `infrastructure/terraform/outputs.tf`
- [x] `infrastructure/terraform/modules/vpc/main.tf`
- [x] `infrastructure/terraform/modules/security/main.tf`
- [x] `infrastructure/terraform/modules/ec2/main.tf`
- [x] `infrastructure/terraform/user-data/bootstrap.sh.tpl`
- [x] `.gitignore` updates (*.tfstate, *.tfvars)

### Scripts (4 files)
- [ ] `scripts/setup-terraform-backend.sh`
- [ ] `scripts/deploy-aws.sh`
- [ ] `scripts/health-check-aws.sh`
- [ ] `scripts/teardown-aws.sh`

### Documentation (2 files)
- [ ] `docs/AWS-DEPLOYMENT.md`
- [ ] `docs/ARCHITECTURE-AWS.md`

### Total: 17 new files

---

## Status: Ready to Begin

✅ **Prerequisites Met:**
- Local stack working perfectly
- All 11 services healthy
- Docker networking fixed
- SQLite persistence verified
- OTel Collector configured
- Docker Compose ready for AWS

**Next Step:** Create Terraform backend setup! 🚀

---

**Last Updated:** November 2, 2024, 6:15 PM EDT  
**Status:** Planning Complete, Ready for Implementation  
**Estimated Completion:** November 4-5, 2024






