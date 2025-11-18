#!/bin/bash
#
# Check Docker Build Status
#

SSH_KEY="$HOME/.ssh/dataprime-demo-key.pem"
EC2_HOST="54.235.171.176"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 Docker Build Status Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

ssh -i "$SSH_KEY" ubuntu@$EC2_HOST << 'EOFREMOTE'
echo "1. Build Process Status:"
if ps aux | grep -v grep | grep "docker build" > /dev/null; then
    echo "   🟡 Build is still running..."
    ps aux | grep -v grep | grep "docker build" | awk '{print "   Process: " $2 " (running for " $10 ")"}'
else
    echo "   ✅ No build process running (either completed or not started)"
fi

echo ""
echo "2. Build Log (last 15 lines):"
if [ -f /tmp/docker-build.log ]; then
    tail -15 /tmp/docker-build.log | sed 's/^/   /'
else
    echo "   ⚠️  No build log found"
fi

echo ""
echo "3. Docker Images:"
sudo docker images ecommerce-demo 2>&1 | sed 's/^/   /'

echo ""
echo "4. System Resources:"
echo "   Memory: $(free -h | grep Mem | awk '{print $3 "/" $2 " used"}')"
echo "   Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " used (" $5 ")"}')"

echo ""
EOFREMOTE

EXIT_CODE=$?

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Status check complete"
    echo ""
    echo "Next steps:"
    echo "  • If build complete: ./complete-profiling-setup.sh"
    echo "  • If still running: wait and run ./check-build-status.sh again"
    echo ""
else
    echo "❌ Could not connect to instance"
fi

