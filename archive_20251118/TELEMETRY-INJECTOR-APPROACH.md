# Telemetry Injector Approach - Scene 9 Database APM

## Why This Approach?

**Problem**: Real service orchestration is unreliable for demos because:
- ❌ Services might not be deployed correctly
- ❌ Network issues between services
- ❌ Timing dependencies
- ❌ Hard to debug when it doesn't work

**Solution**: Directly inject pre-recorded telemetry
- ✅ No service dependencies
- ✅ Guaranteed consistent results
- ✅ Fast execution (no real queries)
- ✅ Perfect for demos

## What It Does

The telemetry injector creates 43 database query spans following OpenTelemetry semantic conventions and sends them directly to Coralogix.

### Span Details

Each span includes all required attributes:
```python
span.set_attribute("db.system", "postgresql")
span.set_attribute("db.name", "productcatalog")
span.set_attribute("db.operation", "SELECT")
span.set_attribute("db.sql.table", "products")
span.set_attribute("net.peer.name", "postgres")          # REQUIRED
span.set_attribute("net.peer.port", 5432)                # REQUIRED
span.set_attribute("db.query.duration_ms", 2800)         # P95/P99
span.set_attribute("db.connection_pool.active", 95)      # Pool exhaustion
span.set_attribute("db.connection_pool.utilization_percent", 95)
```

### Distribution

- **product-service**: 15 spans (2600-3200ms latency)
- **order-service**: 15 spans (2700-3100ms latency)
- **inventory-service**: 13 spans (2650-3000ms latency)
- **Total**: 43 spans
- **Failure rate**: ~8% (some spans have error status)

## Files

### 1. `simple_demo_injector.py` (Fast Version)
- Creates 43 spans instantly
- No delays
- Perfect for quick testing

### 2. `demo_telemetry_injector.py` (Realistic Version)
- Creates 43 spans with simulated delays
- More realistic timing
- Better for presentations

### 3. API Gateway Integration
New endpoint: `/api/demo/inject-telemetry`
- Calls the injector
- Returns immediately
- Spans appear in Coralogix within 10-15 seconds

### 4. Frontend Integration
Button: "🔥 Simulate Database Issues (Scene 9)"
- Calls `/api/demo/inject-telemetry`
- Shows success message
- Guides user to check Coralogix

## Deployment

### Quick Deploy

```bash
cd /Users/andrescott/dataprime-assistant-1
./DEPLOY-TELEMETRY-INJECTOR.sh
```

This will:
1. Copy files to AWS
2. Rebuild Docker image
3. Restart api-gateway and frontend pods
4. Wait for rollout completion

### Manual Deploy

```bash
# 1. Copy files
scp -i ~/.ssh/dataprime-demo-key.pem \
    coralogix-dataprime-demo/services/api_gateway.py \
    coralogix-dataprime-demo/services/simple_demo_injector.py \
    coralogix-dataprime-demo/app/ecommerce_frontend.py \
    ubuntu@54.235.171.176:/tmp/

# 2. SSH to AWS
ssh -i ~/.ssh/dataprime-demo-key.pem ubuntu@54.235.171.176

# 3. Move files
sudo mv /tmp/*.py /opt/dataprime-assistant/coralogix-dataprime-demo/services/
sudo mv /tmp/ecommerce_frontend.py /opt/dataprime-assistant/coralogix-dataprime-demo/app/

# 4. Rebuild
cd /opt/dataprime-assistant/coralogix-dataprime-demo
sudo docker build -t ecommerce-demo:latest .
sudo docker save ecommerce-demo:latest | sudo k3s ctr images import -

# 5. Tag
sudo k3s ctr images tag docker.io/library/ecommerce-demo:latest docker.io/library/dataprime-api-gateway:latest

# 6. Restart
sudo kubectl rollout restart deployment api-gateway -n dataprime-demo
sudo kubectl rollout restart deployment frontend -n dataprime-demo
```

## Testing

### Step 1: Click the Button

1. Navigate to: `https://54.235.171.176:30443/`
2. Click: **"🔥 Simulate Database Issues (Scene 9)"**
3. Confirm the dialog
4. You'll see: "✅ Database telemetry injected!"

### Step 2: Check Coralogix (wait 10-15 seconds)

Navigate to: **APM → Database Monitoring → productcatalog**

Set time range: **Last 5 minutes**

### Step 3: Verify Results

**Calling Services dropdown** should show:
- ✅ product-service
- ✅ order-service
- ✅ inventory-service

**Metrics** should show:
- Query Duration P95: ~2800ms (spike from baseline)
- Query Duration P99: ~3200ms
- Active Queries: 43 (spike)
- Failure Rate: ~8%

**Service Map** should show:
- 3 services connected to PostgreSQL
- All connections showing high latency (red)

## Direct Testing (Without Frontend)

You can also test directly from the command line:

### Option 1: Via kubectl port-forward

```bash
kubectl port-forward -n dataprime-demo svc/api-gateway 8010:8010
curl -X POST http://localhost:8010/api/demo/inject-telemetry
```

### Option 2: Via kubectl exec

```bash
POD=$(kubectl get pods -n dataprime-demo -l app=api-gateway -o jsonpath='{.items[0].metadata.name}')
kubectl exec -it -n dataprime-demo $POD -- python3 /app/services/simple_demo_injector.py
```

### Option 3: Run locally (if you have the env vars)

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="your-collector:4317"
cd coralogix-dataprime-demo/services
python3 simple_demo_injector.py
```

## Troubleshooting

### Spans not appearing in Coralogix

1. **Check OTel Collector is running**:
   ```bash
   kubectl get pods -n dataprime-demo | grep otel-collector
   kubectl logs -n dataprime-demo -l app=otel-collector --tail=50
   ```

2. **Verify endpoint configuration**:
   ```bash
   kubectl get configmap dataprime-config -n dataprime-demo -o yaml | grep OTEL_EXPORTER
   ```

3. **Check API Gateway logs**:
   ```bash
   kubectl logs -n dataprime-demo -l app=api-gateway --tail=100 | grep -i "inject\|telemetry"
   ```

### Button not triggering

1. **Check frontend logs**:
   ```bash
   kubectl logs -n dataprime-demo -l app=frontend --tail=50
   ```

2. **Verify API Gateway service**:
   ```bash
   kubectl get svc -n dataprime-demo api-gateway
   ```

3. **Test endpoint directly**:
   ```bash
   kubectl exec -it -n dataprime-demo $(kubectl get pods -n dataprime-demo -l app=frontend -o jsonpath='{.items[0].metadata.name}') -- curl -X POST http://api-gateway:8010/api/demo/inject-telemetry
   ```

## Advantages vs Real Orchestration

| Aspect | Real Orchestration | Telemetry Injection |
|--------|-------------------|---------------------|
| Reliability | ❌ Depends on all services | ✅ No dependencies |
| Speed | ❌ 10-30 seconds | ✅ Instant |
| Consistency | ❌ Variable results | ✅ Same every time |
| Debugging | ❌ Hard to troubleshoot | ✅ Easy to debug |
| Demo Safety | ❌ Can fail during demo | ✅ Always works |
| Setup | ❌ All services must work | ✅ Just API Gateway |

## Next Steps

1. Deploy using `./DEPLOY-TELEMETRY-INJECTOR.sh`
2. Test the frontend button
3. Verify in Coralogix that 3 services appear
4. Use for your demo presentation

---

**Status**: ✅ READY TO DEPLOY
**Recommended**: Use this approach for reliable demos

