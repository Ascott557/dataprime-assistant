# Execute k3s Migration - Final Steps

All the code and infrastructure is ready! Now you just need to execute the deployment.

## ✅ What's Been Prepared

All the following components have been created and are ready to deploy:

1. **Kubernetes Manifests** (`deployment/kubernetes/`):
   - Namespace, ConfigMaps, Secrets
   - 9 Deployment files (all microservices + frontend)
   - Redis StatefulSet with persistent storage
   - OpenTelemetry Collector DaemonSet
   - Service definitions
   - Ingress configuration

2. **Deployment Script** (`scripts/deploy-k3s.sh`):
   - Automated installation of k3s
   - Docker Compose migration
   - Docker image building
   - Kubernetes deployment
   - Coralogix Operator installation
   - Health verification

3. **Health Check Script** (`scripts/health-check-k3s.sh`):
   - Comprehensive health verification
   - Resource usage monitoring
   - Coralogix integration verification

4. **Documentation**:
   - Full deployment guide
   - Troubleshooting tips
   - Rollback procedures

## 🚀 Quick Start - Execute the Migration

### Step 1: Review Pre-Migration Checklist

Before running the migration, verify:

- ✅ Your EC2 instance is running
- ✅ You have SSH access to the instance
- ✅ Terraform outputs are available (`cd infrastructure/terraform && terraform output`)
- ✅ You have your Coralogix token in `infrastructure/terraform/terraform.tfvars`
- ✅ You have your OpenAI API key in `infrastructure/terraform/terraform.tfvars`
- ✅ You're ready for ~5 minutes of downtime during migration

### Step 2: Run the Deployment Script

From your local machine, in the project root directory:

```bash
cd /Users/andrescott/dataprime-assistant

# Execute the deployment
./scripts/deploy-k3s.sh
```

**What will happen:**
1. Script connects to your EC2 instance via SSH
2. Stops Docker Compose services (backs up data first)
3. Installs k3s (~2 minutes)
4. Builds all Docker images (~3-5 minutes)
5. Deploys to Kubernetes (~2 minutes)
6. Installs Coralogix Operator (~1 minute)
7. Verifies deployment

**Total estimated time: 15-20 minutes**

### Step 3: Verify Deployment

After the script completes, run the health check:

```bash
./scripts/health-check-k3s.sh
```

This will verify:
- ✅ All pods are running
- ✅ Services are responding
- ✅ OpenTelemetry Collector is working
- ✅ Coralogix Operator is installed
- ✅ Resources are within limits

### Step 4: Check Coralogix

1. **Access your application** to generate some traces:
   ```bash
   # Get your instance IP
   cd infrastructure/terraform
   INSTANCE_IP=$(terraform output -raw instance_public_ip)
   echo "Frontend: http://$INSTANCE_IP:30020"
   echo "API: http://$INSTANCE_IP:30010"
   ```

