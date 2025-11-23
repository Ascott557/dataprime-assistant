<!-- c7cc6218-a198-4a7b-bf77-5e916dcfd7ae 0b02e77f-c397-4017-9b27-b7496c2dd8a4 -->
# Black Friday Failure Simulation Demo

## Overview

Implement a complete Black Friday demo that simulates realistic e-commerce failures: database performance degradation from missing indexes, connection pool exhaustion, escalating traffic patterns, and comprehensive OpenTelemetry instrumentation for Coralogix Flow Alert triggering.

## Phase 1: Database Configuration Issues (Prompt 1)

### Create Database Infrastructure Directory

Create `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/infrastructure/database/` directory structure.

### Create missing_index_config.sql

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/infrastructure/database/missing_index_config.sql`

Contents:

- SQL comments explaining the Black Friday demo scenario
- DROP INDEX statements for `idx_products_category` and `idx_products_stock_quantity`
- Commented-out CREATE INDEX statements for quick restoration
- Clear documentation of expected performance impact

### Create connection_pool_config.yaml

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/infrastructure/database/connection_pool_config.yaml`

Contents:

- `max_connections: 20` (deliberately low, normally 100)
- `connection_timeout: 5s`
- `read_replicas.enabled: false` (this is the bug!)
- Extensive comments explaining the misconfiguration scenario

### Create setup_demo_database_issues.sh

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/infrastructure/database/setup_demo_database_issues.sh`

Key features:

- Connect to `postgresql-primary-0` pod in `ecommerce-demo` namespace
- Execute `missing_index_config.sql` via `kubectl exec`
- Update ConfigMap with `DB_MAX_CONNECTIONS=20`
- Restart relevant pods to pick up configuration
- Echo clear confirmation messages
- Idempotent design (safe to run multiple times)
- Error handling with informative messages

## Phase 2: Product Catalog Slow Query Simulation (Prompt 2)

### Modify product_catalog_service.py

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/product_catalog_service.py`

Changes required:

**Add imports and configuration (after line 24):**

```python
import random
from datetime import datetime, timedelta

# Demo mode configuration
DEMO_MODE = os.getenv('DEMO_MODE', 'off')
DEMO_START_TIME_STR = os.getenv('DEMO_START_TIME', '22:47')
```

**Add helper function (after line 125):**

```python
def calculate_demo_minute():
    """Calculate elapsed minutes since demo start time."""
    if DEMO_MODE != 'blackfriday':
        return 0
    
    try:
        now = datetime.now()
        demo_start = datetime.strptime(DEMO_START_TIME_STR, '%H:%M').replace(
            year=now.year, month=now.month, day=now.day
        )
        elapsed = (now - demo_start).total_seconds() / 60
        return max(0, int(elapsed))
    except Exception as e:
        print(f"Error calculating demo minute: {e}")
        return 0

def get_progressive_delay():
    """Get delay based on demo progression."""
    if DEMO_MODE != 'blackfriday':
        return 0
    
    minute = calculate_demo_minute()
    if minute < 10:
        return 500  # 500ms
    elif minute < 15:
        return 1000  # 1000ms
    else:
        return 2500  # 2500ms (critical)
```

**Modify /products endpoint (around line 247):**

Replace the existing slow query simulation with progressive delay:

```python
# Progressive slow query simulation for Black Friday demo
if DEMO_MODE == 'blackfriday':
    delay_ms = get_progressive_delay()
    demo_minute = calculate_demo_minute()
    
    time.sleep(delay_ms / 1000.0)
    
    span.set_attribute("db.simulation.slow_query_enabled", True)
    span.set_attribute("db.simulation.delay_ms", delay_ms)
    span.set_attribute("demo.minute", demo_minute)
    span.set_attribute("db.full_table_scan", True)
    span.set_attribute("db.missing_index", "idx_products_category")
    span.set_attribute("db.rows_scanned", 10000)
    
    if delay_ms > 1000:
        span.set_attribute("db.slow_query", True)
        logger.warning(
            "Slow query detected: missing index",
            extra={
                "category": category,
                "query_duration_ms": delay_ms,
                "demo_minute": demo_minute,
                "recommended_index": "CREATE INDEX idx_products_category ON products(category)"
            }
        )
```

**Apply same pattern to:**

