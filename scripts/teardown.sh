#!/bin/bash
# DataPrime Assistant - Teardown Script
# Destroys AWS infrastructure created by Terraform

set -euo pipefail

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================="
echo -e "${RED}⚠️  Infrastructure Teardown${NC}"
echo "========================================="
echo ""

# Variables
TERRAFORM_DIR="$(dirname "$0")/../infrastructure/terraform"
ENVIRONMENT="${1:-dev}"
VAR_FILE="$TERRAFORM_DIR/environments/$ENVIRONMENT.tfvars"

# Check if Terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "❌ Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

# Check if environment file exists
if [ ! -f "$VAR_FILE" ]; then
    echo "❌ Environment file not found: $VAR_FILE"
    echo "Available environments:"
    ls -1 "$TERRAFORM_DIR/environments/" | grep ".tfvars$" | sed 's/.tfvars//'
    exit 1
fi

echo "Environment: $ENVIRONMENT"
echo "Variable file: $VAR_FILE"
echo ""

# Warning
echo -e "${YELLOW}⚠️  WARNING: This will destroy all AWS resources!${NC}"
echo ""
echo "This includes:"
echo "  - EC2 instance and all data"
echo "  - Elastic IP"
echo "  - Security groups"
echo "  - IAM roles and policies"
echo "  - SSH key pair"
echo ""

# Double confirmation
read -p "Type 'destroy' to confirm: " CONFIRM
if [ "$CONFIRM" != "destroy" ]; then
    echo "Teardown cancelled."
    exit 0
fi

echo ""
read -p "Are you absolutely sure? This cannot be undone! (yes/NO): " CONFIRM2
if [ "$CONFIRM2" != "yes" ]; then
    echo "Teardown cancelled."
    exit 0
fi

# Change to Terraform directory
cd "$TERRAFORM_DIR"

# Get current outputs before destroying
echo ""
echo "📊 Current Infrastructure:"
terraform output 2>/dev/null || echo "No outputs available"
echo ""

# Destroy
echo "🗑️  Destroying infrastructure..."
echo ""

terraform destroy \
    -var-file="$VAR_FILE" \
    -auto-approve || {
    echo ""
    echo "❌ Terraform destroy failed!"
    echo "You may need to manually clean up some resources."
    exit 1
}

# Clean up local files
echo ""
echo "🧹 Cleaning up local files..."

# Remove SSH key
SSH_KEY_PATH="$HOME/.ssh/dataprime-demo-key.pem"
if [ -f "$SSH_KEY_PATH" ]; then
    rm "$SSH_KEY_PATH"
    echo "✅ Removed SSH key: $SSH_KEY_PATH"
fi

# Remove Terraform state backups (optional)
read -p "Remove local Terraform state backups? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -f terraform.tfstate.backup
    rm -f tfplan
    echo "✅ Removed local state backups"
fi

echo ""
echo "========================================="
echo "✅ Teardown Complete!"
echo "========================================="
echo ""
echo "All AWS resources have been destroyed."
echo ""
echo "Note: The S3 backend and DynamoDB table for Terraform state"
echo "were NOT deleted (they have prevent_destroy enabled)."
echo ""
echo "To remove the backend resources:"
echo "  cd infrastructure/terraform/backend-setup"
echo "  terraform destroy"
echo ""

