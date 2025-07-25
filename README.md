# 🤖 Fake DataPrime Assistant

A **Natural Language to DataPrime Query** translation system built with OpenAI GPT-4o and Flask. Convert plain English into Coralogix DataPrime syntax with enterprise-grade observability.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- OpenAI API key
- Coralogix credentials (optional)

### Installation & Setup

1. **Clone and setup**:
```bash
git clone <your-repo-url>
cd dataprime-assistant
```

2. **Create `.env` file**:
```bash
# OpenAI Configuration (REQUIRED)
OPENAI_API_KEY=sk-proj-your-key-here

# Coralogix Configuration (OPTIONAL - for telemetry export)  
CX_TOKEN=your-coralogix-token
CX_ENDPOINT=ingress.eu2.coralogix.com:443
```

3. **Start the application**:
```bash
chmod +x start_app.sh
./start_app.sh
```

4. **Open browser**: http://localhost:8000

## 🎯 Features

### Core Functionality
- **Natural Language Input**: "show me errors from the frontend"
- **DataPrime Output**: `source logs | filter $m.severity == 'Error' and $l.subsystemname == 'frontend'`
- **Intent Classification**: Automatic detection of query intent (errors, performance, aggregation, etc.)
- **Validation**: Real-time syntax and semantic validation
- **Dual AI Modes**: Smart (focused) vs Permissive (creative)

### Demo Features
- **Ctrl+D**: Create slow database span (1.5s delay) for performance demos
- **Ctrl+S**: Toggle between Smart (🟢) and Permissive (🟠) AI modes
- **Real-time feedback**: Instant query generation and validation

## 🏗️ Technical Architecture

```
User Input → Intent Classifier → OpenAI GPT-4o → DataPrime Query → Validation → Response
     ↓              ↓                ↓              ↓             ↓          ↓
OpenTelemetry Instrumentation → Coralogix Export (spans, metrics, logs)
```

### Stack
- **Backend**: Flask 3.1.1, Python 3.8+
- **AI**: OpenAI GPT-4o (few-shot prompting, temperature 0.3)
- **Observability**: OpenTelemetry SDK, Coralogix export
- **Frontend**: Vanilla HTML/CSS/JavaScript

### Key Components
- **Few-shot Learning**: Domain-specific prompts with DataPrime examples
- **Rule-based Intent Classification**: Keyword matching + confidence scoring
- **AST-based Validation**: Syntax parsing, semantic validation, complexity scoring
- **GenAI Semantic Conventions**: OpenTelemetry instrumentation for LLM calls

## 🎭 Demo Scenarios

### Performance Analysis Demo
1. Press **Ctrl+D** to create a slow database span
2. Use Coralogix MCP to query: "show me slow spans from the last hour"
3. Analyze the generated spans for performance bottlenecks
4. Get AI-powered optimization suggestions

### Query Translation Demo
- **Input**: "count errors by service last 24 hours"
- **Output**: `source logs last 1d | filter $m.severity == 'Error' | groupby $l.subsystemname aggregate count()`

## 📊 Sample Queries

| Natural Language | Generated DataPrime |
|------------------|-------------------|
| "show recent errors" | `source logs last 1h \| filter $m.severity == 'Error'` |
| "top slow endpoints" | `source logs \| top 10 by $d.response_time` |
| "count by service" | `source logs \| groupby $l.subsystemname aggregate count()` |

## 🛠️ Utilities

- **`start_app.sh`**: Complete setup and launch script
- **`cleanup_port.sh`**: Clean up port 8000 if needed
- **`requirements.txt`**: Python dependencies

## 🔧 Configuration

### AI Modes
- **Smart Mode** (🟢): Focused on observability queries, strict validation
- **Permissive Mode** (🟠): Creative interpretation, broader query scope

### Telemetry
- **Automatic LLM tracing**: Captures prompts, responses, token usage
- **Custom business metrics**: Intent classification, validation scores
- **Export to Coralogix**: Real-time observability data

## 📈 Performance

- **Latency**: ~900-1200ms (OpenAI API bound)
- **Accuracy**: ~85-90% query translation success
- **Cost**: ~$0.0008 per query
- **Scalability**: Stateless, horizontally scalable

## 🧪 Development

```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run directly  
python3 minimal_dataprime_app.py

# Clean up processes
./cleanup_port.sh
```

## 📝 Classification

**Type**: Natural Language to Domain-Specific Language (NL→DSL) Translation System  
**Pattern**: Few-shot learning with prompt engineering (not RAG, not fine-tuning)  
**Purpose**: Enterprise observability query generation with full telemetry

---

Built with ❤️ for Coralogix Observability | **Fake DataPrime Assistant** 