- `/products/search` endpoint (line 358)
- `/products/popular-with-history` endpoint (line 696)

All three endpoints should use `get_progressive_delay()` and set comprehensive span attributes.

## Phase 3: Checkout Service Connection Pool Exhaustion (Prompt 3)

### Modify checkout_service.py

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/checkout_service.py`

Changes required:

**Add imports and configuration (after line 18):**

```python
import logging
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Demo mode configuration
DEMO_MODE = os.getenv('DEMO_MODE', 'off')
DEMO_START_TIME_STR = os.getenv('DEMO_START_TIME', '22:47')
```

**Add ConnectionPoolSimulator class (after line 51):**

```python
class ConnectionPoolSimulator:
    """Simulates connection pool exhaustion during Black Friday demo."""
    
    def __init__(self):
        self.max_connections = int(os.getenv('DB_MAX_CONNECTIONS', '20'))
        self.rejected_count = 0
    
    def calculate_demo_minute(self):
        """Calculate elapsed minutes since demo start."""
        if DEMO_MODE != 'blackfriday':
            return 0
        
        try:
            now = datetime.now()
            demo_start = datetime.strptime(DEMO_START_TIME_STR, '%H:%M').replace(
                year=now.year, month=now.month, day=now.day
            )
            elapsed = (now - demo_start).total_seconds() / 60
            return max(0, int(elapsed))
        except Exception as e:
            print(f"Error calculating demo minute: {e}")
            return 0
    
    def should_fail_connection(self, span):
        """Determine if connection should fail based on demo progression."""
        if DEMO_MODE != 'blackfriday':
            return False
        
        demo_minute = self.calculate_demo_minute()
        
        # Connection failures increase over time:
        # Minutes 0-15: 0% failure
        # Minute 16: 5% failure
        # Minute 17: 10% failure
        # Minute 18: 15% failure
        # Minute 19: 20% failure
        # Minute 20+: 35% failure
        
        if demo_minute < 15:
            return False
        
        failure_rate = min(0.35, (demo_minute - 15) * 0.05)
        
        if random.random() < failure_rate:
            # Pool exhausted!
            span.set_attribute("db.connection_pool.exhausted", True)
            span.set_attribute("db.connection_pool.size", self.max_connections)
            span.set_attribute("db.connection_pool.active", self.max_connections)
            span.set_attribute("db.connection_pool.wait_time_ms", 5000)
            span.set_attribute("error.type", "ConnectionPoolExhausted")
            span.set_attribute("demo.minute", demo_minute)
            span.set_attribute("demo.failure_rate", failure_rate)
            span.set_status(trace.Status(trace.StatusCode.ERROR))
            
            self.rejected_count += 1
            
            logger.error(
                "Connection pool exhausted",
                extra={
                    "max_connections": self.max_connections,
                    "active_connections": self.max_connections,
                    "wait_time_ms": 5000,
                    "rejected_count": self.rejected_count,
                    "demo_minute": demo_minute,
                    "failure_rate": f"{failure_rate*100:.1f}%",
                    "recommendation": "Enable read replicas or increase max_connections"
                }
            )
            
            return True
        
        return False

# Global simulator instance
pool_simulator = ConnectionPoolSimulator()
```

**Modify /orders/create endpoint (around line 366):**

Wrap the `get_connection()` call with pool exhaustion simulation:

```python
# Check for connection pool exhaustion (Black Friday demo)
if pool_simulator.should_fail_connection(main_span):
    main_span.set_attribute("checkout.failed", True)
    main_span.set_attribute("checkout.failure_reason", "ConnectionPoolExhausted")
    return jsonify({
        "error": "SQLSTATE[08006]: Connection timeout after 5000ms"
    }), 503

# Get connection from pool
conn = get_connection()
```

**Modify /orders/popular-products endpoint (around line 243):**

Add same pattern before `get_connection()` call.

## Phase 4: Black Friday Traffic Scenario (Prompt 4)

### Create black_friday_scenario.py

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/black_friday_scenario.py`

Complete implementation with:

**BlackFridayScenario class:**

- `__init__`: Set normal_rpm=30, peak_rpm=120, phase durations
- `get_current_rpm(elapsed_minutes)`: Calculate RPM based on phase
- `get_user_journey_distribution(elapsed_minutes)`: Return journey weights
- `get_current_phase(elapsed_minutes)`: Return phase name

