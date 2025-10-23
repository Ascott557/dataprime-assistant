#!/bin/bash
# DataPrime Assistant - VM Deployment Script
# Automated deployment to AWS using Terraform

set -euo pipefail

echo "========================================="
echo "🚀 DataPrime Assistant - VM Deployment"
echo "========================================="
echo ""

# Check prerequisites
echo "🔍 Checking prerequisites..."
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform not found. Install: https://www.terraform.io/downloads"; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI not found. Install: https://aws.amazon.com/cli/"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "❌ jq not found. Install: brew install jq (macOS) or apt-get install jq (Linux)"; exit 1; }

terraform version | head -1
aws --version
echo "✅ Prerequisites OK"
echo ""

# Verify AWS credentials
echo "🔍 Verifying AWS credentials..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS credentials not configured"
    echo "Run: aws configure"
    exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
echo "✅ AWS Account: $AWS_ACCOUNT_ID"
echo "✅ AWS User: $AWS_USER"
echo ""

# Variables
TERRAFORM_DIR="$(dirname "$0")/../infrastructure/terraform"
ENVIRONMENT="${1:-dev}"
VAR_FILE="$TERRAFORM_DIR/environments/$ENVIRONMENT.tfvars"

# Check if environment file exists
if [ ! -f "$VAR_FILE" ]; then
    echo "❌ Environment file not found: $VAR_FILE"
    echo "Available environments:"
    ls -1 "$TERRAFORM_DIR/environments/" | grep ".tfvars$" | sed 's/.tfvars//'
    exit 1
fi

echo "📝 Using environment: $ENVIRONMENT"
echo "📝 Variable file: $VAR_FILE"
echo ""

# Check for required sensitive variables
echo "🔐 Checking required secrets..."
MISSING_VARS=0

if [ -z "${TF_VAR_coralogix_token:-}" ]; then
    echo "⚠️  TF_VAR_coralogix_token not set"
    MISSING_VARS=1
fi

if [ -z "${TF_VAR_openai_api_key:-}" ]; then
    echo "⚠️  TF_VAR_openai_api_key not set"
    MISSING_VARS=1
fi

if [ -z "${TF_VAR_postgres_password:-}" ]; then
    echo "⚠️  TF_VAR_postgres_password not set"
    MISSING_VARS=1
fi

if [ $MISSING_VARS -eq 1 ]; then
    echo ""
    echo "❌ Missing required environment variables!"
    echo ""
    echo "Set them before running this script:"
    echo "  export TF_VAR_coralogix_token=\"your_token\""
    echo "  export TF_VAR_openai_api_key=\"your_key\""
    echo "  export TF_VAR_postgres_password=\"your_password\""
    echo ""
    echo "Or create a terraform.tfvars file (don't commit it!):"
    echo "  cd $TERRAFORM_DIR"
    echo "  cat > terraform.tfvars <<EOF"
    echo "coralogix_token = \"your_token\""
    echo "openai_api_key = \"your_key\""
    echo "postgres_password = \"your_password\""
    echo "EOF"
    exit 1
fi

echo "✅ All required secrets are set"
echo ""

# Cost warning
echo "💰 Cost Estimate:"
echo "   EC2 t3.small: ~\$15/month"
echo "   30GB gp3 storage: ~\$2.40/month"
echo "   Elastic IP: \$0 (when attached)"
echo "   Data transfer: ~\$1/month"
echo "   ────────────────────"
echo "   Total: ~\$18-20/month"
echo ""

# Confirmation
read -p "Proceed with deployment to AWS? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

# Change to Terraform directory
cd "$TERRAFORM_DIR"

# Initialize Terraform
echo ""
echo "🔧 Initializing Terraform..."
terraform init || { echo "❌ Terraform init failed"; exit 1; }

# Validate configuration
echo ""
echo "✅ Validating Terraform configuration..."
terraform validate || { echo "❌ Terraform validation failed"; exit 1; }

# Plan
echo ""
echo "📋 Planning infrastructure changes..."
terraform plan \
    -var-file="$VAR_FILE" \
    -out=tfplan || { echo "❌ Terraform plan failed"; exit 1; }

