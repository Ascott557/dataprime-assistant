#!/usr/bin/env bash
#
# Upload Source Maps to Coralogix RUM using CLI
#
# This script uploads JavaScript source maps to Coralogix for error tracking
# with original source code line numbers in the RUM dashboard.
#
# Requirements:
#   - npm installed
#   - @coralogix/rum-cli package (will be installed if not present)
#   - Source map key: cxtp_JG9Z2JVZOnUutZFCBBg9HAwrbcYaeX
#
# Usage:
#   ./upload-source-maps.sh [folder_path]
#   
#   Example:
#   ./upload-source-maps.sh ./dist

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration from .coralogix/rum.config.json
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUM_CONFIG_FILE="${PROJECT_ROOT}/.coralogix/rum.config.json"

# RUM Configuration (from Coralogix)
SOURCE_MAP_KEY="cxtp_JG9Z2JVZOnUutZFCBBg9HAwrbcYaeX"
APPLICATION="ecom_reccomendation"
VERSION="1.0.0"
CORALOGIX_DOMAIN="EU2"

# Get folder path from argument or use default
FOLDER_PATH="${1:-./dist}"

echo -e "${BLUE}📋 Coralogix RUM Source Map Upload${NC}"
echo "  Application: $APPLICATION"
echo "  Version: $VERSION"
echo "  Domain: $CORALOGIX_DOMAIN"
echo "  Folder: $FOLDER_PATH"
echo ""

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ Error: npm is not installed${NC}"
    echo "Please install Node.js and npm first:"
    echo "  https://nodejs.org/"
    exit 1
fi

# Check if Coralogix RUM CLI is installed globally
if ! command -v coralogix-rum-cli &> /dev/null; then
    echo -e "${YELLOW}📦 Installing @coralogix/rum-cli globally...${NC}"
    npm install -g @coralogix/rum-cli
    echo -e "${GREEN}✅ RUM CLI installed${NC}"
    echo ""
fi

# Check if source folder exists
if [ ! -d "$FOLDER_PATH" ]; then
    echo -e "${YELLOW}⚠️  Warning: Folder '$FOLDER_PATH' not found${NC}"
    echo ""
    echo -e "${BLUE}📝 Note: This is a Flask application with inline JavaScript.${NC}"
    echo "   Traditional JavaScript source maps are not applicable."
    echo ""
    echo "   RUM will still work to track:"
    echo "   - User sessions and page views"
    echo "   - User actions and interactions"
    echo "   - Network requests and performance"
    echo "   - JavaScript errors (with inline script context)"
    echo ""
    echo "   If you build JavaScript bundles in the future:"
    echo "   1. Create a build folder (e.g., ./dist)"
    echo "   2. Generate source maps during build"
    echo "   3. Run this script: ./upload-source-maps.sh ./dist"
    echo ""
    exit 0
fi

# Upload source maps using Coralogix RUM CLI
echo -e "${BLUE}📤 Uploading source maps to Coralogix...${NC}"
echo ""

# Execute the exact command format from Coralogix docs
coralogix-rum-cli upload-source-maps \
  -k "$SOURCE_MAP_KEY" \
  -a "$APPLICATION" \
  -e "$CORALOGIX_DOMAIN" \
  -v "$VERSION" \
  -f "$FOLDER_PATH"

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Source maps uploaded successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Deploy the frontend with version: $VERSION"
    echo "  2. Open the app in a browser: http://<your-ip>:30020"
    echo "  3. Check Coralogix RUM dashboard: https://coralogix.com/rum"
    echo "  4. Errors will now show with original source code line numbers"
else
    echo -e "${RED}❌ Source map upload failed (exit code: $EXIT_CODE)${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Verify the source map key is correct"
    echo "  2. Check that $FOLDER_PATH contains .js.map files"
    echo "  3. Ensure the version matches your SDK initialization"
    echo "  4. See: https://coralogix.com/docs/user-guides/rum/cli/"
    exit $EXIT_CODE
fi