**User journey definitions:**

```python
JOURNEYS = {
    'browse_only': {
        'weight_normal': 0.60,
        'weight_degraded': 0.50,
        'steps': [
            ('GET', '/products', {'category': 'electronics', 'price_min': 0, 'price_max': 1000}),
            ('GET', '/products', {'category': 'furniture', 'price_min': 0, 'price_max': 5000})
        ]
    },
    'browse_and_cart': {
        'weight_normal': 0.25,
        'weight_degraded': 0.20,
        'steps': [
            ('GET', '/products', {'category': 'sports', 'price_min': 0, 'price_max': 500}),
            ('POST', '/cart/add', {'product_id': 'random', 'quantity': 1}),
            ('GET', '/cart', {})
        ]
    },
    'full_checkout': {
        'weight_normal': 0.15,
        'weight_degraded': 0.30,
        'steps': [
            ('GET', '/products', {'category': 'electronics', 'price_min': 0, 'price_max': 2000}),
            ('POST', '/cart/add', {'product_id': 'random', 'quantity': 2}),
            ('GET', '/cart', {}),
            ('POST', '/checkout', {'user_id': 'random', 'product_id': 'random', 'quantity': 1})
        ]
    }
}
```

**Traffic generation methods:**

- `execute_journey(journey_type, service_urls)`: Execute journey steps with proper trace propagation
- `generate_traffic(duration_minutes, demo_start_time)`: Main traffic generation loop

### Enhance load_generator.py

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/services/load_generator.py`

Add new endpoints:

**POST /admin/start-demo:**

```python
@app.route('/admin/start-demo', methods=['POST'])
def start_demo():
    """Start Black Friday traffic scenario."""
    with tracer.start_as_current_span("load_generator.start_demo") as span:
        data = request.get_json() or {}
        scenario = data.get('scenario', 'blackfriday')
        duration_minutes = data.get('duration_minutes', 30)
        peak_rpm = data.get('peak_rpm', 120)
        
        if scenario != 'blackfriday':
            return jsonify({"error": "Only 'blackfriday' scenario supported"}), 400
        
        # Import and instantiate scenario
        from black_friday_scenario import BlackFridayScenario
        
        bf_scenario = BlackFridayScenario()
        demo_start_time = datetime.now()
        
        # Store demo state
        load_stats['demo_running'] = True
        load_stats['demo_start_time'] = demo_start_time
        load_stats['demo_scenario'] = bf_scenario
        
        # Start traffic generation in background thread
        import threading
        def run_traffic():
            bf_scenario.generate_traffic(duration_minutes, demo_start_time)
            load_stats['demo_running'] = False
        
        thread = threading.Thread(target=run_traffic, daemon=True)
        thread.start()
        
        return jsonify({
            "status": "demo_started",
            "scenario": scenario,
            "duration_minutes": duration_minutes,
            "peak_rpm": peak_rpm,
            "start_time": demo_start_time.isoformat()
        })
```

**GET /admin/demo-status:**

```python
@app.route('/admin/demo-status', methods=['GET'])
def demo_status():
    """Get current demo status."""
    if not load_stats.get('demo_running'):
        return jsonify({
            "running": False,
            "message": "No demo currently running"
        })
    
    demo_start = load_stats.get('demo_start_time')
    scenario = load_stats.get('demo_scenario')
    
    if not demo_start or not scenario:
        return jsonify({"running": False})
    
    elapsed_minutes = (datetime.now() - demo_start).total_seconds() / 60
    current_rpm = scenario.get_current_rpm(elapsed_minutes)
    phase = scenario.get_current_phase(elapsed_minutes)
    
    # Calculate error rate from recent stats
    error_rate = load_stats['errors'] / max(1, load_stats['requests_sent'])
    
    return jsonify({
        "running": True,
        "elapsed_minutes": int(elapsed_minutes),
        "current_rpm": current_rpm,
        "current_error_rate": round(error_rate, 3),
        "phase": phase,
        "checkouts_attempted": load_stats.get('checkouts_attempted', 0),
        "checkouts_failed": load_stats.get('checkouts_failed', 0)
    })
