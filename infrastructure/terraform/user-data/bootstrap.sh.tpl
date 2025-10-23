#!/bin/bash
# DataPrime Assistant - EC2 Bootstrap Script
# This script runs on first boot to set up the application

set -euo pipefail

# Logging setup
exec > >(tee /var/log/dataprime-bootstrap.log)
exec 2>&1

echo "========================================="
echo "🚀 DataPrime Assistant Bootstrap Starting"
echo "========================================="
echo "Timestamp: $(date)"
echo ""

# Error handling function
error_exit() {
    echo "❌ ERROR: $1" >&2
    exit 1
}

# Success logging
log_success() {
    echo "✅ $1"
}

# Update system
echo "📦 Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq || error_exit "Failed to update package list"
apt-get upgrade -y -qq || error_exit "Failed to upgrade packages"
log_success "System updated"

# Install essential packages
echo "📦 Installing essential packages..."
apt-get install -y -qq \
    curl \
    wget \
    git \
    jq \
    htop \
    net-tools \
    ca-certificates \
    gnupg \
    lsb-release \
    unzip \
    openssl || error_exit "Failed to install essential packages"
log_success "Essential packages installed"

# Install Docker
echo "🐳 Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh || error_exit "Failed to download Docker installer"
    sh get-docker.sh || error_exit "Failed to install Docker"
    rm get-docker.sh
    
    # Add ubuntu user to docker group
    usermod -aG docker ubuntu
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    log_success "Docker installed and started"
else
    log_success "Docker already installed"
fi

# Install Docker Compose V2
echo "🐳 Installing Docker Compose..."
apt-get install -y -qq docker-compose-plugin || error_exit "Failed to install Docker Compose"
log_success "Docker Compose installed"

# Verify Docker installation
docker --version || error_exit "Docker verification failed"
docker compose version || error_exit "Docker Compose verification failed"

# Clone/Setup application code
echo "📁 Setting up application..."
APP_DIR="/opt/dataprime-assistant"
if [ -d "$APP_DIR" ]; then
    echo "⚠️  Application directory already exists, backing up..."
    mv "$APP_DIR" "$APP_DIR.backup.$(date +%s)"
fi

mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Clone from GitHub (adjust URL if using private repo)
echo "📥 Cloning application repository..."
# For now, we'll copy the files during deployment
# In production, you'd clone from git:
# git clone https://github.com/your-org/dataprime-assistant.git .

# For demo, we'll create the necessary structure
mkdir -p deployment/docker deployment/otel
mkdir -p coralogix-dataprime-demo/{app,services}

# Create environment file
echo "🔧 Creating environment configuration..."
cat > deployment/docker/.env.vm <<'EOF'
# Coralogix Configuration
CX_TOKEN=${coralogix_token}
CX_DOMAIN=coralogix.com
CX_APPLICATION_NAME=${coralogix_app_name}
CX_SUBSYSTEM_NAME=vm-deployment

# OpenAI Configuration
OPENAI_API_KEY=${openai_api_key}

# Database Configuration
POSTGRES_USER=dataprime
POSTGRES_PASSWORD=${postgres_password}
POSTGRES_DB=dataprime_demo
DATABASE_URL=postgresql://dataprime:${postgres_password}@postgres:5432/dataprime_demo

# Redis Configuration
REDIS_URL=redis://redis:6379/0

# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_EXPORTER_OTLP_PROTOCOL=grpc

# Deployment Configuration
ENVIRONMENT=${environment}
EOF

chmod 600 deployment/docker/.env.vm
log_success "Environment configuration created"

# Generate SSL certificates
echo "🔒 Generating SSL certificates..."
mkdir -p deployment/docker/nginx/ssl
cd deployment/docker/nginx/ssl

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout dataprime.key \
    -out dataprime.crt \
    -subj "/C=US/ST=State/L=City/O=Coralogix/OU=Demo/CN=${project_name}" \
    -addext "subjectAltName=DNS:${project_name},DNS:localhost,IP:127.0.0.1" \
    2>/dev/null || error_exit "Failed to generate SSL certificates"

chmod 600 dataprime.key
chmod 644 dataprime.crt

cd "$APP_DIR"
log_success "SSL certificates generated"

# Note: In a real deployment, you would now have all your application files
# from the Git clone. For this demo, they need to be included in the AMI
# or deployed via another mechanism (S3, CodeDeploy, etc.)

# Configure UFW firewall
echo "🔥 Configuring firewall..."
ufw --force enable
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 8010/tcp  # API Gateway (optional, for testing)
ufw status
log_success "Firewall configured"

