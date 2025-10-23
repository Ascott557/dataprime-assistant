<!-- 1ff38481-4c83-47b7-8d4b-902f556bfc24 fa75f845-dff3-4c11-b056-be8485c97780 -->
# Phase 1-2: Infrastructure Monitoring + VM Deployment

## Overview

Add Coralogix Infrastructure Monitoring (host metrics) and create production-ready, cost-optimized VM deployment on AWS using Terraform automation. This showcases OpenTelemetry best practices and Coralogix's complete observability platform while minimizing costs.

## Cost Optimization Strategy

- **t3.small** instance (2 vCPU, 2GB RAM) - ~$15/month
- Single AZ deployment (no cross-AZ data transfer costs)
- Containerized PostgreSQL/Redis (avoid managed service costs)
- 30GB gp3 storage (cheaper than gp2)
- No NAT Gateway ($32/month savings)
- Self-signed SSL (no certificate costs)
- **Total estimated cost: ~$18/month**

## Implementation Tasks

### Phase 1: OpenTelemetry Collector & Local Infrastructure

#### 1.1 OpenTelemetry Collector Configuration

**File:** `deployment/otel/otel-collector-vm.yaml`

Complete OTel Collector config with:

- Host metrics receiver (CPU, memory, disk, network, filesystem, load)
- EC2 resource detection processor
- Memory limiter (256MB for t3.small)
- Batch processor (512 batch size for cost efficiency)
- Coralogix exporter with domain `coralogix.com` and company ID `4015437`
- Prometheus exporter on port 8889 for debugging
- Three pipelines: traces, metrics, logs

Key configurations:

```yaml
receivers:
  hostmetrics:
    collection_interval: 30s  # 30s for demo responsiveness (change to 60s for production)
    root_path: /hostfs
    scrapers:
      cpu: {}
      disk: {}
      filesystem:
        exclude_fs_types: [overlay, tmpfs, devtmpfs]
      load: {}
      memory: {}
      network: {}

processors:
  resourcedetection/ec2:
    detectors: [env, ec2, system]
    timeout: 5s
  memory_limiter:
    limit_mib: 512  # CRITICAL: 512MB for t3.small (2GB RAM)
    spike_limit_mib: 128
    check_interval: 1s

exporters:
  coralogix:
    # Coralogix-specific exporter (correct format)
    domain: "coralogix.com"
    private_key: "${CX_TOKEN}"
    application_name: "dataprime-demo"
    subsystem_name: "infrastructure"
    timeout: 30s
  
  prometheus:
    endpoint: "0.0.0.0:8889"  # Local debugging
```

#### 1.2 Docker Compose for VM Deployment

**File:** `deployment/docker/docker-compose.vm.yml`

Services:

- OpenTelemetry Collector (with host filesystem mount)
- PostgreSQL 15 Alpine (minimal image)
- Redis 7 Alpine
- All 8 Python microservices
- NGINX Alpine
- Resource limits on all services

Critical mounts:

```yaml
otel-collector:
  volumes:
 - /:/hostfs:ro
 - /var/run/docker.sock:/var/run/docker.sock:ro
```

Resource limits example:

```yaml
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 256M
```

#### 1.3 Environment Configuration

**File:** `deployment/docker/.env.vm.example`

Variables:

```bash
# Coralogix (Company ID: 4015437)
CX_TOKEN=your_token_here
CX_DOMAIN=coralogix.com
CX_APPLICATION_NAME=dataprime-demo
CX_SUBSYSTEM_NAME=vm-deployment

# OpenAI
OPENAI_API_KEY=your_key_here

# Database
POSTGRES_USER=dataprime
POSTGRES_PASSWORD=generate_secure_password
POSTGRES_DB=dataprime_demo
DATABASE_URL=postgresql://dataprime:password@postgres:5432/dataprime_demo

# Redis
REDIS_URL=redis://redis:6379/0

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

### Phase 2: Terraform Infrastructure (Cost-Optimized)

#### 2.1 Terraform State Backend

**File:** `infrastructure/terraform/backend-setup/main.tf`

Separate directory for one-time backend setup:

- S3 bucket with versioning and encryption
- DynamoDB table for state locking
- Outputs bucket name for main Terraform config

#### 2.2 Main Terraform Configuration

**File:** `infrastructure/terraform/main.tf`

Provider configuration and modules:

```hcl
terraform {
  required_version = ">= 1.5"
  backend "s3" {
    # Populated after backend setup
  }
}

module "vpc" {
  source = "./modules/vpc"
  # Single public subnet, no NAT gateway
}

module "security" {
  source = "./modules/security"
  coralogix_company_id = "4015437"
}

