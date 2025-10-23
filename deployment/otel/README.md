# OpenTelemetry Collector Configuration

This directory contains the OpenTelemetry Collector configuration for the DataPrime Assistant VM deployment.

## Files

- `otel-collector-vm.yaml` - Main collector configuration optimized for t3.small instances

## Features

### Receivers
- **Host Metrics**: Collects CPU, memory, disk, network, filesystem, and load metrics
- **OTLP**: Receives traces, metrics, and logs from application services

### Processors
- **Memory Limiter**: Prevents OOM by limiting memory usage to 512MB
- **Batch Processor**: Optimizes API calls by batching telemetry data
- **Resource Detection**: Auto-detects AWS EC2 metadata for enrichment
- **Resource Attributes**: Adds deployment environment and namespace

### Exporters
- **Coralogix**: Exports all telemetry to Coralogix (Company ID: 4015437)
- **Prometheus**: Local metrics endpoint for debugging (port 8889)
- **Logging**: Debug exporter (disabled by default)

## Configuration

The collector requires these environment variables:

```bash
CX_TOKEN=<your_coralogix_token>
CX_DOMAIN=coralogix.com
CX_APPLICATION_NAME=dataprime-demo
CX_SUBSYSTEM_NAME=infrastructure
ENVIRONMENT=production
```

## Docker Deployment

The collector must be deployed with specific volume mounts:

```yaml
volumes:
  - /:/hostfs:ro  # Required for host metrics
  - /var/run/docker.sock:/var/run/docker.sock:ro  # Optional for container metrics
```

## Ports

- `4317` - OTLP gRPC receiver
- `4318` - OTLP HTTP receiver
- `8888` - Collector's own metrics
- `8889` - Prometheus exporter
- `13133` - Health check endpoint
- `55679` - zPages debugging

## Resource Requirements

- **Memory**: 512MB limit (optimized for t3.small)
- **CPU**: 0.5 cores
- **Collection Interval**: 30s (adjust to 60s for production)

## Monitoring

### Health Check
```bash
curl http://localhost:13133
```

### Prometheus Metrics
```bash
curl http://localhost:8889/metrics
```

### zPages
```bash
# View pipelines and spans
curl http://localhost:55679/debug/tracez
curl http://localhost:55679/debug/pipelinez
```

## Coralogix Integration

The collector exports telemetry to Coralogix Infrastructure Monitoring, which provides:

- **Host Metrics**: CPU, memory, disk, network utilization
- **EC2 Metadata**: Automatic enrichment with instance ID, type, AZ, tags
- **Service Correlation**: Links infrastructure metrics to application traces
- **Cost Optimization**: TCO routing based on data priority

## Troubleshooting

### Collector Not Starting
```bash
# Check logs
docker logs otel-collector

# Verify configuration
docker exec otel-collector cat /etc/otel-collector-config.yaml
```

### No Metrics in Coralogix
1. Verify `CX_TOKEN` is correct
2. Check `CX_DOMAIN` matches your region
3. Ensure host filesystem is mounted at `/hostfs`
4. Check collector logs for export errors

### High Memory Usage
1. Reduce `collection_interval` to 60s
2. Disable `process` scraper if not needed
3. Reduce `batch.send_batch_size` to 256

## Performance Tuning

### For Demo/Development (Low Latency)
```yaml
hostmetrics:
  collection_interval: 15s  # Faster updates

batch:
  timeout: 5s  # Quicker exports
```

### For Production (Cost Optimized)
```yaml
hostmetrics:
  collection_interval: 60s  # Reduce metric volume

batch:
  send_batch_size: 1024  # Fewer API calls
  timeout: 30s
```

## References

- [OpenTelemetry Collector Documentation](https://opentelemetry.io/docs/collector/)
- [Coralogix OpenTelemetry Integration](https://coralogix.com/docs/opentelemetry/)
- [Host Metrics Receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/hostmetricsreceiver)
- [Coralogix Infrastructure Monitoring](https://coralogix.com/docs/infrastructure-monitoring/)

