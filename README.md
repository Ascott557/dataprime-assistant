# 🤖 DataPrime Assistant with AI Observability

> **Production-ready AI application demonstrating comprehensive observability with Coralogix AI Center**

[![AI Observability](https://img.shields.io/badge/AI-Observability-blue)](https://coralogix.com/docs/coralogix-ai-center/)
[![OpenTelemetry](https://img.shields.io/badge/OpenTelemetry-Instrumented-orange)](https://opentelemetry.io/)
[![Flask](https://img.shields.io/badge/Flask-Application-green)](https://flask.palletsprojects.com/)

## Overview

This project demonstrates **enterprise-grade AI observability** using Coralogix AI Center. It's a working Flask application that converts natural language queries into DataPrime syntax while providing comprehensive telemetry, evaluation, and governance.

### Key Features

- ✅ **AI Query Generation** - Natural language to DataPrime conversion using OpenAI GPT-4o
- ✅ **Zero-code Telemetry** - Complete observability using `llm_tracekit` 
- ✅ **Real-time Evaluation** - Policy violation detection via Coralogix evaluators
- ✅ **Dual Mode Demo** - Invisible toggle between permissive and smart modes
- ✅ **Production Ready** - Docker support, error handling, health checks

## Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key
- Coralogix account and token

### Setup

```bash
# 1. Clone and install
git clone <repository-url>
cd dataprime-assistant
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys:
# OPENAI_API_KEY=your-openai-key
# CX_TOKEN=your-coralogix-token

# 3. Start application
python minimal_dataprime_app.py
```

**Access**: http://localhost:8000

### API Endpoints

- `GET /api/health` - Service health and configuration
- `POST /api/generate-query` - Convert natural language to DataPrime
- `POST /api/toggle-mode` - Switch between demo modes

## Demo Usage

The application includes a dual-mode demonstration system:

- **Permissive Mode** (🟠): Generates queries for any input, relies on Coralogix evaluation to detect misuse
- **Smart Mode** (🟢): Application-level filtering blocks inappropriate queries

**Secret Toggle**: Press `Ctrl+S` to invisibly switch modes during live demos.

### Example Queries

**Appropriate (Observability)**:
- "Show me errors from last hour" → `source logs last 1h | filter $m.severity == 'Error'`
- "Count requests by service" → `source logs | groupby $l.service | aggregate count()`

**Inappropriate (Off-topic)**:
- "What's on McDonald's menu?" → Blocked in smart mode, flagged by Coralogix in permissive mode

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Web Interface │───▶│  Flask App       │───▶│  Coralogix AI       │
│   (Port 8000)   │    │  (Dual Mode)     │    │  Center             │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                │                          │
                                ▼                          │
                       ┌──────────────────┐               │
                       │  OpenAI API      │               │
                       │  (Instrumented)  │               │
                       └──────────────────┘               │
                                │                          │
                                ▼                          │
                       ┌──────────────────┐               │
                       │  DataPrime       │               │
                       │  Components      │               │
                       └──────────────────┘               │
                                │                          │
                                ▼                          │
                       ┌──────────────────┐               │
                       │  llm_tracekit    │──────────────┘
                       │  (Telemetry)     │
                       └──────────────────┘
```

## Observability Features

### Telemetry
- **Complete trace data** for all AI interactions
- **Token usage and cost tracking** 
- **Performance metrics** and response times
- **Business context** attributes for filtering

### Evaluation
- **Allowed Topics** - Detects off-topic queries
- **Policy Violations** - Real-time governance alerts  
- **Custom Metrics** - Domain-specific evaluations

### Dashboard Access
Navigate to Coralogix AI Center → Application Catalog → `query-generator` to view:
- LLM call traces and costs
- Evaluation results and policy violations  
- Performance analytics and trends

## Docker Deployment

```bash
# Set environment variables
export OPENAI_API_KEY="your-key"
export CX_TOKEN="your-token" 

# Deploy with Docker Compose
docker-compose up --build
```

## Configuration

### Required Environment Variables

```bash
OPENAI_API_KEY=your-openai-api-key-here
CX_TOKEN=your-coralogix-token-here
```

### Optional Configuration

```bash
CX_ENDPOINT=https://ingress.eu2.coralogix.com:443  # Regional endpoint
PORT=8000                                          # Application port  
DEBUG=true                                         # Debug logging
DEFAULT_DEMO_MODE=permissive                       # Demo mode
```

## API Examples

### Generate Query
```bash
curl -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -d '{"user_input": "show me errors from last hour"}'
```

### Health Check
```bash
curl http://localhost:8000/api/health
```

### Toggle Demo Mode
```bash
curl -X POST http://localhost:8000/api/toggle-mode
```

## Technical Highlights

- **Prompt Engineering**: Clean separation of system instructions and user input prevents evaluation contamination
- **Multi-layer Governance**: Application-level + observability-level AI policy enforcement
- **Zero-code Instrumentation**: Automatic telemetry using OpenTelemetry standards
- **Production Patterns**: Health checks, error handling, environment validation

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality  
4. Submit a pull request

---

**Built with ❤️ for AI Observability demonstrations**