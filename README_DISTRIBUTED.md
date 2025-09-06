# 🚀 Distributed DataPrime Assistant - Enterprise Architecture

This is a **complete transformation** of the DataPrime Assistant into a proper distributed system with enterprise-grade distributed tracing, showcasing single root span propagation and realistic microservices architecture.

## 🏗️ Architecture Overview

```
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend  │───▶│ API Gateway  │───▶│ Query Service   │───▶│ Validation Svc  │
│   (Port -)  │    │  (Port 5000) │    │  (Port 5001)    │    │  (Port 5002)    │
└─────────────┘    └──────────────┘    └─────────────────┘    └─────────────────┘
                                                │                        │
                                                ▼                        ▼
┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Database   │◀───│Queue Worker  │◀───│ Queue Service   │◀───│ Processing Svc  │
│   (SQLite)  │    │ (Background) │    │  (Port 5003)    │    │  (Port 5004)    │
└─────────────┘    └──────────────┘    └─────────────────┘    └─────────────────┘
                                                                        │
                                                                        ▼
                                                                ┌─────────────────┐
                                                                │ Storage Service │
                                                                │  (Port 5005)    │
                                                                └─────────────────┘
```

## 🔧 Services Breakdown

### 🌐 API Gateway (Port 5000)
- **Role**: Entry point for all requests
- **Responsibilities**: Request routing, trace context initiation, service orchestration
- **Endpoints**: `/api/generate-query`, `/api/feedback`, `/api/health`, `/api/stats`
- **Timing**: 5-10ms processing time

### 🧠 Query Service (Port 5001)
- **Role**: LLM-powered DataPrime query generation
- **Responsibilities**: Intent classification, OpenAI integration, query generation
- **Dependencies**: OpenAI API
- **Timing**: 800-1200ms (realistic LLM response time)

### ✅ Validation Service (Port 5002)
- **Role**: DataPrime query validation and enhancement
- **Responsibilities**: Syntax validation, performance suggestions, query optimization
- **Timing**: 50-100ms for comprehensive validation

### 📬 Queue Service (Port 5003)
- **Role**: Message queue and background job management
- **Responsibilities**: Asynchronous processing, job queuing, background worker management
- **Features**: In-memory queue with background worker thread
- **Timing**: 10-20ms for queue operations

### ⚙️ Processing Service (Port 5004)
- **Role**: Background data processing and analysis
- **Responsibilities**: Query complexity analysis, performance insights, data transformation
- **Timing**: 100-200ms for complex processing

### 💾 Storage Service (Port 5005)
- **Role**: Data persistence and feedback management
- **Responsibilities**: SQLite database operations, feedback storage, analytics tracking
- **Timing**: 20-50ms for database operations

## 🔗 Distributed Tracing Features

### ✅ Single Root Span Architecture
- **Root Span**: `api_gateway.generate_query_pipeline` - initiated by API Gateway
- **Child Spans**: Each service creates child spans that properly inherit trace context
- **Trace Context Propagation**: W3C TraceContext standard across all HTTP calls

### 🌳 Span Hierarchy
```
ROOT: api_gateway.generate_query_pipeline
├── api_gateway.call_query_service
│   └── query_service.generate_dataprime_query
│       ├── query_service.classify_intent
│       └── query_service.openai_generation (LLM call)
├── api_gateway.call_validation_service
│   └── validation_service.validate_dataprime_query
│       ├── validation_service.syntax_analysis
│       └── validation_service.enhancement_suggestions
├── api_gateway.enqueue_processing
│   └── queue_service.enqueue_message
│       └── queue_service.add_to_queue
└── queue_service.process_background_message
    └── processing_service.process_query_data
        ├── processing_service.analyze_complexity
        ├── processing_service.generate_insights
        ├── processing_service.transform_data
        └── processing_service.store_insights
            └── storage_service.store_processing_data
```

### 🎯 Service Instrumentation
- **Flask Auto-Instrumentation**: Each service automatically traces HTTP requests
- **Custom Business Logic Spans**: Manual spans for important business operations
- **OpenAI Instrumentation**: Automatic tracing of LLM calls with token usage
- **Database Instrumentation**: SQLite operations automatically traced
- **HTTP Client Instrumentation**: All inter-service calls traced

## 🚀 Quick Start

### 1. Prerequisites
```bash
# Ensure you have Python 3.8+ and virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Setup
```bash
# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys:
# OPENAI_API_KEY=your-openai-api-key
# CX_TOKEN=your-coralogix-token
```

### 3. Start Distributed System
```bash
# Option 1: Use the startup script (recommended)
./start_distributed_system.sh

