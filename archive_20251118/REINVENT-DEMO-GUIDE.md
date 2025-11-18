# re:Invent 2025 Demo Guide - E-commerce AI with Coralogix

**Application:** E-commerce Product Recommendation System  
**Tech Stack:** AI (OpenAI GPT-4) → Tool Calls → PostgreSQL  
**Observability:** Coralogix with Manual OpenTelemetry Instrumentation

---

## Demo Flow

### 1. Normal Operation (Happy Path)

**Show:** Fast, responsive AI recommendations with PostgreSQL

```bash
# Make AI recommendation request
curl -k -X POST https://<EC2_IP>:30444/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_user",
    "user_context": "wireless headphones under $100"
  }' | jq .

# Expected output:
# - trace_id: <UUID>
# - recommendations: 3 products (JBL, Anker, Sennheiser)
# - success: true
# - tool_call_success: true
```

**In Coralogix:**
1. Go to APM → Traces
2. Search for the trace ID
3. Show the complete trace hierarchy:
   - `ai_recommendations` (15-20s total)
   - `chat gpt-4-turbo` (OpenAI call #1, ~1-2s)
   - `product_service.get_products` (~10-50ms)
     - Connection pool metrics: 1% utilization
     - `postgres.query.select_products` (~8-12ms)
       - DB statement, duration, row count
   - `chat gpt-4-turbo` (OpenAI call #2, ~10-13s)

**Key Points:**
- Fast database query (~10ms)
- Low connection pool utilization (1/100 connections)
- Complete visibility from AI → Database
- Manual spans with rich attributes

---

### 2. Slow Database Queries

**Show:** Impact of slow database on user experience

```bash
# Enable slow query simulation (2900ms delay)
curl -X POST http://<EC2_IP>:30014/demo/enable-slow-queries \
  -H "Content-Type: application/json" \
  -d '{"delay_ms": 2900}'

# Expected response:
# {
#   "status": "slow_queries_enabled",
#   "delay_ms": 2900
# }

# Make another AI recommendation request
curl -k -X POST https://<EC2_IP>:30444/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_slow_db",
    "user_context": "noise canceling headphones"
  }' | jq .
```

**In Coralogix:**
1. Search for the new trace ID
2. Show the database span now takes 2900ms
3. Point out the attributes:
   - `db.simulation.slow_query_enabled` = true
   - `db.simulation.delay_ms` = 2900
   - `db.query.duration_ms` = ~2900

**Key Points:**
- Manual instrumentation captures simulation flags
- Easy to identify performance issues
- Database becomes bottleneck (3s vs 10ms)
- Total request time increases significantly

---

### 3. Connection Pool Exhaustion

**Show:** How connection pool limits affect availability

```bash
# Simulate pool exhaustion (hold 95/100 connections)
curl -X POST http://<EC2_IP>:30014/demo/simulate-pool-exhaustion

# Expected response:
# {
#   "status": "pool_exhausted",
#   "held_connections": 95,
#   "pool_stats": {
#     "active_connections": 95,
#     "max_connections": 100,
#     "utilization_percent": 95.0,
#     "available_connections": 5
#   }
# }

# Check health endpoint
curl http://<EC2_IP>:30014/health | jq .connection_pool

# Make AI recommendation request (should still work with 5 available connections)
curl -k -X POST https://<EC2_IP>:30444/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_pool_exhaustion",
    "user_context": "budget wireless earbuds"
  }' | jq .
```

**In Coralogix:**
1. Search for the trace
2. Show connection pool metrics in the span:
   - `db.connection_pool.active` = 96 (including this request)
   - `db.connection_pool.max` = 100
   - `db.connection_pool.utilization_percent` = 96%

**Key Points:**
- Connection pool at 95% utilization
- Request still succeeds (5 connections available)
- Manual instrumentation tracks pool metrics
- Shows importance of proper connection pool sizing

---

### 4. Reset Demo

**Show:** Clearing all simulations

```bash
# Reset all demo simulations
curl -X POST http://<EC2_IP>:30014/demo/reset

# Expected response:
# {
#   "status": "demo_reset",
#   "released_connections": 95,
#   "pool_stats": {
#     "active_connections": 0,
#     "max_connections": 100,
#     "utilization_percent": 0.0,
#     "available_connections": 100
#   }
# }

# Verify back to normal
curl http://<EC2_IP>:30014/health | jq

# Make final request to show fast performance
curl -k -X POST https://<EC2_IP>:30444/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo_reset_test",
    "user_context": "premium wireless headphones"
  }' | jq .trace_id
```

**In Coralogix:**
- Show trace with normal performance restored
- Database query back to ~10ms
- Pool utilization back to 1%

---

## Key Demo Points

### Manual OpenTelemetry Instrumentation

**Why Manual > Auto:**
1. **Explicit Control:** Every span created exactly where needed
2. **Rich Attributes:** Full control over metadata captured
3. **Reliable:** No hidden auto-instrumentation failures
4. **Proven Pattern:** Copied from working implementation

**Code Example:**
```python
# Manual span with explicit attributes
with tracer.start_as_current_span("postgres.query.select_products") as db_span:
    db_span.set_attribute("db.system", "postgresql")
    db_span.set_attribute("db.operation", "SELECT")
    db_span.set_attribute("db.table", "products")
    db_span.set_attribute("db.statement", "SELECT * FROM products...")
    db_span.set_attribute("db.query.category", category)
    db_span.set_attribute("db.query.price_range", f"{price_min}-{price_max}")
    
    # Execute query
    cursor.execute("...", (category, price_min, price_max))
    results = cursor.fetchall()
    
    db_span.set_attribute("db.query.duration_ms", duration)
    db_span.set_attribute("db.rows_returned", len(results))
```

### Connection Pool Monitoring

**Tracked in Every Span:**
- `db.connection_pool.active` - Current active connections
- `db.connection_pool.max` - Maximum pool size (100)
- `db.connection_pool.utilization_percent` - % utilization
- `db.connection_pool.available_connections` - Available connections

### AI Center Integration

**Complete AI Workflow Visibility:**
- User query → OpenAI
- Tool calls → Product Service
- Database queries → PostgreSQL
- Final AI response → User

**All connected in a single distributed trace!**

---

## Cheat Sheet

### Quick Commands

```bash
# Health check
curl http://<EC2_IP>:30014/health | jq

# Enable slow queries
curl -X POST http://<EC2_IP>:30014/demo/enable-slow-queries \
  -H "Content-Type: application/json" \
  -d '{"delay_ms": 2900}'

# Simulate pool exhaustion
curl -X POST http://<EC2_IP>:30014/demo/simulate-pool-exhaustion

# Reset demo
curl -X POST http://<EC2_IP>:30014/demo/reset

# Make AI recommendation
curl -k -X POST https://<EC2_IP>:30444/api/recommendations \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","user_context":"wireless headphones under $100"}' | jq
```

### Coralogix URLs

- **APM Traces:** https://eu2.coralogix.com/apm/traces
- **AI Center:** https://eu2.coralogix.com/ai-center
- **Infrastructure Explorer:** https://eu2.coralogix.com/infrastructure

---

## Demo Script (5-10 minutes)

### Introduction (1 min)
"Today I'm showing you an e-commerce AI recommendation system built with OpenAI GPT-4 and PostgreSQL. We're using Coralogix for complete observability from AI to database using manual OpenTelemetry instrumentation."

### Demo 1: Normal Operation (2 min)
1. Make API call for wireless headphones under $100
2. Show 3 product recommendations returned
3. Open Coralogix trace
4. Walk through the complete flow: AI → Tool Call → PostgreSQL
5. Point out database query took only 10ms, pool at 1% utilization

### Demo 2: Slow Database (2 min)
1. Enable slow query simulation (2900ms)
2. Make another API call
3. Show trace with 2900ms database delay
4. Point out the simulation attributes in the span
5. Explain impact on user experience

### Demo 3: Pool Exhaustion (2 min)
1. Simulate pool exhaustion (95/100 connections)
2. Check health endpoint showing 95% utilization
3. Make API call (still works with 5 available)
4. Show trace with pool metrics
5. Explain connection pool sizing importance

### Demo 4: Reset (1 min)
1. Reset all simulations
2. Make final call showing normal performance
3. Show trace back to 10ms database time

### Wrap-up (1 min)
"This demonstrates how manual OpenTelemetry instrumentation gives us complete visibility into our AI-powered application. We can track everything from the AI model to the database, with rich context at every step. This is critical for production AI applications where reliability and performance matter."

---

## Troubleshooting

### If trace doesn't appear in Coralogix:
1. Wait 2-3 minutes for data to arrive
2. Check OTel Collector logs: `kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector`
3. Check product service logs: `kubectl logs -n dataprime-demo -l app=product-service`

### If PostgreSQL isn't ready:
1. Check pod status: `kubectl get pods -n dataprime-demo -l app=postgres`
2. Check logs: `kubectl logs -n dataprime-demo -l app=postgres`
3. Restart if needed: `kubectl delete pod -n dataprime-demo -l app=postgres`

### If demo endpoints don't work:
1. Check product service health: `curl http://<EC2_IP>:30014/health`
2. Reset demo: `curl -X POST http://<EC2_IP>:30014/demo/reset`
3. Check pod logs for errors

---

## Success Metrics

**What to show:**
- ✅ Complete distributed trace visibility
- ✅ Sub-10ms database queries (normal mode)
- ✅ Connection pool metrics in every span
- ✅ AI Center showing complete workflow
- ✅ Manual instrumentation with rich attributes
- ✅ Demo scenarios working (slow queries, pool exhaustion)

**Key message:**
Manual OpenTelemetry instrumentation provides reliable, detailed observability for AI-powered applications from model to database.

---

## Questions & Answers

**Q: Why manual instrumentation instead of auto-instrumentation?**  
A: Manual instrumentation gives us explicit control, rich attributes, and reliability. Auto-instrumentation can fail silently or miss important context.

**Q: How do you capture connection pool metrics?**  
A: We query the pool state before each database operation and add it as span attributes: `pool_stats = get_pool_stats(); span.set_attribute("db.connection_pool.utilization_percent", pool_stats["utilization_percent"])`

**Q: How does the AI decide which products to recommend?**  
A: OpenAI GPT-4 uses a tool call to query our PostgreSQL database with category and price filters, then generates personalized recommendations based on the results.

**Q: What happens if the database is slow?**  
A: The trace shows exactly where the delay is (database span), how long it took, and what query was running. This makes debugging production issues much faster.

---

## re:Invent 2025 - Ready! 🚀

**Key Takeaways:**
1. Manual OpenTelemetry instrumentation for production AI apps
2. Complete visibility from AI model to database
3. Rich span attributes enable fast debugging
4. Connection pool monitoring prevents availability issues
5. Demo-ready with simulation endpoints

