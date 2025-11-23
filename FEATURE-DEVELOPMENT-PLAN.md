# Feature Development Plan - Realistic E-commerce Demo

**Branch:** `feature/realistic-ecommerce-demo`  
**Created:** November 23, 2025  
**Goal:** Build a production-quality, realistic e-commerce observability demo

---

## Current State Assessment

### ✅ What's Working (Preserved)

1. **Multi-Service Architecture**
   - 8 microservices deployed and running
   - Proper service-to-service communication
   - Realistic e-commerce flow

2. **OpenTelemetry Instrumentation**
   - Manual trace propagation working
   - Traces flowing to Coralogix (~10-20 spans/batch)
   - OTel Collector healthy and exporting

3. **Infrastructure**
   - AWS K3s cluster @ 54.235.171.176
   - PostgreSQL database
   - Redis cache
   - All pods healthy

4. **Black Friday Demo (from commit `3d8aa6f`)**
   - Database degradation simulation
   - Connection pool exhaustion
   - Progressive failure timeline
   - Flow Alert configuration

### ⚠️ Known Issues

1. **Load Generator**
   - Manual trigger required (no auto-start)
   - Blocking API calls
   - Needs improvement for realistic user journeys

2. **Product Catalog**
   - 500 errors on product queries
   - Database schema issues
   - Missing proper error handling

3. **Database**
   - Schema not fully initialized
   - Missing seed data
   - Connection issues in some flows

4. **Observability Gaps**
   - Database APM not fully visible
   - Missing some service-to-service traces
   - Error rates higher than expected

---

## Development Principles

### 🎯 Core Guidelines

1. **Realistic First**
   - All features must represent authentic e-commerce flows
   - Multi-service interactions required
   - No shortcuts that bypass real architecture

2. **Observability Native**
   - Every feature generates meaningful telemetry
   - Traces show complete distributed flows
   - Database operations visible in APM

3. **Incremental Progress**
   - Small, tested commits
   - Each feature branch is self-contained
   - No breaking changes to working components

4. **Test Before Deploy**
   - Verify locally when possible
   - Check telemetry flow after every change
   - Validate in Coralogix before declaring done

---

## Proposed Features (Priority Order)

### Phase 1: Stabilize Core Platform

#### 1.1 Fix Database Schema
**Priority:** HIGH  
**Effort:** 2-3 hours  

**Goal:** Ensure database is properly initialized with complete schema and seed data

**Tasks:**
- [ ] Review and fix `init-db.sql`
- [ ] Add comprehensive seed data (50-100 products)
- [ ] Create proper indexes
- [ ] Add database constraints
- [ ] Test all CRUD operations

**Success Criteria:**
- ✅ All product queries return 200 (not 500)
- ✅ Database has realistic product catalog
- ✅ Queries are fast (<100ms)

---

#### 1.2 Improve Load Generator
**Priority:** HIGH  
**Effort:** 3-4 hours

**Goal:** Create realistic, auto-starting traffic that simulates real user journeys

**Tasks:**
- [ ] Add auto-start on pod initialization
- [ ] Implement realistic user journeys:
  - Browse → View Product
  - Browse → Add to Cart
  - Browse → Cart → Checkout
  - Browse → Checkout (abandoned cart)
- [ ] Add configurable traffic patterns
- [ ] Implement proper error handling
- [ ] Add traffic metrics endpoint

**Success Criteria:**
- ✅ Traffic auto-starts when pod launches
- ✅ Realistic distribution of user actions
- ✅ Full traces across all services
- ✅ Metrics available via API

---

#### 1.3 Enhance Error Handling
**Priority:** MEDIUM  
**Effort:** 2-3 hours

**Goal:** Proper error propagation with meaningful telemetry

**Tasks:**
- [ ] Add try-catch blocks in all services
- [ ] Set proper span statuses on errors
- [ ] Add error attributes to spans
- [ ] Log errors with structured data
- [ ] Return appropriate HTTP status codes

**Success Criteria:**
- ✅ Errors visible in traces
- ✅ Proper error propagation
- ✅ Meaningful error messages

---

### Phase 2: Enhanced Observability

#### 2.1 Database APM Visibility
**Priority:** HIGH  
**Effort:** 2-3 hours

**Goal:** Full visibility into database operations in Coralogix

**Tasks:**
- [ ] Ensure psycopg2 instrumentation working
- [ ] Add database span attributes
- [ ] Capture query details
- [ ] Track connection pool metrics
- [ ] Add slow query detection

**Success Criteria:**
- ✅ Database operations visible in Coralogix APM
- ✅ Query details captured
- ✅ Connection pool metrics available

---

#### 2.2 Service Mesh Visibility
**Priority:** MEDIUM  
**Effort:** 3-4 hours

**Goal:** Complete visibility of all service-to-service calls

**Tasks:**
- [ ] Verify all services propagate trace context
- [ ] Add service-level metrics
- [ ] Track latencies per service
- [ ] Monitor error rates
- [ ] Add service dependency graph

**Success Criteria:**
- ✅ All service calls traced
- ✅ Complete dependency visualization
- ✅ Per-service metrics available

---

### Phase 3: Realistic Demo Scenarios

#### 3.1 Normal Operations Demo
**Priority:** MEDIUM  
**Effort:** 2-3 hours

**Goal:** Show healthy e-commerce platform with realistic traffic

**Tasks:**
- [ ] Configure steady-state traffic (30-60 rpm)
- [ ] All services responding normally
- [ ] Database performing well
- [ ] Clean traces with no errors

