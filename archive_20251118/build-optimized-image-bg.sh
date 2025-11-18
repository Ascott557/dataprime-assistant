#!/bin/bash
#
# Build Optimized Docker Image in Background
# This script starts the build and returns immediately, so your terminal won't hang
#

set -e

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  🚀 Starting Optimized Image Build (Background Mode)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📋 What this does:"
echo "  1. Starts Docker build in background on EC2"
echo "  2. Returns immediately (won't hang)"
echo "  3. Logs output to /tmp/docker-build.log"
echo ""
echo "⏱️  Build time: ~2-3 minutes"
echo "📦 Image size: ~300-500MB (vs 8GB before)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Start build in background
ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << 'EOFREMOTE' &
cd /opt/dataprime-assistant/coralogix-dataprime-demo

echo "Starting Docker build at $(date)..." > /tmp/docker-build.log
echo "" >> /tmp/docker-build.log

sudo docker build -f docker/Dockerfile -t ecommerce-demo:latest . >> /tmp/docker-build.log 2>&1

if [ $? -eq 0 ]; then
    echo "" >> /tmp/docker-build.log
    echo "✅ Build completed successfully at $(date)" >> /tmp/docker-build.log
    sudo docker images ecommerce-demo:latest >> /tmp/docker-build.log 2>&1
else
    echo "" >> /tmp/docker-build.log
    echo "❌ Build failed at $(date)" >> /tmp/docker-build.log
fi
EOFREMOTE

SSH_PID=$!

echo "✅ Build started (PID: $SSH_PID)"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 Monitoring Commands (Run in new terminal):"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "# Check build progress:"
echo "ssh -i $SSH_KEY ubuntu@$EC2_HOST 'tail -20 /tmp/docker-build.log'"
echo ""
echo "# Watch build in real-time:"
echo "ssh -i $SSH_KEY ubuntu@$EC2_HOST 'tail -f /tmp/docker-build.log'"
echo ""
echo "# Check if build is still running:"
echo "ssh -i $SSH_KEY ubuntu@$EC2_HOST 'ps aux | grep docker'"
echo ""
echo "# Check final image size:"
echo "ssh -i $SSH_KEY ubuntu@$EC2_HOST 'sudo docker images ecommerce-demo'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Next: Wait 2-3 minutes, then run:"
echo "   ./check-build-status.sh"
echo ""

