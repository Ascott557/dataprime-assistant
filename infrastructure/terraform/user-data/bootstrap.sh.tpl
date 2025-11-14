#!/bin/bash
###############################################################################
# DataPrime Demo - EC2 Bootstrap Script
# 
# This script:
# 1. Updates system and installs dependencies
# 2. Installs Docker and Docker Compose
# 3. Clones application code
# 4. Creates environment configuration
# 5. Starts all services via Docker Compose
# 6. Configures systemd service for auto-restart
# 7. Sets up firewall rules
# 8. Configures health check monitoring
#
# All output is logged to /var/log/dataprime-bootstrap.log
###############################################################################

set -euo pipefail

# Logging setup
LOGFILE="/var/log/dataprime-bootstrap.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "======================================================================"
echo "DataPrime Demo Bootstrap - Started at $(date)"
echo "======================================================================"

# Environment variables from Terraform
export CX_TOKEN="${coralogix_token}"
export CX_DOMAIN="${coralogix_domain}"
export CX_APPLICATION_NAME="${coralogix_app_name}"
export CX_SUBSYSTEM_NAME="${coralogix_subsystem}"
export OPENAI_API_KEY="${openai_api_key}"
export REDIS_URL="${redis_url}"
export OTEL_EXPORTER_OTLP_ENDPOINT="${otel_endpoint}"
export PROJECT_NAME="${project_name}"
export ENVIRONMENT="${environment}"

# Application directory
APP_DIR="/opt/dataprime-assistant"

###############################################################################
# 1. System Update and Dependencies
###############################################################################
echo "[1/9] Updating system packages..."
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"

echo "[1/9] Installing essential packages..."
apt-get install -y \
  curl \
  wget \
  git \
  unzip \
  jq \
  ca-certificates \
  gnupg \
  lsb-release \
  apt-transport-https \
  software-properties-common

###############################################################################
# 2. Install Docker and Docker Compose
###############################################################################
echo "[2/9] Installing Docker..."

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Verify Docker installation
docker --version
docker compose version

echo "[2/9] Docker installed successfully!"

###############################################################################
# 3. Clone Application Code
###############################################################################
echo "[3/9] Setting up application code..."

# Create application directory
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# Clone repository (or use pre-uploaded code)
if [ ! -d "$APP_DIR/coralogix-dataprime-demo" ]; then
  echo "Cloning repository from ${repository_url}..."
  git clone "${repository_url}" .
else
  echo "Application code already exists, updating..."
  git pull
fi

###############################################################################
# 4. Create Environment Configuration
###############################################################################
echo "[4/9] Creating environment configuration..."

cat > "$APP_DIR/deployment/docker/.env.vm" <<EOF
# Coralogix Configuration
CX_TOKEN=$${CX_TOKEN}
CX_DOMAIN=$${CX_DOMAIN}
CX_APPLICATION_NAME=$${CX_APPLICATION_NAME}
CX_SUBSYSTEM_NAME=$${CX_SUBSYSTEM_NAME}

# OpenAI Configuration
OPENAI_API_KEY=$${OPENAI_API_KEY}

# Redis Configuration
REDIS_URL=$${REDIS_URL}

# OpenTelemetry Configuration
OTEL_EXPORTER_OTLP_ENDPOINT=$${OTEL_EXPORTER_OTLP_ENDPOINT}

# Environment
ENVIRONMENT=$${ENVIRONMENT}
PROJECT_NAME=$${PROJECT_NAME}
EOF

chmod 600 "$APP_DIR/deployment/docker/.env.vm"

echo "[4/9] Environment configuration created!"

###############################################################################
# 5. Generate SSL Certificates
###############################################################################
echo "[5/9] Generating self-signed SSL certificates..."

mkdir -p "$APP_DIR/deployment/docker/nginx/ssl"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$APP_DIR/deployment/docker/nginx/ssl/dataprime.key" \
  -out "$APP_DIR/deployment/docker/nginx/ssl/dataprime.crt" \
  -subj "/C=US/ST=State/L=City/O=Coralogix/CN=dataprime-demo" \
  2>&1

chmod 600 "$APP_DIR/deployment/docker/nginx/ssl/dataprime.key"
chmod 644 "$APP_DIR/deployment/docker/nginx/ssl/dataprime.crt"

