# DataPrime Assistant - Simplified Architecture

## Overview

Simplified infrastructure for **faster shipping** while still demonstrating:
- ✅ Coralogix Infrastructure Monitoring (host metrics)
- ✅ OpenTelemetry distributed tracing across microservices
- ✅ Production-ready patterns
- ✅ Cost-optimized AWS deployment

## Architecture Simplifications

### Database: SQLite Instead of PostgreSQL

**Why SQLite?**
- ✅ **Faster to ship** - no database container, no connection pooling complexity
- ✅ **Less complexity** - built into Python, no additional dependencies
- ✅ **Less memory** - saves ~512MB RAM on t3.small
- ✅ **Persistent storage** - Docker volume mount at `/app/data/`
- ✅ **Perfect for demos** - single-file database, easy to backup/restore

**Trade-offs:**
- ❌ Not for high-concurrency production (but perfect for workshops/demos)
- ✅ Still demonstrates distributed tracing across all microservices
- ✅ Still shows complete observability with Coralogix

### Container Deployment

**Services (11 total containers):**
1. **OpenTelemetry Collector** - Central telemetry hub
   - Host metrics (CPU, memory, disk, network)
   - EC2 resource detection
   - Coralogix exporter
   - Memory: 512MB

2. **Redis** - Distributed cache
   - Session storage
   - Message queue backend
   - Memory: 128MB

3. **8 Python Microservices** - Distributed application
   - API Gateway (8010)
   - Query Service (8011)
   - Validation Service (8012)
   - Queue Service (8013)
   - Processing Service (8014)
   - Storage Service (8015)
   - Queue Worker (8016)
   - External API Service (8017)
   - Memory: 128MB each (~1GB total)

4. **NGINX** - Reverse proxy
   - SSL termination
   - Security headers
   - Rate limiting
   - Memory: 32MB

5. **Frontend** - Web UI (8020)
   - Memory: 128MB

**Total Memory Allocation: ~1.9GB** (fits comfortably on t3.small with 2GB RAM)

## Cost Optimization

**Monthly AWS Costs:**
- EC2 t3.small: $15.18/month
- 30GB gp3 storage: $2.40/month
- Data transfer: ~$1/month
- **Total: ~$18.58/month**

**Savings vs PostgreSQL Architecture:**
- No PostgreSQL container: -512MB RAM, simpler deployment
- No managed RDS: -$15/month
- **Focus on demo excellence, not production scale**

## Data Persistence

**SQLite Database:**
- Location: `/app/data/feedback.db`
- Volume: `sqlite-data` (Docker named volume)
- Backup: Simple file copy
- Migrations: Handled by application on startup

**Redis Cache:**
- Volume: `redis-data` (AOF persistence)
- Stores: Sessions, temporary data, message queue

## Key Features Still Demonstrated

✅ **Infrastructure Monitoring**
- Host metrics (CPU, memory, disk, network) via OTel Collector
- EC2 resource detection and metadata enrichment
- Visible in Coralogix Infrastructure Explorer

✅ **Distributed Tracing**
- Full trace context propagation across 8 microservices
- Parent-child span relationships
- Service dependency mapping
- Latency analysis

✅ **Production Patterns**
- Health checks on all services
- Resource limits
- Graceful shutdown
- Security best practices (non-root containers)
- SSL/TLS termination

✅ **Cost Optimization**
- Minimal AWS resources
- Single AZ deployment
- No NAT Gateway
- Containerized infrastructure

## Deployment

**Local Testing:**
```bash
cd deployment/docker
cp env.vm.example .env.vm
# Edit .env.vm with your credentials
docker compose --env-file .env.vm -f docker-compose.vm.yml up -d
```

**AWS Deployment:**
```bash
# Coming soon with Terraform automation
./scripts/deploy-vm.sh
```

## What We're NOT Showing

❌ High-concurrency database patterns (PostgreSQL connection pooling)
❌ Multi-region deployment
❌ Kubernetes orchestration (Phase 3)
❌ Database replication/HA

## What We ARE Showing

✅ Complete observability with Coralogix (metrics, traces, logs)
✅ Infrastructure monitoring with OTel host metrics
✅ Distributed tracing across microservices
✅ Production-ready containerization
✅ Cost-optimized AWS deployment
✅ Security best practices
✅ Automated health checks

## Development Workflow

1. **Local development** - Docker Compose with SQLite
2. **Testing** - All services with health checks
3. **AWS deployment** - Terraform automation
4. **Monitoring** - Coralogix dashboards

## Future Enhancements (Phase 3+)

- Kubernetes deployment (Helm charts)
- Multi-language services (Go, Node.js)
- Database migration to PostgreSQL for production demos
- Advanced Coralogix features (alerts, dashboards, SLOs)

---

**Last Updated:** November 2, 2024
**Architecture:** Simplified for faster shipping
**Status:** Ready for local testing, AWS deployment in progress