module "ec2" {
  source = "./modules/ec2"
  instance_type = "t3.small"  # Cost optimized
}
```

#### 2.3 VPC Module (Minimal)

**File:** `infrastructure/terraform/modules/vpc/main.tf`

Minimal VPC setup:

- VPC with 10.0.0.0/16 CIDR
- Single public subnet in us-east-1a
- Internet Gateway
- Public route table
- No NAT Gateway (cost savings)

#### 2.4 Security Module

**File:** `infrastructure/terraform/modules/security/main.tf`

Security group with minimal ports:

- SSH (22) from your IP only
- HTTP (80) and HTTPS (443) from anywhere
- Application port (8010) from anywhere
- OTel ports (4317, 4318) from VPC only

IAM role for Coralogix Infrastructure Explorer:

```hcl
# IAM role with trust relationship to Coralogix account
# Company ID: 4015437
# Read-only EC2 permissions for metadata enrichment
```

SSH key pair creation via Terraform:

```hcl
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "deployer" {
  key_name   = "${var.project_name}-key"
  public_key = tls_private_key.ssh_key.public_key_openssh
}
```

#### 2.5 EC2 Module (Cost-Optimized)

**File:** `infrastructure/terraform/modules/ec2/main.tf`

t3.small instance configuration:

- Latest Ubuntu 22.04 LTS AMI (auto-lookup)
- 30GB gp3 root volume
- Detailed monitoring disabled (cost savings)
- User data script for bootstrapping
- Elastic IP for stable access
- Instance profile with Coralogix IAM role

#### 2.6 Bootstrap Script

**File:** `infrastructure/terraform/user-data/bootstrap.sh.tpl`

Complete bootstrap script:

1. System update and upgrade
2. Install Docker and Docker Compose V2
3. Install OpenTelemetry Collector as systemd service
4. Clone/copy DataPrime Assistant code
5. Create .env file from Terraform variables
6. Generate self-signed SSL certificate
7. Configure NGINX
8. Start Docker Compose services
9. Configure UFW firewall
10. Setup health check cron job

Key sections:

```bash
#!/bin/bash
set -euo pipefail

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose V2
apt-get install -y docker-compose-plugin

# Configure application
cd /opt/dataprime-assistant
cat > deployment/docker/.env.vm <<EOF
CX_TOKEN=${coralogix_token}
CX_DOMAIN=coralogix.com
...
EOF

# Start services
docker compose -f deployment/docker/docker-compose.vm.yml up -d
```

#### 2.7 Variables and Outputs

**File:** `infrastructure/terraform/variables.tf`

Variables:

- `aws_region` (default: us-east-1)
- `project_name` (default: dataprime-demo)
- `environment` (default: dev)
- `instance_type` (default: t3.small)
- `root_volume_size` (default: 30)
- `coralogix_token` (sensitive)
- `coralogix_company_id` (default: 4015437)
- `openai_api_key` (sensitive)
- `postgres_password` (sensitive)
- `allowed_ssh_cidr` (required)

**File:** `infrastructure/terraform/outputs.tf`

Outputs:

- Instance ID, public IP, private IP
- SSH private key (sensitive)
- Application URL
- Security group ID
- SSH command

### Phase 2.5: Service Updates

#### 2.8 Update Services for PostgreSQL

**Files:** `coralogix-dataprime-demo/services/*.py`

Update each service:

- Replace SQLite with PostgreSQL using `psycopg2-binary`
- Add `DATABASE_URL` environment variable support
- Implement connection pooling with `psycopg2.pool`
- Add retry logic with exponential backoff
- Update health checks to verify DB connection

Example connection:

```python
import psycopg2.pool
from urllib.parse import urlparse

db_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=os.getenv('DATABASE_URL')
)
```

#### 2.9 Create Dockerfiles for Services

**Files:** `coralogix-dataprime-demo/services/*/Dockerfile`

Multi-stage Dockerfile template:

```dockerfile
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
ENV PATH=/root/.local/bin:$PATH
EXPOSE 8010
HEALTHCHECK CMD curl -f http://localhost:8010/health || exit 1
CMD ["python", "api_gateway.py"]
```

#### 2.10 Update Requirements

**File:** `coralogix-dataprime-demo/requirements.txt`

Add:

- `psycopg2-binary==2.9.9` (PostgreSQL driver)
- `redis==5.0.1` (Redis client)
- `sqlalchemy==2.0.23` (optional ORM)

### Phase 2.6: NGINX & SSL

#### 2.11 NGINX Configuration

**File:** `deployment/docker/nginx/nginx.conf`

Main NGINX config with:

- Worker processes auto
- SSL configuration
- Gzip compression
- Security headers
- Rate limiting

**File:** `deployment/docker/nginx/conf.d/dataprime.conf`

Server block with:

- Listen 80 and 443
- Reverse proxy to frontend (8020)
- Reverse proxy to API gateway (8010)
- SSL certificate paths
- Security headers (X-Frame-Options, CSP, etc.)

#### 2.12 SSL Certificate Generation

**File:** `deployment/docker/nginx/ssl/generate-certs.sh`

Script to generate self-signed certificate:

```bash
#!/bin/bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/nginx/ssl/dataprime.key \
  -out /etc/nginx/ssl/dataprime.crt \
  -subj "/C=US/ST=State/L=City/O=Coralogix/CN=dataprime-demo"