# Option 2: Start manually
python distributed_app.py
```

### 4. Test the System
```bash
# Run comprehensive tests
python test_distributed_tracing.py

# Manual test via curl
curl -X POST http://localhost:8010/api/generate-query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Show me errors from the last hour grouped by service"}'
```

## 📊 Expected Coralogix Results

### Service Map View
- **6 interconnected services** with clear dependency relationships
- **Service topology** showing API Gateway → Query/Validation → Queue → Processing → Storage
- **Realistic latency distribution** across service boundaries

### Trace View
- **Single root trace** spanning all services
- **Total trace duration**: 1-2 seconds with proper timing breakdown:
  - API Gateway: 5-10ms
  - Query Service: 800-1200ms (LLM call dominates)
  - Validation Service: 50-100ms
  - Queue Service: 10-20ms
  - Processing Service: 100-200ms
  - Storage Service: 20-50ms

### Span Attributes
Each span includes rich attributes for observability:
- **Service identification**: `service.name`, `service.version`
- **Business context**: `user.input.query`, `query.generated`, `intent.type`
- **Performance metrics**: `processing.time_ms`, `validation.score`
- **Technical details**: `database.operation`, `queue.size`, `openai.tokens_used`

## 🔧 Configuration

### Service Ports
- API Gateway: `5000`
- Query Service: `5001`
- Validation Service: `5002`
- Queue Service: `5003`
- Processing Service: `5004`
- Storage Service: `5005`

### Telemetry Configuration
```python
# Coralogix configuration
service_name="dataprime_distributed_system"
application_name="ai-dataprime-enterprise" 
subsystem_name="distributed-microservices"
```

## 🐛 Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   # Check if ports are already in use
   lsof -i :5000-5005
   
   # Kill existing processes
   ./cleanup_port.sh
   ```

2. **Missing dependencies**
   ```bash
   pip install opentelemetry-instrumentation-requests>=0.48b0
   ```

3. **Environment variables not set**
   ```bash
   # Check your .env file
   cat .env
   # Should contain OPENAI_API_KEY and CX_TOKEN
   ```

4. **Services can't communicate**
   ```bash
   # Test individual service health
   curl http://localhost:8011/health
   curl http://localhost:8012/health
   # etc.
   ```

### Health Checks
Each service provides a `/health` endpoint:
- `GET http://localhost:8010/api/health` - API Gateway + downstream health
- `GET http://localhost:8011/health` - Query Service
- `GET http://localhost:8012/health` - Validation Service
- `GET http://localhost:8013/health` - Queue Service
- `GET http://localhost:8014/health` - Processing Service
- `GET http://localhost:8015/health` - Storage Service

## 📈 Monitoring & Observability

### Key Metrics to Monitor
1. **Request Success Rate**: API Gateway success/error ratio
2. **Service Latency**: P95 response times per service
3. **Queue Depth**: Background processing queue size
4. **Database Performance**: Storage service operation timing
5. **OpenAI Usage**: Token consumption and response times

### Coralogix Dashboards
Look for these patterns in your Coralogix dashboard:
- **Service Dependencies**: Clear service-to-service call patterns
- **Error Propagation**: How errors flow through the system
- **Performance Bottlenecks**: Which services contribute most to latency
- **Business Metrics**: Query success rates, user satisfaction scores

## 🎯 Demo Script

For demonstrations, use this flow:

1. **Start System**: `./start_distributed_system.sh`
2. **Generate Query**: Submit a complex query via API Gateway
3. **Show Coralogix**: Display the resulting trace with single root span
4. **Highlight Architecture**: Point out 6 connected services
5. **Discuss Timing**: Show realistic enterprise timing distribution
6. **Submit Feedback**: Demonstrate feedback storage flow
7. **Show Service Map**: Display service dependency graph

## 🔮 Future Enhancements

- **Redis Integration**: Replace in-memory queue with Redis
- **Kubernetes Deployment**: Container orchestration configuration
- **Circuit Breakers**: Resilience patterns for service failures
- **Rate Limiting**: API Gateway rate limiting and throttling
- **Metrics Collection**: Prometheus metrics export
- **Service Mesh**: Istio integration for advanced observability

---

**This distributed architecture demonstrates enterprise-grade observability with proper trace context propagation, realistic service complexity, and comprehensive monitoring capabilities.**
