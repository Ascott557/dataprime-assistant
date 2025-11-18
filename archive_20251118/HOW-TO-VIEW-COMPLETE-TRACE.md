# How to View Complete Distributed Trace with Database Spans

**Important:** The AI Center view you're currently using filters/groups spans for AI-specific analysis. To see the **complete distributed trace** with HTTP and database spans, you need to use the **APM Traces view**.

---

## ✅ Test Trace Generated

```
Trace ID: a69e7fe3ecccd6fc6a1bee4c2c6e50ac
Status: SUCCESS
Products returned: 9
Duration: ~13-15s
```

---

## 🔍 How to View the Complete Trace

### Option 1: APM → Traces (RECOMMENDED for full span tree)

1. **Navigate to APM:**
   ```
   Coralogix → APM → Traces (NOT AI Center)
   ```

2. **Search for the trace:**
   ```
   Trace ID: a69e7fe3ecccd6fc6a1bee4c2c6e50ac
   OR
   Service: recommendation-ai
   Time: Last 15 minutes
   ```

3. **Click on the trace** to open full span tree

4. **Expected Spans (in APM view):**
   ```
   ai_recommendations (root, ~15s)
   │
   ├─ chat gpt-4-turbo (LLM #1, ~1.5s)
   │  └─ [OpenAI tool call spans from llm-tracekit]
   │
   ├─ http.get_product_data (HTTP call, ~10-40ms) ← YOUR MANUAL SPAN
   │  │  [http.method: GET]
   │  │  [http.url: http://product-service:8014/products]
   │  │  [tool.function: get_product_data]
   │  │
   │  └─ get_products_from_db (Product Service span, ~30ms)
   │     │  [db.system: postgresql]
   │     │  [db.connection_pool stats]
   │     │
   │     └─ db.query.select_products (Database query, ~5-15ms) ← YOUR MANUAL SPAN
   │        [db.system: postgresql]
   │        [db.operation: SELECT]
   │        [db.table: products]
   │        [db.statement: SELECT ... FROM products ...]
   │        [db.query.duration_ms: 6.78]
   │        [db.rows_returned: 9]
   │
   ├─ ai_final_response (child span, ~1s)
   │
   └─ chat gpt-4-turbo (LLM #2, ~11s)
      └─ [Final AI response]
   ```

### Option 2: Explore → Logs & Traces

1. **Navigate:**
   ```
   Coralogix → Explore → Logs & Traces
   ```

2. **Query:**
   ```dataprime
   source traces
   | filter $m.trace_id == 'a69e7fe3ecccd6fc6a1bee4c2c6e50ac'
   ```

3. **View results:** Shows all spans in the trace

### Option 3: AI Center (Current view - Limited)

**Note:** AI Center **filters spans** to show only AI-relevant operations:
- ✅ Shows: LLM calls, AI operations
- ❌ Hides: Infrastructure spans (HTTP, database, etc.)

This is why you don't see `http.get_product_data` and `db.query.select_products` in your current screenshot.

---

## 🎯 Key Differences Between Views

| View | Purpose | What You See |
|------|---------|--------------|
| **AI Center** | AI model analysis | LLM calls, prompts, completions, tool calls |
| **APM Traces** | Full distributed tracing | ALL spans: HTTP, DB, AI, infrastructure |
| **Service Map** | Service dependencies | Service-to-service calls, latencies |

---

## 🧪 Verification Steps

### 1. Check APM Traces for HTTP Span

```
APM → Traces → Filter by trace ID
Look for span name: "http.get_product_data"

Expected attributes:
- http.method = GET
- http.url = http://product-service:8014/products
- http.status_code = 200
- tool.function = get_product_data
- tool.parameters.category = Wireless Headphones
```

### 2. Check for Database Span

```
In the same trace, look for span name: "db.query.select_products"

Expected attributes:
- db.system = postgresql
- db.operation = SELECT
- db.table = products
- db.statement = SELECT id, name, ... FROM products ...
- db.query.duration_ms = 6.78
- db.rows_returned = 9
```

