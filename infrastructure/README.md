# DataPrime Demo - AWS Infrastructure

This directory contains Terraform configuration and automation scripts for deploying the DataPrime Demo to AWS EC2.

## 📁 Directory Structure

```
infrastructure/
├── terraform/
│   ├── main.tf                    # Main Terraform configuration
│   ├── variables.tf               # Input variables
│   ├── outputs.tf                 # Output values
│   ├── terraform.tfvars.example   # Example variables file
│   ├── .gitignore                 # Git ignore rules
│   ├── backend-setup/             # Terraform backend (S3 + DynamoDB)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── modules/
│   │   ├── vpc/                   # VPC with public subnet
│   │   ├── security/              # Security group, IAM, SSH key
│   │   └── ec2/                   # EC2 instance configuration
│   └── user-data/
│       └── bootstrap.sh.tpl       # EC2 initialization script
└── README.md (this file)
```

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** with programmatic access
2. **Terraform** >= 1.5 ([Install](https://www.terraform.io/downloads))
3. **AWS CLI** configured ([Install](https://aws.amazon.com/cli/))
4. **Required Credentials:**
   - Coralogix Send-Your-Data API key
   - OpenAI API key (for query generation)
   - Your public IP address (for SSH access)

### Step 1: Setup Terraform Backend (One-time)

```bash
cd /Users/andrescott/dataprime-assistant
./scripts/setup-terraform-backend.sh
```

This creates:
- S3 bucket for Terraform state
- DynamoDB table for state locking

**Important:** After this completes, update `infrastructure/terraform/main.tf` with the backend configuration shown in the script output.

### Step 2: Deploy to AWS

```bash
./scripts/deploy-aws.sh
```

This script will:
1. ✅ Check prerequisites (Terraform, AWS CLI, jq)
2. ✅ Prompt for required secrets (if needed)
3. ✅ Initialize Terraform
4. ✅ Create deployment plan
5. ✅ Deploy infrastructure to AWS
6. ✅ Save SSH key for instance access
7. ✅ Display access information

**Deployment time:** ~3 minutes for Terraform + ~10 minutes for bootstrapping

### Step 3: Verify Deployment

```bash
./scripts/health-check-aws.sh
```

This checks:
- EC2 instance status
- Docker containers
- Service health endpoints
- Application accessibility

### Step 4: Access Your Application

After deployment completes:

- **Frontend (HTTPS):** `https://<your-elastic-ip>`
- **API Gateway:** `http://<your-elastic-ip>:8010`
- **SSH Access:** `ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@<your-elastic-ip>`

### Step 5: Cleanup (When Done)

```bash
./scripts/teardown-aws.sh
```

This destroys all AWS resources (EC2, VPC, security groups, etc.)

---

## 💰 Cost Breakdown

| Resource | Specification | Monthly Cost |
|----------|---------------|--------------|
| EC2 Instance | t3.small (2 vCPU, 2GB RAM) | $15.18 |
| EBS Storage | 30GB gp3 | $2.40 |
| Elastic IP | 1 (attached) | $0.00 |
| Data Transfer | ~5GB/month | ~$0.45 |
| **TOTAL** | | **~$18/month** |

**Cost Savings vs. Typical Setup:**
- ✅ No RDS (using containerized SQLite): Save $15/month
- ✅ No ElastiCache (using containerized Redis): Save $13/month
- ✅ No NAT Gateway (public subnet only): Save $32/month
- ✅ No Load Balancer (direct access): Save $16/month
- **Total Savings: ~$76/month (80% reduction)**

---

## 🏗️ Architecture

```
Internet
    ↓
Elastic IP (Public)
    ↓
EC2 t3.small (Ubuntu 22.04)
├─ Security Group (SSH, HTTP, HTTPS, 8010)
├─ IAM Role (Coralogix Integration)
└─ Docker Compose Stack
   ├─ NGINX (Reverse proxy, SSL termination)
   ├─ Frontend (React app)
   ├─ API Gateway (Main API)
   ├─ 7 Microservices (Python)
   ├─ Redis (In-memory cache)
   ├─ SQLite (Persistent data)
   └─ OTel Collector (Infrastructure monitoring)
       └─ Sends to Coralogix
```

---

## 📝 Manual Deployment (Advanced)

If you prefer to run Terraform commands manually:

### 1. Backend Setup

```bash
cd infrastructure/terraform/backend-setup
terraform init
terraform apply
```

Note the S3 bucket name and DynamoDB table name.

### 2. Update Main Configuration

Edit `infrastructure/terraform/main.tf` and uncomment/update the backend block:

```hcl
backend "s3" {
  bucket         = "dataprime-demo-terraform-state-XXXXXXXX"  # From step 1
  key            = "dataprime-demo/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "dataprime-demo-terraform-locks"           # From step 1
  encrypt        = true
}
```

### 3. Create terraform.tfvars

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
coralogix_token  = "your-coralogix-token"
openai_api_key   = "sk-your-openai-key"
allowed_ssh_cidr = "your.ip.address.here/32"
```

### 4. Deploy

```bash
terraform init
terraform plan
terraform apply
```

### 5. Save SSH Key

```bash
terraform output -raw ssh_private_key > ~/.ssh/dataprime-demo-key.pem
chmod 600 ~/.ssh/dataprime-demo-key.pem
```

---

## 🔍 Monitoring Bootstrap

The EC2 instance runs a bootstrap script on first launch. Monitor its progress:

```bash
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@<elastic-ip> \
  "tail -f /var/log/dataprime-bootstrap.log"
```

Bootstrap steps:
1. ✅ System update and dependency installation
2. ✅ Docker and Docker Compose installation
3. ✅ Application code clone
4. ✅ Environment configuration
5. ✅ SSL certificate generation
6. ✅ Docker Compose services start
7. ✅ Systemd service configuration (auto-restart)
8. ✅ Firewall setup (UFW)
9. ✅ Health check monitoring (cron job)

**Total time:** ~5-10 minutes

---

## 🔧 Troubleshooting

### Services Not Starting

```bash
# SSH into instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@<elastic-ip>

# Check Docker Compose status
cd /opt/dataprime-assistant/deployment/docker
docker compose --env-file .env.vm -f docker-compose.vm.yml ps

# View logs
docker compose --env-file .env.vm -f docker-compose.vm.yml logs -f

# Restart services
docker compose --env-file .env.vm -f docker-compose.vm.yml restart
```

### SSH Connection Refused

- Instance may still be booting (wait 1-2 minutes)
- Check security group allows your IP: `allowed_ssh_cidr` in `terraform.tfvars`
- Verify your public IP: `curl https://checkip.amazonaws.com`

### Terraform State Locked

If Terraform reports a state lock error:

```bash
cd infrastructure/terraform
terraform force-unlock <lock-id>
```

### Cost Concerns

Check your AWS billing dashboard:
- Expected: ~$0.60/day = ~$18/month
- If higher, verify no orphaned resources

---

## 🔄 Updating the Deployment

To update application code or configuration:

### Method 1: Recreate Instance (Clean)

```bash
cd infrastructure/terraform
terraform destroy -auto-approve
terraform apply -auto-approve
```

### Method 2: Update In-Place (Fast)

```bash
# SSH into instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@<elastic-ip>

# Update code
cd /opt/dataprime-assistant
git pull

# Rebuild and restart services
cd deployment/docker
docker compose --env-file .env.vm -f docker-compose.vm.yml build
docker compose --env-file .env.vm -f docker-compose.vm.yml restart
```

---

## 🎯 Coralogix Integration

### Infrastructure Explorer

After deployment, view EC2 metrics in Coralogix:

1. Login to Coralogix: `https://coralogix.com`
2. Navigate to **Infrastructure Explorer**
3. Look for your instance (tagged with `dataprime-demo`)

**Metrics collected:**
- CPU usage, load average
- Memory usage
- Disk usage and I/O
- Network traffic
- Process metrics

**Metadata enrichment:**
- AWS Account ID
- Region
- Instance ID and type
- EC2 tags
- Availability Zone

### IAM Role for Cross-Account Access

The Terraform creates an IAM role that allows Coralogix to read EC2 metadata:

- **Role Name:** `dataprime-demo-coralogix-role`
- **Trust:** Coralogix AWS account (625240141681)
- **Permissions:** Read-only EC2 access (describe, get, list)
- **External ID:** Your Coralogix company ID (4015437)

---

## 📚 Additional Resources

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Coralogix Documentation](https://coralogix.com/docs/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Docker Compose Reference](https://docs.docker.com/compose/)

---

## 🆘 Support

If you encounter issues:

1. **Check logs:** `./scripts/health-check-aws.sh`
2. **Review bootstrap log:** `tail -f /var/log/dataprime-bootstrap.log`
3. **Validate Terraform:** `terraform validate`
4. **Check AWS console:** Verify resources exist

---

**Last Updated:** November 5, 2024  
**Terraform Version:** >= 1.5  
**AWS Provider:** ~> 5.0





