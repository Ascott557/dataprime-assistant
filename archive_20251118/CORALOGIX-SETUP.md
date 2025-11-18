# Coralogix UI Configuration Guide

This document describes how to configure dashboards, SLOs, and alerts in the Coralogix UI after deploying the e-commerce recommendation system.

**IMPORTANT**: All evaluations, P95/P99 calculations, dashboards, SLOs, and alerts are configured in the Coralogix UI. Your application code only emits the proper OpenTelemetry data.

---

## Prerequisites

1. Application deployed and running (Docker or Kubernetes)
2. Telemetry data flowing to Coralogix (eu2.coralogix.com)
3. Access to Coralogix UI with admin permissions

---

## Step 1: Get RUM Public Key

Before deploying the frontend, obtain your RUM public key:

1. Log into Coralogix UI: https://eu2.coralogix.com
2. Navigate to **Data Flow → RUM**
3. Click **"Create Application"**
4. Enter application name: `ecommerce-recommendation`
5. Click **"Create"**
6. Copy the **Public Key** (format: `pub_xxxxx...`)
7. Update your `.env` file:
   ```bash
   CX_RUM_PUBLIC_KEY=pub_your_actual_key_here
   ```
8. Restart the frontend service

---

## Step 2: Enable AI Center Evaluations

Coralogix runs evaluations server-side. You only need to enable them in the UI.

### Enable Context Adherence

1. Navigate to **AI Center → Eval Catalog**
2. Find **Context Adherence** evaluation
3. Click **"Add to App"**
4. Select application: `ecommerce-recommendation`
5. Configure threshold:
   - **Threshold**: Score < 0.8 = Issue
   - This flags when AI responses don't match the tool call results
6. Click **"Enable"**

### Enable Tool Parameter Correctness

1. In **AI Center → Eval Catalog**
2. Find **Tool Parameter Correctness** evaluation
3. Click **"Add to App"**
4. Select application: `ecommerce-recommendation`
5. This automatically validates tool parameters against the schema
6. Click **"Enable"**

### View Results

1. Navigate to **AI Center → Application Overview**
2. Select application: `ecommerce-recommendation`
3. You will see:
   - **Issue Rate**: Automatically calculated (% of LLM calls with failed evaluations)
   - **Error Rate**: % of LLM calls that failed completely
   - **Evaluation Scores**: Click any LLM call to see detailed scores

**When tool calls succeed**: Context Adherence ~0.95 (high), Tool Correctness PASSED  
**When tool calls fail**: Context Adherence ~0.12 (low), Tool Correctness FAILED

---

## Step 3: Create SLO (Scene 11)

Service Level Objectives track business commitments.

1. Navigate to **SLOs → Create SLO**
2. Enter SLO details:
   - **Name**: `AI Recommendation Quality`
   - **Description**: `Ensures AI recommendations pass quality evaluations`
   - **Type**: Availability SLO
   - **Target**: 95% (≥95% success rate)
   - **Measurement Window**: 1 hour rolling
   - **Data Source**: AI Center Issue Rate

3. Configure measurement query:
   ```dataprime
   source logs
   | filter $d.cx.application_name == 'ecommerce-recommendation'
   | filter $d.cx.subsystem_name == 'ai-engine'
   | filter $d.gen_ai.system == 'openai'
   | create has_issue = (
       $d['gen_ai.response.evaluations.context_adherence.score'] < 0.8 or
       $d['gen_ai.response.evaluations.tool_parameter_correctness.passed'] == false
   )
   | aggregate
       sum(if(has_issue, 1, 0)) as issue_count,
       count() as total_calls
   | create success_rate = ((total_calls - issue_count) / total_calls) * 100
   | filter success_rate < 95  // Breach when below 95%
   ```

4. Configure alerting:
   - **Alert on breach**: Yes
   - **Notification channel**: Slack/Email
   - **Severity**: High

5. Click **"Create SLO"**

---

## Step 4: Create Flow Alert (Scene 1-2)

Flow Alerts fire when multiple conditions are met simultaneously.