### 3. Verify Span Nesting

```
Click on "http.get_product_data" span
→ Should show "get_products_from_db" as child
  → Should show "db.query.select_products" as child

This confirms proper parent-child relationship
```

---

## 🔍 If Spans Are Still Missing

### Check OTel Collector Logs:

```bash
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl logs -n dataprime-demo -l app.kubernetes.io/name=opentelemetry-collector --tail=100"
```

Look for:
- ✅ Spans being received from `recommendation-ai`
- ✅ Spans being received from `product-service`
- ❌ Any export errors

### Check Service Logs:

```bash
# Recommendation AI logs
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl logs -n dataprime-demo -l app=recommendation-ai | grep 'Calling Product Service'"

# Product Service logs  
ssh -i ~/.ssh/ecommerce-demo-key.pem ubuntu@54.235.171.176 \
  "sudo kubectl logs -n dataprime-demo -l app=product-service | tail -50"
```

---

## 📊 What Your Screenshots Show

### Screenshot 1 (Old App - `old_app_files`)
```
✅ Shows: api-gateway → query-service → storage-service → database
✅ Full distributed trace visible
✅ Database INSERT operations visible
✅ Multiple services in the chain
```

**Note:** This was the **APM Traces view**, not AI Center

### Screenshot 2 (Current App - E-commerce)
```
⚠️ Shows: Only AI-related spans
⚠️ Filtered view (AI Center)
⚠️ HTTP/DB spans hidden by default
❌ Need to switch to APM view
```

**Solution:** View the same trace in **APM → Traces**

---

## 🎯 Expected vs Actual

### What You're Seeing (AI Center):
```
ai_recommendations
├─ chat gpt-4-turbo (1.57s)
├─ GET (4.44ms) ← Automatic span from RequestsInstrumentor
├─ ai_final_response (1.13s)
└─ chat gpt-4-turbo (11.31s)
```

### What You Should See (APM Traces):
```
ai_recommendations
├─ chat gpt-4-turbo (1.57s)
├─ http.get_product_data (40ms) ← YOUR MANUAL SPAN
│  └─ get_products_from_db (30ms)
│     └─ db.query.select_products (6.78ms) ← YOUR MANUAL DATABASE SPAN
├─ ai_final_response (1.13s)
└─ chat gpt-4-turbo (11.31s)
```

---

## ✅ Action Items

1. **Open APM → Traces** (not AI Center)
2. **Search for trace:** `a69e7fe3ecccd6fc6a1bee4c2c6e50ac`
3. **Expand the span tree** to see all children
4. **Look for:**
   - `http.get_product_data` span with HTTP attributes
   - `db.query.select_products` span with database attributes
5. **Verify nesting:** HTTP → Product Service → Database

---

## 🚨 Common Gotchas

### 1. AI Center Filtering
- **Problem:** AI Center hides infrastructure spans
- **Solution:** Use APM Traces for full visibility

### 2. Span Name Confusion
- **Problem:** Automatic instrumentation creates spans with generic names (GET, POST)
- **Solution:** Manual spans have descriptive names (http.get_product_data)

### 3. Service-Specific Views
- **Problem:** Filtering by service shows only that service's spans
- **Solution:** View full trace to see cross-service calls

### 4. Collapsed Spans
- **Problem:** Child spans might be collapsed by default
- **Solution:** Click the expand arrow (▶) next to parent spans

---

## 📚 Documentation References

**Coralogix APM Traces:**
https://coralogix.com/docs/apm/

**Distributed Tracing:**
https://coralogix.com/docs/distributed-tracing/

**AI Center:**
https://coralogix.com/docs/ai-center/

---

**TL;DR:** You're currently viewing AI Center which filters out infrastructure spans. Switch to **APM → Traces** to see the complete distributed trace including HTTP calls and database queries. 🎯