2. **Open Coralogix Infrastructure Explorer**:
   - Go to [https://coralogix.com/infrastructure](https://coralogix.com/infrastructure)
   - Look for your k3s node
   - Verify you see host metrics (CPU, memory, disk, network)

3. **Check trace enrichment**:
   - Go to Explore → Traces in Coralogix
   - Open any trace from `dataprime-demo`
   - Click on a span
   - Look for the **HOST** tab (this was missing before!)
   - You should now see:
     - `k8s.pod.name`: Name of the pod handling the request
     - `k8s.namespace.name`: `dataprime-demo`
     - `k8s.node.name`: Your k3s node name
     - `k8s.deployment.name`: The deployment name
     - Host metrics: CPU, memory, etc.

## 🎯 Expected Results

### Before Migration (Docker Compose)
- ❌ No HOST tab data in traces
- ❌ No Kubernetes metadata
- ❌ Limited infrastructure visibility

### After Migration (k3s + Coralogix Operator)
- ✅ HOST tab populated with Kubernetes metadata
- ✅ Pod, namespace, and node information in every trace
- ✅ Host metrics visible in Infrastructure Explorer
- ✅ Full Kubernetes observability

## 🔧 Troubleshooting

### If the deployment script fails:

1. **Check the error message** - the script will show what failed
2. **Check connectivity**: 
   ```bash
   cd infrastructure/terraform
   INSTANCE_IP=$(terraform output -raw instance_public_ip)
   ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$INSTANCE_IP
   ```
3. **Try manual deployment** - Follow the guide in `deployment/kubernetes/K3S-DEPLOYMENT-GUIDE.md`
4. **Run health check** to see what's working:
   ```bash
   ./scripts/health-check-k3s.sh
   ```

### If pods are not starting:

```bash
# SSH to instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$INSTANCE_IP

# Check pod status
kubectl get pods -n dataprime-demo

# Describe failing pod
kubectl describe pod <POD_NAME> -n dataprime-demo

# Check logs
kubectl logs <POD_NAME> -n dataprime-demo
```

### If no metrics appear in Coralogix:

1. **Wait 5 minutes** - metrics can take time to appear
2. **Check OTel Collector logs**:
   ```bash
   kubectl logs -n dataprime-demo -l app=otel-collector --tail=100
   ```
3. **Verify secret**:
   ```bash
   kubectl get secret dataprime-secrets -n dataprime-demo -o yaml
   ```
4. **Check Coralogix Operator**:
   ```bash
   kubectl get pods -n coralogix-operator-system
   kubectl logs -n coralogix-operator-system -l app.kubernetes.io/name=coralogix-operator
   ```

## 🔄 Rollback Plan

If something goes wrong and you need to rollback to Docker Compose:

```bash
# SSH to instance
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@$INSTANCE_IP

# Uninstall k3s
/usr/local/bin/k3s-uninstall.sh

# Restore Docker Compose
cd /opt/dataprime-assistant/deployment/docker
docker compose --env-file .env.vm -f docker-compose.vm.yml up -d
```

## 📊 Monitoring After Migration

### View real-time pod status:
```bash
kubectl get pods -n dataprime-demo -w
```

### Check resource usage:
```bash
kubectl top nodes
kubectl top pods -n dataprime-demo
```

### View logs:
```bash
# API Gateway logs
kubectl logs -n dataprime-demo -l app=api-gateway -f

# OTel Collector logs
kubectl logs -n dataprime-demo -l app=otel-collector -f
```

### Access application:
```bash
# Get instance IP
cd infrastructure/terraform
INSTANCE_IP=$(terraform output -raw instance_public_ip)

# Open in browser
echo "Frontend: http://$INSTANCE_IP:30020"
echo "API Gateway: http://$INSTANCE_IP:30010"
```

## 📚 Additional Resources

- **Full Deployment Guide**: `deployment/kubernetes/K3S-DEPLOYMENT-GUIDE.md`
- **Kubernetes Manifests**: `deployment/kubernetes/`
- **Coralogix Operator**: [GitHub Repository](https://github.com/coralogix/coralogix-operator)
- **k3s Documentation**: [https://docs.k3s.io/](https://docs.k3s.io/)

## ✨ What's Next After Migration?

Once you verify the migration is successful:

1. **Generate traffic** - Use the application to create traces
2. **Explore Infrastructure Explorer** - See your k3s metrics
3. **Check trace metadata** - Verify HOST tab is populated
4. **Set up alerts** - Use Coralogix Operator to create Kubernetes-aware alerts
5. **Optimize resources** - Adjust pod limits based on actual usage
6. **Enable auto-scaling** - Add HorizontalPodAutoscaler for production

---

## 🎉 Ready to Execute?

Everything is prepared and ready to go. Just run:

```bash
cd /Users/andrescott/dataprime-assistant
./scripts/deploy-k3s.sh
```

The script will guide you through the process and show progress at each step!

**Good luck with the migration! 🚀**



