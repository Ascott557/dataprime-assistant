# 🚀 Coralogix DataPrime AI Assistant Demo

A complete distributed AI assistant that demonstrates Coralogix's AI Center capabilities with OpenTelemetry tracing, DataPrime query generation, and real-time observability.

## ✨ Features

- **🤖 AI-Powered Query Generation**: Convert natural language to DataPrime queries
- **📊 Distributed Tracing**: Complete OpenTelemetry instrumentation across 8 microservices
- **🔍 Coralogix AI Center Integration**: Content evaluation, safety policies, and monitoring
- **💬 Interactive Feedback System**: 5-star rating system with trace correlation
- **🏗️ Microservices Architecture**: Production-ready distributed system
- **🐳 Docker Support**: One-command deployment with Docker Compose

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │───▶│   API Gateway    │───▶│ Query Service   │
│   (Port 8020)   │    │   (Port 8010)    │    │   (Port 8011)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Storage Service │    │Validation Service│    │Processing Service│
│   (Port 8015)   │    │   (Port 8012)    │    │   (Port 8014)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│External API Svc │    │   Queue Service  │    │Queue Worker Svc │
│   (Port 8016)   │    │   (Port 8013)    │    │   (Port 8017)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API Key
- Coralogix Account with AI Center enabled

> 📋 **All configuration is handled via a single `.env` file** - see `.env.example` for required variables!

### 1. Clone and Setup

```bash
git clone <repository-url>
cd coralogix-dataprime-demo
```

### 2. Configure Environment

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

**Required Environment Variables** (edit `.env` file):

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Coralogix Configuration  
CX_TOKEN=your_coralogix_send_data_key_here
CX_DOMAIN=eu2.coralogix.com
CX_APPLICATION_NAME=dataprime-demo
CX_SUBSYSTEM_NAME=ai-assistant
```

### 🌍 **Coralogix Regional Configuration**

**IMPORTANT**: Set `CX_DOMAIN` to match your Coralogix region. The demo uses the new regional endpoints as per [Coralogix's updated endpoint structure](https://coralogix.com/blog/everything-you-need-to-know-about-the-new-coralogix-endpoints/).

| **Region** | **CX_DOMAIN Value** | **Description** |
|------------|-------------------|-----------------|
| 🇺🇸 **US East (Ohio)** | `us1.coralogix.com` | Primary US region |
| 🇺🇸 **US West (Oregon)** | `us2.coralogix.com` | West Coast US |
| 🇮🇪 **EU West (Ireland)** | `eu1.coralogix.com` | Primary EU region |
| 🇸🇪 **EU North (Stockholm)** | `eu2.coralogix.com` | **Default** - Nordic region |
| 🇮🇳 **Asia Pacific (Mumbai)** | `ap1.coralogix.com` | India region |
| 🇸🇬 **Asia Pacific (Singapore)** | `ap2.coralogix.com` | Southeast Asia |
| 🇮🇩 **Asia Pacific (Jakarta)** | `ap3.coralogix.com` | Indonesia region |

**How to find your region**: Check your Coralogix team URL. For example:
- `my-team.eu2.coralogix.com` → Use `CX_DOMAIN=eu2.coralogix.com`
- `my-team.us1.coralogix.com` → Use `CX_DOMAIN=us1.coralogix.com`

> 💡 **Quick Setup**: The `.env.example` file contains all required variables with placeholder values. Simply replace the placeholder values with your actual API keys and correct regional domain.

### 3. Launch with Docker

```bash
cd docker
docker-compose up -d
```

### 4. Access the Demo

- **Frontend**: http://localhost:8020
- **API Gateway**: http://localhost:8010
- **Health Check**: http://localhost:8010/api/health

## 🎯 Demo Usage

### 1. Generate DataPrime Queries

Navigate to http://localhost:8020 and try these example queries:

```
Show me errors from the last hour
Find slow database queries
Count logs by service
What are the top error messages?
Show me frontend errors
Display API response times
```

### 2. Rate Queries

After each query generation, use the 5-star feedback system:
- 👎 (1 star) - Poor
- 😐 (2 stars) - Fair  
- 👍 (3 stars) - Good
- 😊 (4 stars) - Very Good
- 🌟 (5 stars) - Excellent

### 3. Monitor in Coralogix

1. **View Traces**: Go to Coralogix → APM → Traces
2. **AI Center**: Check AI Center → Evaluations for content analysis
3. **Logs**: See structured logs from all microservices
4. **Metrics**: Monitor system performance and AI usage

## 🔍 Coralogix AI Center Features Demonstrated

### Content Evaluation
- **Allowed Topics**: Configurable topic validation
- **Content Safety**: Automatic content moderation
- **Quality Scoring**: AI response quality assessment

### Observability
- **Token Usage**: Track OpenAI API consumption
- **Response Times**: Monitor AI processing latency
- **Error Tracking**: Capture and analyze failures
- **User Feedback**: Correlation with trace data

### Compliance
- **Data Privacy**: Secure handling of user inputs
- **Audit Trail**: Complete request/response logging
- **Policy Enforcement**: Configurable content policies

## 🛠️ Development

### Local Development (without Docker)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment**:
   ```bash
   source .env
   ```

3. **Start Services**:
   ```bash
   python app/distributed_app.py
   ```

4. **Start Frontend** (in another terminal):
   ```bash
   python app/distributed_frontend.py
   ```

### Service Endpoints

| Service | Port | Health Check |
|---------|------|--------------|
| API Gateway | 8010 | `/api/health` |
| Query Service | 8011 | `/health` |
| Validation Service | 8012 | `/health` |
| Queue Service | 8013 | `/health` |
| Processing Service | 8014 | `/health` |
| Storage Service | 8015 | `/health` |
| External API Service | 8016 | `/health` |
| Queue Worker Service | 8017 | `/health` |
| Frontend | 8020 | `/health` |

## 📊 Monitoring & Observability

### Key Metrics to Watch
- **Request Latency**: End-to-end query processing time
- **AI Token Usage**: OpenAI API consumption
- **Error Rates**: Service failure percentages  
- **Feedback Scores**: User satisfaction ratings
- **Trace Completion**: Distributed tracing coverage

### Coralogix Dashboards
The demo automatically creates traces and logs that populate:
- Service dependency maps
- Performance dashboards  
- Error tracking views
- AI usage analytics
- User feedback correlation

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key for AI features | Required |
| `CX_TOKEN` | Coralogix Send Data API key | Required |
| `CX_DOMAIN` | Coralogix domain | `eu2.coralogix.com` |
| `CX_APPLICATION_NAME` | Application name in Coralogix | `dataprime-demo` |
| `CX_SUBSYSTEM_NAME` | Subsystem name in Coralogix | `ai-assistant` |

### AI Center Configuration

To fully demo AI Center features:

1. **Enable AI Center** in your Coralogix account
2. **Configure Allowed Topics**: Add terms like `dataprime`, `frontend`, `errors`, `logs`
3. **Set Evaluation Policies**: Configure content safety rules
4. **Create Dashboards**: Monitor AI usage and performance

## 🐛 Troubleshooting

### Common Issues

**Services won't start**:
- Check environment variables are set
- Ensure ports 8010-8020 are available
- Verify Docker has sufficient resources

**AI Center not working**:
- Confirm AI Center is enabled in Coralogix
- Check CX_TOKEN has proper permissions
- Verify domain configuration

**No traces appearing**:
- Check Coralogix token and domain
- Ensure services can reach Coralogix endpoints
- Verify OpenTelemetry configuration

### Logs and Debugging

```bash
# View service logs
docker-compose logs -f dataprime-demo