1. Navigate to **Alerts → Create Alert → Flow Alert**
2. Enter alert details:
   - **Name**: `Product Recommendation AI - Quality Degradation`
   - **Description**: `Cascading failure from infrastructure to business impact`
   - **Trigger**: All conditions must be true within 5 minutes

3. Add Condition 1: **AI Issue Rate > 20%**
   ```dataprime
   source logs
   | filter $d.cx.application_name == 'ecommerce-recommendation'
   | filter exists($d['gen_ai.response.evaluations'])
   | create has_issue = (
       $d['gen_ai.response.evaluations.context_adherence.score'] < 0.8 or
       $d['gen_ai.response.evaluations.tool_parameter_correctness.passed'] == false
   )
   | aggregate sum(if(has_issue, 1, 0)) / count() * 100 as issue_rate
   | filter issue_rate > 20
   ```

4. Add Condition 2: **Cart Abandonment Rate > 20%**
   ```dataprime
   source logs
   | filter $d.cx.application_name == 'ecommerce-recommendation'
   | filter $d.action == 'cart_abandonment'
   | aggregate count() as abandonments
   // Calculate rate vs total sessions in UI
   ```

5. Add Condition 3: **Product Service Error Rate > 5%**
   ```dataprime
   source spans
   | filter $d.service_name == 'product-service'
   | filter $d.status_code == 'ERROR'
   | aggregate count() as errors
   // Calculate rate vs total requests in UI
   ```

6. Add Condition 4: **SLO Breach**
   - Select existing SLO: `AI Recommendation Quality`
   - Breach condition: Success rate < 95%

7. Configure notification:
   - **Channel**: Slack
   - **Channel name**: `#incidents`
   - **Message template**:
     ```
     🚨 Product Recommendation AI Quality Degradation
     
     Multiple systems affected:
     - AI Issue Rate > 20%
     - Cart Abandonment > 20%
     - Product Service Errors > 5%
     - SLO Breach: AI Quality < 95%
     
     Investigate immediately in AI Center and Database APM.
     ```

8. Click **"Create Flow Alert"**

---

## Step 5: Create Custom Dashboard (Scene 13)

Build a unified dashboard showing all 4 observability stages.

1. Navigate to **Dashboards → Create Dashboard**
2. Enter dashboard name: `Product Recommendation AI Health - 4-Stage Observability`
3. Set time range: Last 1 hour (adjustable)

### Row 1: Stage 4 - Business Metrics

**Widget 1: AI Issue Rate**
- Type: Line Chart
- Data Source: AI Center
- Metric: `ai.issue_rate_percent`
- Query:
  ```dataprime
  source logs
  | filter $d.cx.application_name == 'ecommerce-recommendation'
  | filter exists($d['gen_ai.response.evaluations'])
  | create has_issue = (
      $d['gen_ai.response.evaluations.context_adherence.score'] < 0.8 or
      $d['gen_ai.response.evaluations.tool_parameter_correctness.passed'] == false
  )
  | aggregate sum(if(has_issue, 1, 0)) / count() * 100 as issue_rate
  ```

**Widget 2: Revenue per Session**
- Type: Gauge
- Data Source: RUM
- Metric: Custom calculation from RUM data

**Widget 3: Cart Abandonment Rate**
- Type: Line Chart
- Data Source: RUM
- Filter: `action == 'cart_abandonment'`

### Row 2: Stage 3 - User Experience

**Widget 4: Active User Sessions**
- Type: Counter
- Data Source: RUM
- Metric: Active sessions count

**Widget 5: Recommendation Ratings**
- Type: Histogram
- Data Source: Metrics
- Metric: `business.recommendation_rating`

### Row 3: Stage 2 - Application Metrics

**Widget 6: Product Service Error Rate**
- Type: Line Chart
- Data Source: APM
- Query:
  ```dataprime
  source spans
  | filter $d.service_name == 'product-service'
  | filter $d.status_code == 'ERROR'
  | aggregate count() as errors
  ```

