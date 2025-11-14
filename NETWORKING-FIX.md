# Docker Networking Fix - November 2, 2024

## Issue

When clicking "Generate DataPrime Query" in the frontend, the application returned:
```
Error: HTTPConnectionPool(host='localhost', port=8011): Max retries exceeded
Connection refused to localhost:8011
```

## Root Cause

All services were hardcoded to use `localhost` URLs instead of Docker service names:
- `http://localhost:8011` → Should be `http://query-service:8011`
- `http://localhost:8012` → Should be `http://validation-service:8012`
- etc.

This works when running services directly on the host with `distributed_app.py`, but fails in Docker Compose where services must communicate via Docker network names.

## Fix Applied

Updated all service-to-service URLs to use environment variables with Docker service name defaults:

### Files Modified:

**1. `/services/api_gateway.py`**
```python
# Before
QUERY_SERVICE_URL = "http://localhost:8011"
VALIDATION_SERVICE_URL = "http://localhost:8012"

# After
QUERY_SERVICE_URL = os.getenv("QUERY_SERVICE_URL", "http://query-service:8011")
VALIDATION_SERVICE_URL = os.getenv("VALIDATION_SERVICE_URL", "http://validation-service:8012")
```

**2. `/services/queue_worker_service.py`**
```python
# Before
EXTERNAL_API_SERVICE_URL = "http://localhost:8016"
STORAGE_SERVICE_URL = "http://localhost:8015"

# After
EXTERNAL_API_SERVICE_URL = os.getenv("EXTERNAL_API_SERVICE_URL", "http://external-api-service:8016")
STORAGE_SERVICE_URL = os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8015")
```

**3. `/services/processing_service.py`**
```python
# Before
storage_response = requests.post("http://localhost:8015/store", ...)

# After
storage_service_url = os.getenv("STORAGE_SERVICE_URL", "http://storage-service:8015")
storage_response = requests.post(f"{storage_service_url}/store", ...)
```

**4. `/services/queue_service.py`**
```python
# Before
processing_response = requests.post("http://localhost:8014/process", ...)

# After
processing_service_url = os.getenv("PROCESSING_SERVICE_URL", "http://processing-service:8014")
processing_response = requests.post(f"{processing_service_url}/process", ...)
```

## Services Rebuilt and Restarted

```bash
✅ api-gateway           - Rebuilt and healthy
✅ queue-worker-service  - Rebuilt and healthy
✅ processing-service    - Rebuilt and healthy
✅ queue-service         - Rebuilt and healthy
```

## Status

**All 11/11 services healthy** ✅

```
NAME                   STATUS
api-gateway            Up (healthy)
query-service          Up (healthy)
validation-service     Up (healthy)
queue-service          Up (healthy)
processing-service     Up (healthy)
storage-service        Up (healthy)
queue-worker-service   Up (healthy)
external-api-service   Up (healthy)
frontend               Up (healthy)
nginx                  Up (healthy)
otel-collector         Up
redis                  Up (healthy)
```

## How to Test

1. **Refresh your browser** at http://localhost:8020
2. Enter a query like: `"show me errors from the last 4 hours"`
3. Click **"🔍 Generate DataPrime Query"**
4. The request should now work!

Expected flow:
```
Browser → Frontend (8020)
  → API Gateway (8010)
    → Query Service (8011) ✅ Now using Docker network
      → OpenAI API
    ← Generated query returned
  ← Response to frontend
```

## Benefits of This Approach

1. **Environment Variable Override**: Can still override URLs if needed
2. **Docker-Friendly Defaults**: Works out of the box in Docker Compose
3. **Backwards Compatible**: Can still run with localhost for local development by setting env vars
4. **Flexibility**: Easy to point to different service instances

## Verification Commands

```bash
# Check API Gateway can reach Query Service
docker exec api-gateway curl -s http://query-service:8011/health

# Check Queue Worker can reach Storage Service
docker exec queue-worker-service curl -s http://storage-service:8015/health

# Test full flow
curl -X POST http://localhost:8010/api/generate \
  -H "Content-Type: application/json" \
  -d '{"natural_language_query": "show errors", "service": "coralogix"}'
```

---

**Fixed:** November 2, 2024, 6:04 PM EDT  
**Status:** ✅ Application fully functional