echo ""
read -p "Apply this plan? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    rm tfplan
    exit 0
fi

# Apply
echo ""
echo "🚀 Applying Terraform plan..."
terraform apply tfplan || { echo "❌ Terraform apply failed"; exit 1; }
rm tfplan

# Get outputs
echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""

INSTANCE_ID=$(terraform output -raw instance_id)
PUBLIC_IP=$(terraform output -raw elastic_ip || terraform output -raw instance_public_ip)
SSH_KEY_NAME=$(terraform output -raw ssh_key_name)

echo "📊 Instance Information:"
echo "   Instance ID: $INSTANCE_ID"
echo "   Public IP: $PUBLIC_IP"
echo ""

# Save SSH key
echo "🔑 Saving SSH private key..."
SSH_KEY_PATH="$HOME/.ssh/dataprime-demo-key.pem"
terraform output -raw ssh_private_key > "$SSH_KEY_PATH"
chmod 600 "$SSH_KEY_PATH"
echo "✅ SSH key saved to: $SSH_KEY_PATH"
echo ""

# Wait for instance to be ready
echo "⏳ Waiting for instance to be ready (this may take 2-3 minutes)..."
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
echo "✅ Instance is running"
echo ""

echo "⏳ Waiting for bootstrap script to complete (~5 minutes)..."
echo "   You can monitor progress by SSH'ing into the instance and running:"
echo "   tail -f /var/log/cloud-init-output.log"
echo ""

# Wait a bit for SSH to be available
sleep 30

# Try to connect and check bootstrap status
echo "🔍 Checking bootstrap status..."
for i in {1..20}; do
    if ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no -o ConnectTimeout=5 "ubuntu@$PUBLIC_IP" "[ -f /var/log/dataprime-bootstrap.log ]" 2>/dev/null; then
        BOOTSTRAP_COMPLETE=$(ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "ubuntu@$PUBLIC_IP" "grep -q 'Bootstrap Complete' /var/log/dataprime-bootstrap.log && echo 'yes' || echo 'no'" 2>/dev/null || echo "no")
        if [ "$BOOTSTRAP_COMPLETE" = "yes" ]; then
            echo "✅ Bootstrap script completed successfully"
            break
        fi
    fi
    echo "   Attempt $i/20: Bootstrap still running..."
    sleep 15
done

echo ""
echo "========================================="
echo "🎉 DataPrime Assistant Deployed!"
echo "========================================="
echo ""
echo "🌐 Access URLs:"
echo "   Frontend:     https://$PUBLIC_IP"
echo "   API Gateway:  http://$PUBLIC_IP:8010/api/health"
echo ""
echo "🔑 SSH Access:"
echo "   ssh -i $SSH_KEY_PATH ubuntu@$PUBLIC_IP"
echo ""
echo "📋 Useful Commands:"
echo "   # Check service status"
echo "   ssh -i $SSH_KEY_PATH ubuntu@$PUBLIC_IP 'cd /opt/dataprime-assistant/deployment/docker && docker compose -f docker-compose.vm.yml ps'"
echo ""
echo "   # View logs"
echo "   ssh -i $SSH_KEY_PATH ubuntu@$PUBLIC_IP 'tail -f /var/log/dataprime-bootstrap.log'"
echo ""
echo "   # Monitor Docker services"
echo "   ssh -i $SSH_KEY_PATH ubuntu@$PUBLIC_IP 'cd /opt/dataprime-assistant/deployment/docker && docker compose -f docker-compose.vm.yml logs -f'"
echo ""
echo "🔍 Coralogix Integration:"
echo "   Infrastructure Explorer: https://coralogix.com/infrastructure"
echo "   APM Traces: https://coralogix.com/apm"
echo "   Logs: https://coralogix.com/logs"
echo ""
echo "⚠️  Note: SSL certificate is self-signed. Accept browser warning."
echo ""
echo "💰 Estimated Cost: ~\$18-20/month"
echo ""
echo "To destroy: ./scripts/teardown.sh"
echo "========================================="