# Check individual service health
curl http://localhost:8010/api/health

# Monitor traces
curl http://localhost:8010/api/stats
```

## 🔧 Troubleshooting

### Telemetry Data Not Appearing in Coralogix

If you're not seeing telemetry data in Coralogix:

1. **Check Regional Endpoint**: Ensure `CX_DOMAIN` matches your Coralogix region
   ```bash
   # Verify your current setting
   curl -s http://localhost:8010/api/health | jq .telemetry_initialized
   ```

2. **Verify Correct Endpoint Mapping**: The demo automatically maps domains to ingress endpoints:
   - `eu2.coralogix.com` → `https://ingress.eu2.coralogix.com:443`
   - `us1.coralogix.com` → `https://ingress.us1.coralogix.com:443`
   - See [Coralogix endpoint documentation](https://coralogix.com/blog/everything-you-need-to-know-about-the-new-coralogix-endpoints/) for all regions

3. **Test Telemetry Generation**:
   ```bash
   # Generate a test query and check trace ID
   curl -X POST http://localhost:8010/api/generate-query \
     -H "Content-Type: application/json" \
     -d '{"user_input": "test query", "user_id": "test"}'
   ```

4. **Check Coralogix AI Center**: Look for:
   - Application: `dataprime-demo`
   - Subsystem: `ai-assistant`
   - Data may take 2-5 minutes to appear

### Legacy Domain Support

The demo supports legacy domains but automatically redirects to new endpoints:
- `coralogix.com` → `ingress.eu1.coralogix.com:443`
- `coralogix.us` → `ingress.us1.coralogix.com:443`
- `coralogix.in` → `ingress.ap1.coralogix.com:443`

**Recommendation**: Use the new regional domains for best performance and future compatibility.

## 🤝 Contributing

This demo showcases Coralogix AI Center capabilities. To contribute:

1. Fork the repository
2. Create a feature branch
3. Test with your Coralogix environment  
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues with:
- **Demo setup**: Open a GitHub issue
- **Coralogix features**: Contact Coralogix support
- **AI Center**: Check Coralogix documentation

---

**Built with ❤️ to showcase the power of Coralogix AI Center**