**Widget 7: Tool Call Success Rate**
- Type: Line Chart
- Data Source: Metrics
- Metric: Calculate from `ai.tool_call.success` and `ai.tool_call.failure`

**Widget 8: API Latency P95**
- Type: Line Chart
- Data Source: APM
- Metric: API Gateway P95 latency

### Row 4: Stage 1 - Infrastructure Metrics

**Widget 9: DB Query Duration P95**
- Type: Line Chart
- Data Source: Metrics
- Metric: `db.query.duration_ms` (P95 auto-calculated from histogram)

**Widget 10: DB Query Duration P99**
- Type: Line Chart
- Data Source: Metrics
- Metric: `db.query.duration_ms` (P99 auto-calculated from histogram)

**Widget 11: Active Queries**
- Type: Line Chart
- Data Source: Metrics
- Metric: `db.active_queries`

**Widget 12: Connection Pool Utilization**
- Type: Gauge
- Data Source: Metrics
- Metric: `db.connection_pool.utilization_percent`

### Dashboard Settings

- **Time Sync**: All widgets use same time range
- **Auto-refresh**: 30 seconds
- **Demo marker**: Add vertical line at 10:47 AM for demo purposes

4. Click **"Save Dashboard"**

---

## Step 6: Verify End-to-End Integration

### Test Normal Flow

1. Access frontend: http://localhost:8020
2. Enter user context: "Looking for wireless headphones, $50-150 range"
3. Click "Get Recommendations"
4. Verify in Coralogix:
   - **AI Center**: LLM call appears with high Context Adherence (~0.95)
   - **Traces**: Single trace ID from frontend → database
   - **Metrics**: `db.query.duration_ms` shows healthy latency (~45ms)

### Test Failure Scenario

1. In frontend, click **"Simulate Slow Database"**
2. Request recommendations again
3. Verify in Coralogix:
   - **Database APM**: P95 jumps to ~2800ms
   - **Traces**: Tool call shows timeout after 3000ms
   - **AI Center**: Context Adherence drops to ~0.12 (AI used fallback)
   - **Flow Alert**: Should fire when all 4 conditions are met

---

## Troubleshooting

### Evaluations Not Appearing

**Problem**: AI Center shows LLM calls but no evaluation scores.

**Solution**:
1. Verify `llm-tracekit` is configured with `capture_content=True`
2. Check that evaluations are enabled in AI Center → Eval Catalog
3. Wait 1-2 minutes for evaluations to process

### P95/P99 Not Calculated

**Problem**: Database APM doesn't show P95/P99 metrics.

**Solution**:
1. Verify code records to histogram: `db_query_duration_histogram.record(duration_ms)`
2. DON'T set span attributes like `span.set_attribute("db.query.p95", ...)` (wrong approach)
3. Coralogix calculates P95/P99 from histogram data automatically

### RUM Data Not Appearing

**Problem**: RUM dashboard is empty.

**Solution**:
1. Verify RUM public key is correct in `.env`
2. Check browser console for RUM SDK initialization
3. Verify RUM SDK loads: Check Network tab for `coralogix-rum.min.js`

### Traces Not Correlating

**Problem**: Multiple trace IDs instead of one end-to-end trace.

**Solution**:
1. Verify W3C trace context propagation in all services
2. Check that `TraceContextTextMapPropagator().inject(headers)` is called
3. Check that `TraceContextTextMapPropagator().extract(headers)` is called

---

## Demo Checklist

Before running the demo:

- [ ] RUM public key configured
- [ ] Context Adherence evaluation enabled
- [ ] Tool Parameter Correctness evaluation enabled
- [ ] SLO "AI Recommendation Quality" created (target: 95%)
- [ ] Flow Alert created with 4 conditions
- [ ] Custom dashboard created with all 4 stages
- [ ] Normal flow tested (healthy metrics)
- [ ] Failure scenario tested (degraded metrics, alert fires)
- [ ] All traces show single trace ID end-to-end

---

## Support

For issues with Coralogix configuration:
- Documentation: https://coralogix.com/docs/
- Support: support@coralogix.com
- Community: https://community.coralogix.com/