echo "[5/9] SSL certificates generated!"

###############################################################################
# 6. Start Docker Compose Services
###############################################################################
echo "[6/9] Starting Docker Compose services..."

cd "$APP_DIR/deployment/docker"

# Pull images first
docker compose --env-file .env.vm -f docker-compose.vm.yml pull

# Build custom images
docker compose --env-file .env.vm -f docker-compose.vm.yml build --no-cache

# Start services
docker compose --env-file .env.vm -f docker-compose.vm.yml up -d

echo "[6/9] Waiting for services to initialize (60 seconds)..."
sleep 60

# Check service status
docker compose --env-file .env.vm -f docker-compose.vm.yml ps

echo "[6/9] Docker Compose services started!"

###############################################################################
# 7. Configure Systemd Service for Auto-Restart
###############################################################################
echo "[7/9] Configuring systemd service..."

cat > /etc/systemd/system/dataprime-demo.service <<EOF
[Unit]
Description=DataPrime Demo Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR/deployment/docker
ExecStart=/usr/bin/docker compose --env-file .env.vm -f docker-compose.vm.yml up -d
ExecStop=/usr/bin/docker compose --env-file .env.vm -f docker-compose.vm.yml down
ExecReload=/usr/bin/docker compose --env-file .env.vm -f docker-compose.vm.yml restart

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable dataprime-demo.service

echo "[7/9] Systemd service configured!"

###############################################################################
# 8. Configure Firewall (UFW)
###############################################################################
echo "[8/9] Configuring firewall..."

# Install UFW if not already installed
apt-get install -y ufw

# Configure UFW rules
ufw --force reset
ufw default deny incoming
ufw default allow outgoing

# Allow SSH, HTTP, HTTPS
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw allow 8010/tcp comment 'API Gateway'

# Enable UFW
ufw --force enable

echo "[8/9] Firewall configured!"

###############################################################################
# 9. Set Up Health Check Monitoring
###############################################################################
echo "[9/9] Setting up health check monitoring..."

cat > /usr/local/bin/dataprime-health-check.sh <<'EOF'
#!/bin/bash
# Health check script for DataPrime Demo

LOGFILE="/var/log/dataprime-health-check.log"
APP_DIR="/opt/dataprime-assistant"

echo "=== Health Check - $(date) ===" >> "$LOGFILE"

cd "$APP_DIR/deployment/docker"

# Check if all containers are running
UNHEALTHY=$(docker compose --env-file .env.vm -f docker-compose.vm.yml ps | grep -v "Up" | grep -v "NAME" | wc -l)

if [ "$UNHEALTHY" -gt 0 ]; then
  echo "WARNING: $UNHEALTHY unhealthy containers detected!" >> "$LOGFILE"
  docker compose --env-file .env.vm -f docker-compose.vm.yml ps >> "$LOGFILE"
  
  # Attempt restart
  echo "Attempting to restart services..." >> "$LOGFILE"
  docker compose --env-file .env.vm -f docker-compose.vm.yml restart
else
  echo "All containers healthy" >> "$LOGFILE"
fi
EOF

chmod +x /usr/local/bin/dataprime-health-check.sh

# Add cron job (every 5 minutes)
cat > /etc/cron.d/dataprime-health-check <<EOF
*/5 * * * * root /usr/local/bin/dataprime-health-check.sh
EOF

echo "[9/9] Health check monitoring configured!"

###############################################################################
# Finalization
###############################################################################
echo "======================================================================"
echo "Bootstrap Complete!"
echo "======================================================================"
echo "Timestamp: $(date)"
echo "Application Directory: $APP_DIR"
echo "Log File: $LOGFILE"
echo ""
echo "Services Status:"
docker compose --env-file "$APP_DIR/deployment/docker/.env.vm" -f "$APP_DIR/deployment/docker/docker-compose.vm.yml" ps
echo ""
echo "Access your application at:"
echo "  https://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)"
echo "  or http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8010 (API)"
echo ""
echo "To check logs:"
echo "  tail -f $LOGFILE"
echo "  cd $APP_DIR/deployment/docker && docker compose --env-file .env.vm -f docker-compose.vm.yml logs -f"
echo "======================================================================"

exit 0