```

## Phase 5: Demo Orchestration Script (Prompt 5)

### Create run-demo.sh

File: `/Users/andrescott/dataprime-assistant-1/coralogix-dataprime-demo/scripts/run-demo.sh`

Complete bash script with:

**Pre-flight checks:**

```bash
#!/bin/bash
set -e

# ANSI colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  BLACK FRIDAY DEMO - PRE-FLIGHT CHECK${NC}"
echo -e "${BLUE}========================================${NC}"

# Check kubectl connectivity
echo -n "Checking Kubernetes connectivity... "
if kubectl cluster-info &> /dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Failed${NC}"
    exit 1
fi

# Check all services running
echo -n "Checking service health... "
PODS=$(kubectl get pods -n ecommerce-demo -l app=product-catalog -o jsonpath='{.items[*].status.phase}')
if [[ "$PODS" == *"Running"* ]]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ Services not ready${NC}"
    exit 1
fi

# Check OTel collector
echo -n "Checking Coralogix OTel Collector... "
OTEL_POD=$(kubectl get pods -n ecommerce-demo -l app.kubernetes.io/name=opentelemetry-collector -o jsonpath='{.items[0].status.phase}')
if [[ "$OTEL_POD" == "Running" ]]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${YELLOW}⚠ OTel Collector not found${NC}"
fi

# Check PostgreSQL
echo -n "Checking PostgreSQL... "
PG_READY=$(kubectl exec -n ecommerce-demo postgresql-primary-0 -- pg_isready -U ecommerce_user 2>&1 | grep "accepting connections")
if [[ -n "$PG_READY" ]]; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗ PostgreSQL not ready${NC}"
    exit 1
fi
```

**Demo timeline display:**

```bash
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}         DEMO TIMELINE${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "  ${GREEN}0-10 min:${NC}  Traffic ramp (30→120 req/min)"
echo -e " ${GREEN}10-15 min:${NC}  Peak traffic, normal ops"
echo -e " ${YELLOW}15-20 min:${NC}  Database degradation"
echo -e " ${YELLOW}20-25 min:${NC}  Connection pool exhaustion"
echo -e " ${RED}22-23 min:${NC}  🚨 FLOW ALERT TRIGGERS"
echo -e " ${RED}25-30 min:${NC}  Peak failure (35%)"
echo -e "${BLUE}========================================${NC}"
echo ""
```

**Configuration application:**

```bash
echo -e "${BLUE}Applying demo configuration...${NC}"

# Run database issues setup script
./infrastructure/database/setup_demo_database_issues.sh

# Set DEMO_MODE and DEMO_START_TIME in ConfigMap
CURRENT_TIME=$(date +%H:%M)
kubectl patch configmap ecommerce-config -n ecommerce-demo \
  --patch "{\"data\": {\"DEMO_MODE\": \"blackfriday\", \"DEMO_START_TIME\": \"$CURRENT_TIME\"}}"

echo -e "${GREEN}✓${NC} ConfigMap updated with DEMO_MODE=blackfriday"

# Restart services to pick up new config
kubectl rollout restart deployment -n ecommerce-demo
kubectl rollout status deployment -n ecommerce-demo --timeout=120s

echo -e "${GREEN}✓${NC} Services restarted"
```

**Start traffic generation:**

```bash

echo -e "${BLUE}Starting Black Friday traffic generation...${NC}"

LOAD_GEN_POD=$(kubectl get pods -n ecommerce-demo -l app=load-generator -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n ecommerce-demo $LOAD_GEN_POD -- \

curl

### To-dos

- [ ] Remove OpenAI/LLM dependencies from requirements.txt and shared_telemetry.py
- [ ] Rename product_service.py to product_catalog_service.py, update references
- [ ] Rename order_service.py to checkout_service.py, update semantics
- [ ] Adapt inventory_service.py to cart_service.py with Redis storage
- [ ] Delete query, validation, queue, and queue_worker services
- [ ] Create load_generator.py service (replaces api_gateway)
- [ ] Adapt recommendation_ai_service to recommendation_service (remove OpenAI)
- [ ] Adapt external_api_service to currency_service
- [ ] Adapt processing_service to shipping_service
- [ ] Adapt storage_service to ad_service
- [ ] Create init-db.sql with e-commerce schema and seed data
- [ ] Create microservices docker-compose.yml with all 8 services
- [ ] Create .env.example with all required environment variables
- [ ] Build, start, and test all services with trace propagation