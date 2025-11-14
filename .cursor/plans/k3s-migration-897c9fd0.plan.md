<!-- 897c9fd0-f036-4c6d-a4cf-89dec72eb93b 4c2934f4-d1eb-4194-8ae1-462ef967a2ea -->
# APM Pod & Host Integration Plan

## Problem

Traces from your application services don't have Kubernetes metadata (pod name, namespace, deployment) because they're bypassing the OpenTelemetry Collector and sending directly to Coralogix. The APM Pod & Host view requires Span Metrics and k8s enrichment.

## Root Causes

1. **`shared_telemetry.py`** (line 70) exports directly to `https://ingress.eu2.coralogix.com:443`
2. **Helm values missing `spanMetrics` preset** - Required for APM Pod & Host correlation
3. **k8sattributes processor never runs** - Traces skip the collector entirely

## Solution Overview

1. Enable Span Metrics preset in Coralogix Helm chart
2. Modify application code to send traces to local OTel Collector
3. Update ConfigMap with collector endpoint
4. Restart applications to apply changes
5. Verify k8s metadata appears in traces

---

## Implementation Steps

### Step 1: Update Helm Values for Full APM

**File**: `deployment/kubernetes/coralogix-infra-values.yaml`

Add `spanMetrics` preset with recommended APM dimensions:

```yaml
presets:
  # Existing presets
  hostmetrics:
    enabled: true
  kubeletstats:
    enabled: true
  kubernetesAttributes:
    enabled: true
  kubernetesMetrics:
    enabled: true
  loadBalancing:
    enabled: true
  
  # ADD THIS - Span Metrics for APM
  spanMetrics:
    enabled: true
    dimensions:
   - name: http.method
   - name: http.status_code
   - name: service.version
   - name: deployment.environment
   - name: k8s.namespace.name
   - name: k8s.deployment.name
   - name: k8s.pod.name
```

**Why**: According to [Coralogix APM docs](https://coralogix.com/docs/user-guides/apm/getting-started/apm-onboarding-tutorial/), Span Metrics generate RED metrics (requests, errors, duration) and enable Pod & Host correlation.

### Step 2: Modify Application Telemetry Export

**File**: `coralogix-dataprime-demo/app/shared_telemetry.py`

**Current (lines 70-77)**: Exports directly to Coralogix

```python
setup_export_to_coralogix(
    service_name="dataprime_assistant",
    application_name=os.getenv('CX_APPLICATION_NAME', 'dataprime-demo'),
    subsystem_name=os.getenv('CX_SUBSYSTEM_NAME', 'ai-assistant'),
    coralogix_token=os.getenv('CX_TOKEN'),
    coralogix_endpoint=cx_endpoint,  # Direct to Coralogix
    capture_content=True
)
```

**Change to**: Export to local OTel Collector

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Get service metadata
service_name = os.getenv('SERVICE_NAME', 'dataprime_assistant')
otel_endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', 'http://coralogix-opentelemetry-collector:4317')

# Create resource with service identity
resource = Resource.create({
    "service.name": service_name,
    "service.version": os.getenv('SERVICE_VERSION', '1.0.0'),
    "deployment.environment": "production",
})

# Setup tracer provider
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# Export to local OTel Collector (which forwards to Coralogix)
otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint, insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

print(f"✅ Exporting traces to OTel Collector: {otel_endpoint}")
```

**Why**: Sending to the OTel Collector allows the `k8sattributes` processor to enrich spans with pod metadata before forwarding to Coralogix.

### Step 3: Update Kubernetes ConfigMap

**File**: `deployment/kubernetes/configmap.yaml`

Add `SERVICE_NAME` for each service and ensure `OTEL_EXPORTER_OTLP_ENDPOINT`:

```yaml
data:
  OTEL_EXPORTER_OTLP_ENDPOINT: "http://coralogix-opentelemetry-collector:4317"
  CX_DOMAIN: "eu2.coralogix.com"
  # ... existing config
```

### Step 4: Update Service Deployments

**Files**: `deployment/kubernetes/deployments/*.yaml`

Add `SERVICE_NAME` environment variable to each deployment:

```yaml
env:
 - name: SERVICE_NAME
    value: "api-gateway"  # Change per service
 - name: OTEL_EXPORTER_OTLP_ENDPOINT
    valueFrom:
      configMapKeyRef:
        name: dataprime-config
        key: OTEL_EXPORTER_OTLP_ENDPOINT
```

Services to update:

- api-gateway.yaml
- query-service.yaml
- validation-service.yaml
- processing-service.yaml
- storage-service.yaml
- queue-service.yaml
- queue-worker-service.yaml
- external-api-service.yaml
- frontend.yaml (if applicable)

### Step 5: Apply Changes

Run deployment script:

```bash
./scripts/deploy-coralogix-infra.sh
```

Then restart application pods:

```bash
kubectl rollout restart deployment -n dataprime-demo
```

### Step 6: Rebuild and Deploy Application Images

Since `shared_telemetry.py` is baked into images, rebuild them:

```bash
ssh ubuntu@<instance-ip>
cd /opt/dataprime-assistant
# Rebuild images with updated telemetry code
docker build -t dataprime-api-gateway -f services/api-gateway/Dockerfile .
# ... repeat for each service
# Import to k3s
docker save dataprime-api-gateway | sudo k3s ctr images import -
# ... repeat for each service
# Restart deployments
kubectl rollout restart deployment -n dataprime-demo
```

### Step 7: Verification

1. Check traces have k8s metadata:

                        - Navigate to trace in Coralogix
                        - Click POD tab
                        - Should show: pod name, namespace, deployment

2. Verify Span Metrics exist:

                        - Go to Metrics Explorer
                        - Search for: `calls_total`, `duration_ms_bucket`
                        - Filter by `service.name`

3. Check APM Pod & Host view:

                        - APM > Service Catalog > Select service
                        - Click "Pod & Host" tab
                        - Should show pod resource usage correlated with service

---

## Expected Results

- Traces will have `k8s.pod.name`, `k8s.namespace.name`, `k8s.deployment.name` tags
- APM Pod & Host view will display pod CPU, memory, network metrics
- Span Metrics will generate RED metrics for all services
- Full correlation between traces, metrics, and infrastructure data

### To-dos

- [ ] Create Kubernetes manifests for all services (namespace, configmap, secret, deployments, services, statefulsets, daemonset)
- [ ] Create deployment script that installs k3s, stops Docker Compose, and deploys to k3s
- [ ] Add Coralogix Operator Helm installation to deployment script
- [ ] Configure k3s Traefik ingress for HTTPS access to frontend and API
- [ ] Execute deployment script and verify all services are running and metrics appear in Coralogix