**Success Criteria:**
- ✅ <5% error rate
- ✅ P95 latency <500ms
- ✅ Clean traces in Coralogix

---

#### 3.2 Flash Sale Scenario
**Priority:** MEDIUM  
**Effort:** 4-5 hours

**Goal:** Realistic high-traffic event with graceful degradation

**Tasks:**
- [ ] Traffic ramp from 30 rpm → 300 rpm
- [ ] Simulate inventory contention
- [ ] Show cache effectiveness
- [ ] Demonstrate autoscaling (if configured)
- [ ] Proper error handling under load

**Success Criteria:**
- ✅ Traffic scales smoothly
- ✅ Errors increase gradually (not catastrophically)
- ✅ Recovery after traffic drops

---

#### 3.3 Database Issue Scenario
**Priority:** LOW  
**Effort:** 3-4 hours

**Goal:** Show how database problems affect the platform

**Tasks:**
- [ ] Simulate slow queries (missing indexes)
- [ ] Connection pool exhaustion
- [ ] Proper backpressure to clients
- [ ] Alert triggering

**Success Criteria:**
- ✅ Database issues visible in traces
- ✅ Error propagation makes sense
- ✅ Flow Alert triggers appropriately

---

### Phase 4: Advanced Features

#### 4.1 Real User Monitoring (RUM)
**Priority:** LOW  
**Effort:** 4-6 hours

**Goal:** Frontend observability with Coralogix RUM

**Tasks:**
- [ ] Add simple web frontend
- [ ] Integrate Coralogix RUM SDK
- [ ] Connect frontend → backend traces
- [ ] Track user sessions
- [ ] Monitor page performance

---

#### 4.2 Custom Business Metrics
**Priority:** LOW  
**Effort:** 2-3 hours

**Goal:** Business-level observability

**Tasks:**
- [ ] Track revenue per request
- [ ] Monitor cart abandonment rate
- [ ] Checkout success rate
- [ ] Average order value
- [ ] Export as custom metrics

---

## Development Workflow

### Before Starting Any Feature

1. **Create subtask branch**
   ```bash
   git checkout feature/realistic-ecommerce-demo
   git checkout -b feature/fix-database-schema
   ```

2. **Document the goal**
   - What problem are you solving?
   - How will you know it's done?
   - What could go wrong?

3. **Make a plan**
   - Break into small steps
   - Identify dependencies
   - Estimate time

### During Development

1. **Small commits**
   - One logical change per commit
   - Clear commit messages
   - Test after each commit

2. **Verify locally when possible**
   - Use docker-compose if available
   - Check logs for errors
   - Test manually

3. **Deploy to AWS incrementally**
   - Don't batch multiple changes
   - Check telemetry after each deploy
   - Rollback if issues arise

### After Completing Feature

1. **Verify in Coralogix**
   - Check traces
   - Verify metrics
   - Confirm no new errors

2. **Merge back to feature branch**
   ```bash
   git checkout feature/realistic-ecommerce-demo
   git merge feature/fix-database-schema
   ```

3. **Document what changed**
   - Update relevant docs
   - Add to CHANGELOG
   - Note any gotchas

4. **Only merge to main when stable**
   - Feature branch should be thoroughly tested
   - Multiple features can be built before merging
   - Main branch stays stable

---

## Success Metrics

### Platform Health
- ✅ All services running without crashes
- ✅ <10% error rate
- ✅ P95 latency <1 second
- ✅ Database queries <200ms average

### Observability Quality
- ✅ 100% of requests traced
- ✅ Complete service graph visible
- ✅ Database operations in APM
- ✅ Meaningful error messages

### Demo Effectiveness
- ✅ Realistic user journeys
- ✅ Clear problem scenarios
- ✅ Compelling narrative
- ✅ Easy to reproduce

---

## Anti-Patterns to Avoid

### ❌ Don't Do This

1. **Direct Service Calls from Load Generator**
   - Load generator should simulate user actions
   - Let orchestration services handle coordination
   - Don't bypass realistic flow for convenience

2. **Fake Traffic Patterns**
   - No unrealistic RPM jumps
   - Real users don't behave uniformly
   - Include think time and abandonment

3. **Ignoring Errors**
   - Every error should be investigated
   - High error rates mean something is broken
   - Don't accept "good enough for demo"

4. **Breaking Working Features**
   - Test before deploying
   - Have rollback plan
   - Don't sacrifice stability for new features

5. **Poor Git Hygiene**
   - No commits to main without review
   - No force pushes
   - Keep feature branches focused

---

## Getting Started

### Recommended First Task: Fix Database Schema

This is the foundation. Once the database works properly, everything else becomes easier.

```bash
# Start here
git checkout feature/realistic-ecommerce-demo

# Check current database state
ssh -i ~/.ssh/ecommerce-platform-key.pem ubuntu@54.235.171.176 \
  'sudo kubectl exec -n ecommerce-demo postgresql-primary-0 -- \
   psql -U ecommerce_user -d ecommerce -c "\dt"'

# Review init-db.sql
cat coralogix-dataprime-demo/docker/init-db.sql

# Make improvements, test, commit
```

---

## Questions to Answer Before Building

1. **What's the narrative?**
   - Who is the audience?
   - What story are we telling?
   - What problems are we demonstrating?

2. **What's the scope?**
   - Just observability, or full platform demo?
   - How much complexity do we need?
   - What's the time budget?

3. **What's success?**
   - When is this "done"?
   - What are the must-haves vs nice-to-haves?
   - How will we measure effectiveness?

---

**Next Step:** Review this plan and decide which feature to tackle first. I recommend starting with fixing the database schema, as it's foundational for everything else.