# Start Docker Compose services
echo "🚀 Starting application services..."
cd "$APP_DIR/deployment/docker"

# Pull images first to avoid timeouts
docker compose -f docker-compose.vm.yml pull || echo "⚠️  Some images need to be built locally"

# Start services
docker compose -f docker-compose.vm.yml up -d || error_exit "Failed to start Docker services"

log_success "Application services started"

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Health check
echo "🔍 Performing health checks..."
HEALTH_CHECK_PASSED=0

for i in {1..10}; do
    if curl -f http://localhost:8010/api/health > /dev/null 2>&1; then
        log_success "API Gateway is healthy"
        HEALTH_CHECK_PASSED=1
        break
    fi
    echo "   Attempt $i/10 failed, waiting..."
    sleep 10
done

if [ $HEALTH_CHECK_PASSED -eq 0 ]; then
    echo "⚠️  Health check did not pass, but continuing..."
    echo "   Check logs: docker compose -f $APP_DIR/deployment/docker/docker-compose.vm.yml logs"
fi

# Setup log rotation
echo "📝 Configuring log rotation..."
cat > /etc/logrotate.d/dataprime <<'LOGROTATE'
/var/log/dataprime-bootstrap.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
LOGROTATE
log_success "Log rotation configured"

# Create health check cron job
echo "⏰ Setting up health check cron job..."
cat > /usr/local/bin/dataprime-health-check.sh <<'HEALTHCHECK'
#!/bin/bash
# Health check script for DataPrime Assistant

cd /opt/dataprime-assistant/deployment/docker

# Check if all containers are running
if ! docker compose -f docker-compose.vm.yml ps | grep -q "Up"; then
    echo "$(date): Some containers are down, restarting..." >> /var/log/dataprime-health.log
    docker compose -f docker-compose.vm.yml up -d
fi

# Check API Gateway health
if ! curl -f http://localhost:8010/api/health > /dev/null 2>&1; then
    echo "$(date): API Gateway unhealthy, restarting services..." >> /var/log/dataprime-health.log
    docker compose -f docker-compose.vm.yml restart api-gateway
fi
HEALTHCHECK

chmod +x /usr/local/bin/dataprime-health-check.sh

# Add to crontab (run every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/dataprime-health-check.sh") | crontab -
log_success "Health check cron job configured"

# Create README for operators
cat > /opt/dataprime-assistant/README-DEPLOYMENT.md <<'README'
# DataPrime Assistant - Deployment Information

## Application Location
- Application Directory: /opt/dataprime-assistant
- Docker Compose File: /opt/dataprime-assistant/deployment/docker/docker-compose.vm.yml
- Environment Config: /opt/dataprime-assistant/deployment/docker/.env.vm

## Useful Commands

### Check Service Status
```bash
cd /opt/dataprime-assistant/deployment/docker
docker compose -f docker-compose.vm.yml ps
```

### View Logs
```bash
docker compose -f docker-compose.vm.yml logs -f
docker compose -f docker-compose.vm.yml logs -f api-gateway
```

### Restart Services
```bash
docker compose -f docker-compose.vm.yml restart
docker compose -f docker-compose.vm.yml restart api-gateway
```

### Stop/Start All Services
```bash
docker compose -f docker-compose.vm.yml stop
docker compose -f docker-compose.vm.yml start
```

### Health Checks
```bash
curl http://localhost:8010/api/health
curl http://localhost:13133  # OTel Collector health
```

## Logs
- Bootstrap Log: /var/log/dataprime-bootstrap.log
- Health Check Log: /var/log/dataprime-health.log
- Docker Logs: Use docker compose logs command above

## Troubleshooting
1. Check if Docker is running: `systemctl status docker`
2. Check container status: `docker ps -a`
3. Check logs: `docker compose logs`
4. Restart services: `docker compose restart`
5. Check firewall: `ufw status`
README

log_success "Operator README created"

# Final output
echo ""
echo "========================================="
echo "✅ Bootstrap Complete!"
echo "========================================="
echo "Application: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "API Gateway: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8010/api/health"
echo ""
echo "📁 Application Directory: /opt/dataprime-assistant"
echo "📋 Logs: /var/log/dataprime-bootstrap.log"
echo "📖 README: /opt/dataprime-assistant/README-DEPLOYMENT.md"
echo ""
echo "🔍 Check status:"
echo "   cd /opt/dataprime-assistant/deployment/docker"
echo "   docker compose -f docker-compose.vm.yml ps"
echo ""
echo "🎉 DataPrime Assistant is ready!"
echo "========================================="

