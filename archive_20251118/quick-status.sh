#!/bin/bash
# Quick status check - exits immediately
ssh -i ~/.ssh/dataprime-demo-key.pem -o ConnectTimeout=5 -o ServerAliveInterval=2 ubuntu@54.235.171.176 'sudo kubectl get pods -n dataprime-demo 2>/dev/null | grep -E "product-service|api-gateway|frontend" | grep -v "demo-frontend" | head -5'

