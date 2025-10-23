# DataPrime Assistant - VM Deployment Guide

Complete guide for deploying DataPrime Assistant to AWS using Terraform automation.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Cost Breakdown](#cost-breakdown)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Accessing the Application](#accessing-the-application)
- [Verifying Coralogix Integration](#verifying-coralogix-integration)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Teardown](#teardown)

## Prerequisites

### Required Tools
- **Terraform** >= 1.5 - [Install](https://www.terraform.io/downloads)
- **AWS CLI** >= 2.x - [Install](https://aws.amazon.com/cli/)
- **jq** - JSON processor - `brew install jq` (macOS) or `apt-get install jq` (Linux)
- **Git** - Version control
- **SSH** client

### AWS Requirements
- AWS account with appropriate permissions
- AWS CLI configured with credentials (`aws configure`)
- Permissions to create: EC2, VPC, IAM, S3, DynamoDB

### Coralogix Requirements
- Active Coralogix account
- Send Data API Key (from Settings → Send Data)
- Company ID (from Settings → Account)
- AI Center enabled (optional, for advanced features)

### OpenAI Requirements
- OpenAI API key with GPT-4 access

## Cost Breakdown

### Monthly AWS Costs (t3.small deployment)
| Resource | Monthly Cost |
|----------|--------------|
| EC2 t3.small (730 hrs) | $15.18 |
| EBS gp3 30GB | $2.40 |
| Elastic IP (attached) | $0.00 |
| Data Transfer (~10GB) | ~$1.00 |
| **Total** | **~$18.58/month** |

**Cost optimization features:**
- Single AZ deployment (no cross-AZ data transfer)
- Containerized databases (no RDS/ElastiCache costs)
- No NAT Gateway ($32/month savings)
- Standard monitoring (no detailed monitoring)
- gp3 storage (cheaper than gp2)

## Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo>
cd dataprime-assistant
```

### 2. Set Environment Variables
```bash
# Required secrets
export TF_VAR_coralogix_token="your_coralogix_token"
export TF_VAR_openai_api_key="your_openai_key"
export TF_VAR_postgres_password="$(openssl rand -base64 32)"

# Optional: Your IP for SSH access
export TF_VAR_allowed_ssh_cidr="$(curl -s ifconfig.me)/32"
```

### 3. Setup Terraform Backend (One-time)
```bash
./scripts/setup-terraform-backend.sh
```

### 4. Deploy Infrastructure
```bash
./scripts/deploy-vm.sh dev
```

### 5. Access Application
The script will output URLs when complete:
- Frontend: `https://<ELASTIC_IP>`
- API: `http://<ELASTIC_IP>:8010/api/health`

## Detailed Setup

### Step 1: Terraform Backend Setup

The Terraform backend uses S3 for state storage and DynamoDB for state locking.

```bash
# Run the backend setup script
./scripts/setup-terraform-backend.sh

# This creates:
# - S3 bucket: dataprime-demo-terraform-state-us-east-1
# - DynamoDB table: dataprime-demo-terraform-locks
# - backend.tf configuration file
```

**Note:** This only needs to be done once per AWS account/region.

### Step 2: Configure Deployment

Edit `infrastructure/terraform/environments/dev.tfvars`:

```hcl
# Update with your IP address for SSH access
allowed_ssh_cidr = "YOUR_IP/32"

# Customize instance type if needed
instance_type = "t3.small"  # or "t3.medium" for more power
```

### Step 3: Set Secrets

**Option A: Environment Variables** (Recommended)
```bash
export TF_VAR_coralogix_token="your_token"
export TF_VAR_openai_api_key="sk-..."
export TF_VAR_postgres_password="secure_password"
```

**Option B: terraform.tfvars file** (Don't commit!)
```bash
cd infrastructure/terraform
cat > terraform.tfvars <<EOF
coralogix_token = "your_token"
openai_api_key = "sk-..."
postgres_password = "secure_password"
EOF
chmod 600 terraform.tfvars
```

### Step 4: Deploy

**Using automation script (recommended):**
```bash
./scripts/deploy-vm.sh dev
```

**Manual deployment:**
```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan
terraform plan -var-file=environments/dev.tfvars -out=tfplan

# Apply
terraform apply tfplan
```

### Step 5: Save SSH Key

```bash
# Extract SSH private key
cd infrastructure/terraform
terraform output -raw ssh_private_key > ~/.ssh/dataprime-demo-key.pem
chmod 600 ~/.ssh/dataprime-demo-key.pem
```

## Accessing the Application

### Get Instance Information
```bash
cd infrastructure/terraform
terraform output
```

### SSH Access
```bash
# Get the public IP
PUBLIC_IP=$(terraform output -raw elastic_ip)

# Connect
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$PUBLIC_IP
```

### Application URLs
- **Frontend**: `https://<PUBLIC_IP>`
  - Accept self-signed certificate warning
- **API Gateway**: `http://<PUBLIC_IP>:8010/api/health`
- **OpenTelemetry Collector**: `http://<PUBLIC_IP>:13133` (health)

### Monitor Bootstrap Progress
```bash
# SSH into instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$PUBLIC_IP

# Monitor bootstrap
tail -f /var/log/cloud-init-output.log

# Check DataPrime bootstrap log
tail -f /var/log/dataprime-bootstrap.log

# Check Docker services
cd /opt/dataprime-assistant/deployment/docker
docker compose -f docker-compose.vm.yml ps
docker compose -f docker-compose.vm.yml logs -f
```

## Verifying Coralogix Integration

### 1. Infrastructure Metrics
Navigate to Coralogix → Infrastructure Explorer:
- Verify EC2 instance appears
- Check host metrics (CPU, memory, disk, network)
- Verify EC2 metadata enrichment (instance type, AZ, tags)

### 2. Application Traces
Navigate to Coralogix → APM → Traces:
- Generate a query in the application
- Find traces with service name `dataprime_assistant`
- Verify distributed tracing across all 8 microservices
- Check trace correlation with infrastructure metrics

### 3. Logs
Navigate to Coralogix → Logs:
- Filter by application: `dataprime-demo`
- Verify structured logs from all services
- Check log-trace correlation

### 4. AI Center (if enabled)
Navigate to Coralogix → AI Center → Evaluations:
- Verify OpenAI interactions are captured
- Check content evaluation policies
- Review AI usage metrics

## Troubleshooting

### Services Not Starting
```bash
# Check Docker status
sudo systemctl status docker

# Check container status
cd /opt/dataprime-assistant/deployment/docker
docker compose -f docker-compose.vm.yml ps

# View logs
docker compose -f docker-compose.vm.yml logs

# Restart services
docker compose -f docker-compose.vm.yml restart
```

### No Data in Coralogix
1. **Verify credentials:**
   ```bash
   # Check environment file
   cat /opt/dataprime-assistant/deployment/docker/.env.vm | grep CX_TOKEN
   ```

2. **Check OpenTelemetry Collector:**
   ```bash
   docker logs otel-collector
   curl http://localhost:13133  # Health check
   ```

3. **Verify domain configuration:**
   - Ensure `CX_DOMAIN` matches your Coralogix region
   - Common: `coralogix.com`, `coralogix.us`, `coralogix.in`

### High Memory Usage
```bash
# Check memory usage
free -h
docker stats --no-stream

# Restart memory-intensive services
docker compose -f /opt/dataprime-assistant/deployment/docker/docker-compose.vm.yml restart api-gateway
```

### SSL Certificate Warnings
The deployment uses self-signed certificates. This is normal for demos.

**For production**, use Let's Encrypt:
```bash
# Install certbot
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d your-domain.com

# Update NGINX configuration to use Let's Encrypt certs
```

## Maintenance

### Health Checks
```bash
# Run health check script
./scripts/health-check.sh <PUBLIC_IP>

# Or manually check endpoints
curl http://<PUBLIC_IP>:8010/api/health
```

### View Logs
```bash
# SSH into instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$PUBLIC_IP

# Application logs
cd /opt/dataprime-assistant/deployment/docker
docker compose -f docker-compose.vm.yml logs -f

# Specific service
docker compose -f docker-compose.vm.yml logs -f api-gateway

# Bootstrap log
tail -f /var/log/dataprime-bootstrap.log
```

### Update Application
```bash
# SSH into instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$PUBLIC_IP

# Pull latest changes
cd /opt/dataprime-assistant
git pull

# Rebuild and restart
cd deployment/docker
docker compose -f docker-compose.vm.yml build
docker compose -f docker-compose.vm.yml up -d
```

### Backup Database
```bash
# Backup PostgreSQL
docker exec postgres pg_dump -U dataprime dataprime_demo > backup.sql

# Restore
cat backup.sql | docker exec -i postgres psql -U dataprime dataprime_demo
```

## Teardown

### Complete Infrastructure Removal
```bash
# Using automation script
./scripts/teardown.sh dev

# Manual
cd infrastructure/terraform
terraform destroy -var-file=environments/dev.tfvars
```

**Note:** The S3 backend and DynamoDB table are not deleted (prevent_destroy enabled).

To remove backend resources:
```bash
cd infrastructure/terraform/backend-setup
terraform destroy
```

## Scaling Considerations

### Vertical Scaling (Upgrade instance)
1. Update `instance_type` in `environments/dev.tfvars`
2. Run `terraform apply`
3. Instance will be recreated with new type

### Horizontal Scaling (Multiple instances)
Not supported in current configuration. Consider:
- AWS Auto Scaling Groups
- Application Load Balancer
- RDS for PostgreSQL
- ElastiCache for Redis

## Security Best Practices

1. **Restrict SSH access** - Update `allowed_ssh_cidr` to your IP only
2. **Use AWS Secrets Manager** - For production secrets
3. **Enable VPC Flow Logs** - For network monitoring
4. **Regular updates** - Keep OS and Docker images updated
5. **Use SSL certificates** - Let's Encrypt for production
6. **Enable AWS GuardDuty** - Threat detection
7. **Regular backups** - Database and configuration

## Support

For issues:
- **Infrastructure**: Check Terraform logs and AWS Console
- **Application**: Check Docker logs and service health
- **Coralogix**: Verify token, domain, and network connectivity
- **OpenAI**: Verify API key and quota

## Additional Resources

- [Coralogix Documentation](https://coralogix.com/docs/)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Docker Compose](https://docs.docker.com/compose/)