```

### Phase 2.7: Automation Scripts

#### 2.13 Backend Setup Script

**File:** `scripts/setup-terraform-backend.sh`

One-time script to:

- Check AWS credentials
- Create S3 bucket with versioning
- Create DynamoDB table
- Output backend config for main Terraform

#### 2.14 VM Deployment Script

**File:** `scripts/deploy-vm.sh`

Main deployment script:

- Check prerequisites (Terraform, AWS CLI, jq)
- Prompt for required secrets
- Initialize Terraform
- Plan and apply
- Save SSH key to ~/.ssh/
- Wait for instance ready
- Run health checks
- Display access information

#### 2.15 Health Check Script

**File:** `scripts/health-check.sh`

Comprehensive checks:

- All 8 service endpoints
- OTel Collector (port 13133)
- PostgreSQL (via psql)
- Redis (via redis-cli)
- NGINX status
- Colored output (green/red)

#### 2.16 Teardown Script

**File:** `scripts/teardown.sh`

Cleanup script:

- Confirmation prompt
- Terraform destroy
- Remove SSH key
- Clean local state files

### Documentation

#### 2.17 Deployment Guide

**File:** `docs/DEPLOYMENT-VM.md`

Complete guide:

- Prerequisites
- Cost breakdown
- Step-by-step deployment
- Accessing the application
- Verifying Coralogix integration
- Troubleshooting
- Scaling considerations

#### 2.18 Architecture Documentation

**File:** `docs/ARCHITECTURE.md`

Updated architecture doc:

- Infrastructure diagram
- Network topology
- Data flow (metrics, traces, logs)
- Coralogix integration points
- Cost optimization decisions

## Implementation Order

1. **Local Development First** (Phase 1.1-1.3)

                                                - OpenTelemetry Collector config
                                                - Docker Compose with PostgreSQL/Redis
                                                - Test locally before AWS deployment

2. **Service Updates** (Phase 2.8-2.10)

                                                - Migrate SQLite → PostgreSQL
                                                - Create Dockerfiles
                                                - Test with local Docker Compose

3. **Terraform Infrastructure** (Phase 2.1-2.7)

                                                - Backend setup
                                                - VPC, Security, EC2 modules
                                                - Bootstrap script

4. **NGINX & Automation** (Phase 2.11-2.16)

                                                - NGINX configuration
                                                - Deployment scripts
                                                - Health checks

5. **Testing & Documentation** (Phase 2.17-2.18)

                                                - Deploy to AWS
                                                - Verify all services
                                                - Complete documentation

## Success Criteria

✅ **Phase 1 Complete:**

- OTel Collector collecting host metrics
- Metrics visible in Coralogix Infrastructure Explorer
- Docker Compose runs all services locally
- PostgreSQL replaces SQLite
- All health checks pass

✅ **Phase 2 Complete:**

- Single command deploys to AWS: `./scripts/deploy-vm.sh`
- Application accessible via public IP
- SSL working (self-signed)
- Infrastructure metrics in Coralogix
- Total AWS cost under $20/month
- Complete documentation

## Key Files to Create

**Phase 1:** 3 files

- `deployment/otel/otel-collector-vm.yaml`
- `deployment/docker/docker-compose.vm.yml`
- `deployment/docker/.env.vm.example`

**Phase 2:** 25+ files

- Terraform modules (VPC, Security, EC2)
- Backend setup
- Bootstrap script
- Service Dockerfiles (8 files)
- NGINX configs
- Automation scripts (4 files)
- Documentation (2 files)

## Cost Breakdown

- **EC2 t3.small:** $15.18/month
- **30GB gp3 storage:** $2.40/month
- **Elastic IP (attached):** $0/month
- **Data transfer:** ~$1/month
- **Total:** ~$18.58/month

**Cost savings vs original plan:**

- t3.xlarge → t3.small: -$106/month
- No RDS: -$15/month
- No ElastiCache: -$13/month
- No NAT Gateway: -$32/month
- **Total savings: ~$166/month (90% reduction)**

### To-dos

- [ ] Create OpenTelemetry Collector configuration with host metrics, EC2 detection, and Coralogix exporter
- [ ] Create production Docker Compose with OTel Collector, PostgreSQL, Redis, NGINX, and all services
- [ ] Create environment configuration template with all required variables
- [ ] Update all 8 services to use PostgreSQL instead of SQLite with connection pooling
- [ ] Create optimized Dockerfiles for all 8 microservices with multi-stage builds
- [ ] Create Terraform backend setup for S3 state and DynamoDB locking
- [ ] Create Terraform modules for VPC, Security (with SSH key), and EC2 (t3.small)
- [ ] Create EC2 bootstrap script to install Docker, OTel Collector, and start services
- [ ] Create NGINX reverse proxy configuration with SSL and security headers
- [ ] Create script to generate self-signed SSL certificates
- [ ] Create deployment, health check, and teardown automation scripts
- [ ] Test complete stack locally with Docker Compose before AWS deployment
- [ ] Deploy to AWS using automation script and verify all services
- [ ] Verify infrastructure metrics and traces appear in Coralogix with EC2 metadata
- [ ] Create deployment guide and update architecture documentation