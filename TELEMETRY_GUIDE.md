# Distributed Tracing for AI-Powered Applications: A Developer Advocate's Guide

## The AI Observability Challenge

Modern AI applications present unique observability challenges that traditional monitoring approaches struggle to address:

- **Complex User Journeys**: Users interact with AI systems through multiple touchpoints (web UI, voice, API)
- **Asynchronous Processing**: AI inference, feedback collection, and model improvement happen at different times
- **Multi-Modal Interactions**: Voice, text, and structured data flows need correlation
- **Feedback Loops**: User satisfaction directly impacts model performance and requires tracing back to original interactions

This guide demonstrates how to implement distributed tracing for AI applications using the DataPrime Assistant as a real-world example.

## Architecture Overview

Our implementation showcases a **frontend-driven distributed tracing** pattern specifically designed for AI applications:

```
Frontend (JavaScript)          Backend (Python/Flask)           External Services
┌─────────────────────┐       ┌─────────────────────────┐       ┌─────────────────┐
│ User Interaction    │ ────► │ Query Generation        │ ────► │ OpenAI GPT-4o   │
│ (Voice/Text Input)  │       │ (AI Intent Analysis)    │       │ (LLM Inference)  │
└─────────────────────┘       └─────────────────────────┘       └─────────────────┘
           │                             │                              │
           │ W3C Trace Context           │ Child Spans                  │ Auto-Instrumented
           │ (traceparent header)        │ Same Trace ID                │ via llm-tracekit
           ▼                             ▼                              ▼
┌─────────────────────┐       ┌─────────────────────────┐       ┌─────────────────┐
│ Feedback Submission │ ────► │ Database Operations     │ ────► │ SQLite3         │
│ (Thumbs Up/Down)    │       │ (Feedback Storage)      │       │ (Persistence)   │
└─────────────────────┘       └─────────────────────────┘       └─────────────────┘
```

**Key Innovation**: A single trace ID follows the complete user journey from initial query through AI processing to feedback submission, creating perfect correlation for AI Center analysis.

## Implementation Deep Dive

### 1. Frontend Trace Generation (JavaScript)

The frontend creates W3C-compliant trace contexts and propagates them across all API interactions:

```javascript
// Generate W3C-compliant trace ID (32 hex characters)
function generateTraceId() {
    return Array.from({length: 32}, () => 
        Math.floor(Math.random() * 16).toString(16)
    ).join('');
}

// Generate span ID (16 hex characters)
function generateSpanId() {
    return Array.from({length: 16}, () => 
        Math.floor(Math.random() * 16).toString(16)
    ).join('');
}

// Create W3C trace headers for HTTP requests
function createTraceHeaders() {
    if (!currentTraceId) {
        currentTraceId = generateTraceId();
        console.log(`🆕 Created new trace: ${currentTraceId}`);
    }
    
    const spanId = generateSpanId();
    return {
        'traceparent': `00-${currentTraceId}-${spanId}-01`,
        'tracestate': ''
    };
}

// Usage in API calls
const traceHeaders = createTraceHeaders();
const response = await fetch('/api/generate-query', {
    method: 'POST',
    headers: { 
        'Content-Type': 'application/json',
        ...traceHeaders  // Propagate trace context
    },
    body: JSON.stringify({ user_input: userInput })
});
```

**Why This Matters for AI Applications:**
- **User Session Continuity**: Each user interaction maintains the same trace ID
- **Cross-Modal Correlation**: Voice and text inputs share trace context
- **Feedback Attribution**: Thumbs up/down events link back to original AI responses

### 2. Backend Trace Context Extraction (Python/Flask)

The backend extracts W3C trace context from HTTP headers and creates child spans:

```python
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry import trace, context

def extract_trace_context_from_request():
    """Extract W3C trace context from HTTP request headers."""
    try:
        # Get the trace context propagator
        propagator = TraceContextTextMapPropagator()
        
        # Extract context from request headers
        carrier = dict(request.headers)
        context = propagator.extract(carrier)
        
        return context
    except Exception as e:
        print(f"⚠️ Failed to extract trace context: {e}")
        return None

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """Generate DataPrime query with distributed tracing support."""
    # Extract trace context and set as current context
    trace_context = extract_trace_context_from_request()
    if trace_context:
        token = context.attach(trace_context)
    else:
        token = None
    
    try:
        # All operations now happen within the distributed trace
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("🧠 Generate DataPrime Query") as span:
            # Add AI-specific attributes
            span.set_attribute("ai.model", "gpt-4o")
            span.set_attribute("ai.intent", intent_info.get('intent', 'unknown'))
            span.set_attribute("ai.confidence", intent_info.get('confidence', 0.0))
            span.set_attribute("query.complexity", complexity_score)
            
            # Generate AI response
            result = generate_dataprime_query(user_input)
            
            # Return trace ID for frontend correlation
            current_span = trace.get_current_span()
            trace_id = format(current_span.get_span_context().trace_id, '032x')
            result["trace_id"] = trace_id
            
            return jsonify(result)
    
    finally:
        # Clean up context
        if token:
            context.detach(token)
```

**AI-Specific Benefits:**
- **Model Performance Tracking**: Each AI inference is traced with model metadata
- **Intent Analysis Correlation**: User intent confidence scores are captured
- **Query Complexity Metrics**: Generated query complexity is tracked for optimization

### 3. Feedback Correlation (The AI Center Secret Sauce)

The most critical aspect for AI applications is correlating user feedback with the original AI interaction:

```python
@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """Submit user feedback with perfect trace correlation."""
    # Extract the SAME trace context from feedback request
    trace_context = extract_trace_context_from_request()
    if trace_context:
        token = context.attach(trace_context)
    else:
        token = None
    
    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("👍 Submit User Feedback") as span:
            # Add feedback-specific attributes
            span.set_attribute("feedback.type", data['feedback_type'])
            span.set_attribute("feedback.session_id", data['session_id'])
            span.set_attribute("feedback.correlated", True)
            
            # Store feedback with trace correlation
            feedback_id = store_feedback_in_database(data, trace_id)
            
            print(f"✅ Feedback received: {data['feedback_type']} for session {data['session_id']} (correlated with {trace_id})")
            
            return jsonify({
                "success": True,
                "feedback_id": feedback_id,
                "trace_id": trace_id,
                "correlated": True
            })
    
    finally:
        if token:
            context.detach(token)
```

**The Result**: In Coralogix AI Center, you see:
- **Single Trace View**: Complete user journey from query → AI processing → feedback
- **Perfect Attribution**: Every thumbs up/down links to the exact AI response
- **Performance Correlation**: Model latency directly connected to user satisfaction

## Telemetry Stack Configuration

### Required Dependencies

```python
# requirements.txt
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-instrumentation-flask>=0.48b0
opentelemetry-instrumentation-sqlite3>=0.48b0
llm-tracekit>=0.1.0  # Coralogix AI-specific instrumentation
```

### Initialization Sequence (Critical Order!)

```python
def initialize_telemetry():
    """Initialize telemetry with proper instrumentation order."""
    try:
        # 1. Setup Coralogix export FIRST
        from llm_tracekit import OpenAIInstrumentor, setup_export_to_coralogix
        setup_export_to_coralogix(
            service_name="dataprime_assistant",
            application_name="ai-dataprime", 
            subsystem_name="query-generator",
            coralogix_token=os.getenv('CX_TOKEN'),
            coralogix_endpoint=os.getenv('CX_ENDPOINT'),
            capture_content=True  # Essential for AI Center analysis
        )
        
        # 2. Instrument AI/LLM calls
        OpenAIInstrumentor().instrument()
        
        # 3. Instrument database operations
        SQLite3Instrumentor().instrument()
        
        # 4. Flask instrumentation happens AFTER app creation
        return True
    except Exception as e:
        print(f"❌ Telemetry setup failed: {e}")
        return False

# Application initialization
telemetry_enabled = initialize_telemetry()
app = Flask(__name__)

# 5. Instrument Flask app LAST
if telemetry_enabled:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
```

**Why This Order Matters:**
- Coralogix export must be configured before any instrumentation
- LLM instrumentation needs to be active before AI calls
- Database instrumentation must precede any DB operations
- Flask instrumentation requires the app object to exist

## Span Naming Strategy for AI Applications

Instead of generic HTTP span names, use business-meaningful names that tell the AI story:

```python
# ❌ Generic (technical)
POST /api/generate-query
POST /api/feedback
INSERT sqlite

# ✅ AI-Meaningful (business)
🧠 Generate DataPrime Query
👍 Submit User Feedback  
💾 Store Feedback Data
🤖 OpenAI Query Generation
📊 Intent Analysis
```

**Implementation:**
```python
# Use descriptive span names
with tracer.start_as_current_span("🧠 Generate DataPrime Query") as span:
    span.set_attribute("ai.operation", "query_generation")
    span.set_attribute("ai.model", "gpt-4o")
    
with tracer.start_as_current_span("📊 Analyze User Intent") as span:
    span.set_attribute("ai.intent.detected", intent)
    span.set_attribute("ai.intent.confidence", confidence)
    
with tracer.start_as_current_span("👍 Process User Feedback") as span:
    span.set_attribute("feedback.sentiment", "positive" if thumbs_up else "negative")
```

## Key Attributes for AI Center Analysis

Coralogix AI Center becomes incredibly powerful when you add the right attributes:

```python
# AI Model Attributes
span.set_attribute("ai.model.name", "gpt-4o")
span.set_attribute("ai.model.version", "2024-05-13")
span.set_attribute("ai.model.provider", "openai")
span.set_attribute("ai.model.temperature", 0.7)

# User Intent Attributes  
span.set_attribute("ai.intent.category", "error_analysis")
span.set_attribute("ai.intent.confidence", 0.85)
span.set_attribute("ai.intent.keywords", ["errors", "database", "timeout"])

# Query Generation Attributes
span.set_attribute("query.language", "dataprime")
span.set_attribute("query.complexity_score", 0.6)
span.set_attribute("query.validation_status", "PASS")
span.set_attribute("query.execution_time_ms", 1250)

# Feedback Correlation Attributes
span.set_attribute("feedback.type", "thumbs_up")
span.set_attribute("feedback.session_duration_seconds", 45)
span.set_attribute("feedback.user_satisfaction", "high")
span.set_attribute("correlation.original_trace_id", original_trace_id)
```

**AI Center Benefits:**
- **Model Performance Trends**: Track accuracy and latency by model version
- **Intent Recognition Analysis**: Monitor confidence scores and misclassifications  
- **User Satisfaction Correlation**: Connect feedback directly to model parameters
- **Query Quality Metrics**: Analyze complexity vs. user satisfaction

## Testing Your Distributed Tracing

### Manual Testing Script

```bash
#!/bin/bash
# Test complete distributed tracing flow

TRACE_ID="12345678901234567890123456789012"

echo "🧪 Testing Query Generation..."
QUERY_RESPONSE=$(curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-${TRACE_ID}-1111222233334444-01" \
  -d '{"user_input": "Show me authentication errors"}')

echo "Query Response: $QUERY_RESPONSE"
RETURNED_TRACE_ID=$(echo $QUERY_RESPONSE | jq -r '.trace_id')

echo "🧪 Testing Feedback Submission..."
FEEDBACK_RESPONSE=$(curl -s -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-${TRACE_ID}-5555666677778888-01" \
  -d '{
    "session_id": "test-correlation",
    "feedback_type": "thumbs_up", 
    "user_input": "Show me authentication errors",
    "query_text": "source logs | filter $m.severity == \"Error\""
  }')

echo "Feedback Response: $FEEDBACK_RESPONSE"
FEEDBACK_TRACE_ID=$(echo $FEEDBACK_RESPONSE | jq -r '.trace_id')

echo "🔍 Trace Correlation Check:"
echo "  Query Trace ID:    $RETURNED_TRACE_ID"
echo "  Feedback Trace ID: $FEEDBACK_TRACE_ID"

if [ "$RETURNED_TRACE_ID" = "$FEEDBACK_TRACE_ID" ]; then
    echo "✅ SUCCESS: Traces are perfectly correlated!"
else
    echo "❌ FAILURE: Trace correlation broken"
fi
```

## Error Path Demonstration: Real-World Observability

The true value of distributed tracing emerges when things go wrong. Let's intentionally trigger error scenarios to demonstrate how traces help with troubleshooting.

### 1. OpenAI API Failures

**Scenario**: OpenAI API timeout or rate limiting

```python
# Enhanced error handling in query generation
@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    trace_context = extract_trace_context_from_request()
    if trace_context:
        token = context.attach(trace_context)
    else:
        token = None
    
    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("🧠 Generate DataPrime Query") as span:
            try:
                # Add timeout and retry attributes
                span.set_attribute("ai.timeout_seconds", 30)
                span.set_attribute("ai.max_retries", 3)
                
                # This will fail if OpenAI is down or rate limited
                result = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    timeout=30
                )
                
                span.set_attribute("ai.response.success", True)
                span.set_attribute("ai.response.tokens", result.usage.total_tokens)
                
            except openai.APITimeoutError as e:
                span.record_exception(e)
                span.set_attribute("ai.error.type", "timeout")
                span.set_attribute("ai.error.duration_seconds", 30)
                span.set_status(trace.Status(trace.StatusCode.ERROR, "OpenAI API timeout"))
                
                return jsonify({
                    "error": "AI service temporarily unavailable",
                    "error_type": "timeout",
                    "trace_id": format(span.get_span_context().trace_id, '032x'),
                    "retry_after_seconds": 60
                }), 503
                
            except openai.RateLimitError as e:
                span.record_exception(e)
                span.set_attribute("ai.error.type", "rate_limit")
                span.set_attribute("ai.error.retry_after", e.retry_after if hasattr(e, 'retry_after') else 60)
                span.set_status(trace.Status(trace.StatusCode.ERROR, "OpenAI rate limit exceeded"))
                
                return jsonify({
                    "error": "Too many requests - please try again later",
                    "error_type": "rate_limit", 
                    "trace_id": format(span.get_span_context().trace_id, '032x'),
                    "retry_after_seconds": getattr(e, 'retry_after', 60)
                }), 429
                
            except Exception as e:
                span.record_exception(e)
                span.set_attribute("ai.error.type", "unknown")
                span.set_status(trace.Status(trace.StatusCode.ERROR, f"Unexpected AI error: {str(e)}"))
                
                return jsonify({
                    "error": "Internal AI processing error",
                    "error_type": "unknown",
                    "trace_id": format(span.get_span_context().trace_id, '032x')
                }), 500
                
    finally:
        if token:
            context.detach(token)
```

**Testing Error Scenarios**:

```bash
#!/bin/bash
# Test OpenAI API failures

echo "🔥 Testing OpenAI Timeout Scenario..."
# Simulate network issues by using invalid endpoint
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-error123456789012345678901234-1111222233334444-01" \
  -d '{"user_input": "This will timeout"}' | jq

echo "🔥 Testing Rate Limit Scenario..."
# Send rapid requests to trigger rate limiting
for i in {1..10}; do
  curl -s -X POST http://localhost:8000/api/generate-query \
    -H "Content-Type: application/json" \
    -H "traceparent: 00-ratelimit78901234567890123456-$(printf "%016d" $i)-01" \
    -d '{"user_input": "Rapid request '$i'"}' &
done
wait
```

### 2. Database Connection Failures

**Scenario**: SQLite database locked or corrupted

```python
# Enhanced database error handling
def _process_feedback(data, span, original_trace_id):
    try:
        # Add database operation attributes
        span.set_attribute("db.operation", "INSERT")
        span.set_attribute("db.table", "feedback")
        span.set_attribute("db.connection_timeout", 30)
        
        conn = sqlite3.connect('feedback.db', timeout=30)
        cursor = conn.cursor()
        
        # This might fail if database is locked
        cursor.execute('''
            INSERT INTO feedback (session_id, query_text, user_input, feedback_type, trace_id, span_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['session_id'],
            data['query_text'], 
            data['user_input'],
            data['feedback_type'],
            trace_id,
            span_id
        ))
        
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        span.set_attribute("db.rows_affected", 1)
        span.set_attribute("db.feedback_id", feedback_id)
        span.set_attribute("db.success", True)
        
        return jsonify({
            "success": True,
            "feedback_id": feedback_id,
            "trace_id": trace_id
        })
        
    except sqlite3.OperationalError as e:
        span.record_exception(e)
        span.set_attribute("db.error.type", "operational")
        span.set_attribute("db.error.locked", "database is locked" in str(e).lower())
        span.set_status(trace.Status(trace.StatusCode.ERROR, f"Database error: {str(e)}"))
        
        if "database is locked" in str(e).lower():
            return jsonify({
                "success": False,
                "error": "Database temporarily unavailable - high load",
                "error_type": "database_locked",
                "trace_id": trace_id,
                "retry_suggested": True
            }), 503
        else:
            return jsonify({
                "success": False,
                "error": "Database operation failed",
                "error_type": "database_error", 
                "trace_id": trace_id
            }), 500
            
    except Exception as e:
        span.record_exception(e)
        span.set_attribute("db.error.type", "unknown")
        span.set_status(trace.Status(trace.StatusCode.ERROR, f"Unexpected database error: {str(e)}"))
        
        return jsonify({
            "success": False,
            "error": "Internal database error",
            "error_type": "unknown",
            "trace_id": trace_id
        }), 500
```

**Testing Database Errors**:

```bash
#!/bin/bash
# Test database failure scenarios

echo "🔥 Testing Database Lock Scenario..."
# Create multiple concurrent feedback submissions
TRACE_ID="dblock1234567890123456789012345"

for i in {1..20}; do
  curl -s -X POST http://localhost:8000/api/feedback \
    -H "Content-Type: application/json" \
    -H "traceparent: 00-${TRACE_ID}-$(printf "%016d" $i)-01" \
    -d '{
      "session_id": "concurrent-test-'$i'",
      "feedback_type": "thumbs_up",
      "user_input": "Concurrent test",
      "query_text": "test query"
    }' &
done
wait

echo "🔥 Testing Database Corruption Recovery..."
# Temporarily corrupt the database file (be careful!)
# mv feedback.db feedback.db.backup
# echo "corrupted" > feedback.db

curl -s -X POST http://localhost:8000/api/feedback \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-corrupt567890123456789012345678-1111222233334444-01" \
  -d '{
    "session_id": "corruption-test",
    "feedback_type": "thumbs_down", 
    "user_input": "This should fail",
    "query_text": "corrupted test"
  }' | jq

# Restore database
# mv feedback.db.backup feedback.db
```

### 3. Context Propagation Failures

**Scenario**: Trace context gets lost or corrupted

```python
# Enhanced context validation
def extract_trace_context_from_request():
    """Extract W3C trace context with comprehensive error handling."""
    try:
        propagator = TraceContextTextMapPropagator()
        carrier = dict(request.headers)
        
        # Validate traceparent format
        traceparent = request.headers.get('traceparent', '')
        if traceparent:
            # W3C traceparent format: 00-{trace_id}-{span_id}-{flags}
            parts = traceparent.split('-')
            if len(parts) != 4:
                print(f"⚠️ Invalid traceparent format: {traceparent}")
                return None
                
            version, trace_id, span_id, flags = parts
            
            # Validate each component
            if version != '00':
                print(f"⚠️ Unsupported traceparent version: {version}")
                return None
                
            if len(trace_id) != 32 or not all(c in '0123456789abcdef' for c in trace_id.lower()):
                print(f"⚠️ Invalid trace_id format: {trace_id}")
                return None
                
            if len(span_id) != 16 or not all(c in '0123456789abcdef' for c in span_id.lower()):
                print(f"⚠️ Invalid span_id format: {span_id}")
                return None
                
            if trace_id == '0' * 32:
                print(f"⚠️ Invalid trace_id: all zeros")
                return None
                
            if span_id == '0' * 16:
                print(f"⚠️ Invalid span_id: all zeros") 
                return None
        
        context = propagator.extract(carrier)
        
        # Additional validation - check if context was actually extracted
        if context and hasattr(context, 'get'):
            span_context = trace.get_current_span(context).get_span_context()
            if span_context.trace_id == 0:
                print(f"⚠️ Context extraction failed - no valid trace context")
                return None
                
        return context
        
    except Exception as e:
        print(f"⚠️ Context extraction error: {e}")
        return None
```

**Testing Context Failures**:

```bash
#!/bin/bash
# Test trace context corruption scenarios

echo "🔥 Testing Invalid Trace Context Formats..."

# Invalid version
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 01-12345678901234567890123456789012-1111222233334444-01" \
  -d '{"user_input": "Invalid version test"}' | jq

# Invalid trace ID (too short)
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-1234567890123456789012345678901-1111222233334444-01" \
  -d '{"user_input": "Short trace ID test"}' | jq

# Invalid span ID (non-hex characters)
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-12345678901234567890123456789012-11112222333344gg-01" \
  -d '{"user_input": "Invalid span ID test"}' | jq

# All-zero trace ID (invalid)
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-00000000000000000000000000000000-1111222233334444-01" \
  -d '{"user_input": "Zero trace ID test"}' | jq

# Malformed traceparent (missing parts)
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-12345678901234567890123456789012-1111222233334444" \
  -d '{"user_input": "Malformed header test"}' | jq
```

### 4. Cascade Failure Demonstration

**Scenario**: How failures propagate through the distributed trace

```python
# Enhanced error propagation tracking
@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    trace_context = extract_trace_context_from_request()
    if trace_context:
        token = context.attach(trace_context)
    else:
        token = None
    
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("🧠 Generate DataPrime Query") as main_span:
        try:
            # Step 1: Intent Analysis (might fail)
            with tracer.start_as_current_span("📊 Analyze User Intent") as intent_span:
                try:
                    intent_result = analyze_intent(user_input)
                    intent_span.set_attribute("intent.success", True)
                    intent_span.set_attribute("intent.category", intent_result.get('intent', 'unknown'))
                except Exception as e:
                    intent_span.record_exception(e)
                    intent_span.set_status(trace.Status(trace.StatusCode.ERROR, "Intent analysis failed"))
                    intent_span.set_attribute("intent.success", False)
                    # Continue with fallback intent
                    intent_result = {"intent": "general", "confidence": 0.0}
            
            # Step 2: OpenAI Query Generation (might fail)
            with tracer.start_as_current_span("🤖 OpenAI Query Generation") as ai_span:
                try:
                    ai_result = call_openai_api(user_input, intent_result)
                    ai_span.set_attribute("ai.success", True)
                    ai_span.set_attribute("ai.tokens", ai_result.get('tokens', 0))
                except Exception as e:
                    ai_span.record_exception(e)
                    ai_span.set_status(trace.Status(trace.StatusCode.ERROR, "OpenAI generation failed"))
                    ai_span.set_attribute("ai.success", False)
                    
                    # This failure should propagate up
                    main_span.set_status(trace.Status(trace.StatusCode.ERROR, "Query generation pipeline failed"))
                    raise e
            
            # Step 3: Query Validation (might fail)
            with tracer.start_as_current_span("✅ Validate Generated Query") as validation_span:
                try:
                    validation_result = validate_dataprime_query(ai_result['query'])
                    validation_span.set_attribute("validation.success", True)
                    validation_span.set_attribute("validation.score", validation_result.get('score', 0))
                except Exception as e:
                    validation_span.record_exception(e)
                    validation_span.set_status(trace.Status(trace.StatusCode.ERROR, "Query validation failed"))
                    validation_span.set_attribute("validation.success", False)
                    
                    # Mark main span as degraded (partial success)
                    main_span.set_attribute("pipeline.degraded", True)
                    main_span.add_event("Query validation failed - returning unvalidated result")
            
            # Success path
            main_span.set_attribute("pipeline.success", True)
            main_span.set_attribute("pipeline.steps_completed", 3)
            
            return jsonify({
                "query": ai_result['query'],
                "intent": intent_result,
                "validation": validation_result,
                "trace_id": format(main_span.get_span_context().trace_id, '032x'),
                "pipeline_health": "healthy"
            })
            
        except Exception as e:
            # Top-level error handling
            main_span.record_exception(e)
            main_span.set_status(trace.Status(trace.StatusCode.ERROR, f"Pipeline failed: {str(e)}"))
            main_span.set_attribute("pipeline.success", False)
            main_span.set_attribute("pipeline.failure_point", identify_failure_point(e))
            
            return jsonify({
                "error": "Query generation failed",
                "trace_id": format(main_span.get_span_context().trace_id, '032x'),
                "pipeline_health": "failed",
                "failure_point": identify_failure_point(e)
            }), 500
            
        finally:
            if token:
                context.detach(token)

def identify_failure_point(error):
    """Identify where in the pipeline the failure occurred."""
    error_str = str(error).lower()
    if "intent" in error_str:
        return "intent_analysis"
    elif "openai" in error_str or "api" in error_str:
        return "ai_generation"
    elif "validation" in error_str:
        return "query_validation"
    else:
        return "unknown"
```

**Testing Cascade Failures**:

```bash
#!/bin/bash
# Test how failures cascade through the system

echo "🔥 Testing Complete Pipeline Failure..."
TRACE_ID="cascade123456789012345678901234"

# This should show failure propagating through all spans
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-${TRACE_ID}-1111222233334444-01" \
  -d '{"user_input": ""}' | jq  # Empty input should trigger failures

echo "🔥 Testing Partial Failure (Degraded Mode)..."
TRACE_ID="degraded12345678901234567890123"

# This should show some steps succeeding, others failing
curl -s -X POST http://localhost:8000/api/generate-query \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-${TRACE_ID}-2222333344445555-01" \
  -d '{"user_input": "show me some complex query that might partially fail"}' | jq
```

### Expected Error Traces in Coralogix

When errors occur, Coralogix shows incredibly valuable troubleshooting information:

**1. OpenAI API Timeout Trace:**
```
Trace ID: error123456789012345678901234
├── 🧠 Generate DataPrime Query (30.5s) ❌ ERROR
│   ├── 📊 Analyze User Intent (0.1s) ✅ OK
│   ├── 🤖 OpenAI Query Generation (30.0s) ❌ TIMEOUT
│   │   └── Exception: APITimeoutError: Request timed out
│   └── ✅ Validate Generated Query (SKIPPED)
└── Attributes:
    - ai.error.type: "timeout"
    - ai.error.duration_seconds: 30
    - pipeline.failure_point: "ai_generation"
```

**2. Database Lock Cascade:**
```
Trace ID: dblock1234567890123456789012345
├── 🧠 Generate DataPrime Query (0.2s) ✅ OK
│   └── Query: "source logs | filter..."
├── 👍 Submit User Feedback (5.0s) ❌ ERROR
│   ├── 💾 Store Feedback Data (5.0s) ❌ DATABASE_LOCKED
│   │   └── Exception: OperationalError: database is locked
│   └── Attributes:
│       - db.error.type: "operational"
│       - db.error.locked: true
│       - retry_suggested: true
└── Impact: User feedback lost, retry needed
```

**3. Context Propagation Failure:**
```
Trace ID: 00000000000000000000000000000000 (Invalid)
├── ⚠️ Context Validation Failed
│   └── Warning: "Invalid trace_id: all zeros"
├── 🧠 Generate DataPrime Query (NEW TRACE) ⚠️
│   └── Trace ID: f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6
└── 👍 Submit User Feedback (NEW TRACE) ⚠️
    └── Trace ID: a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6
```

**Key Benefits of Error Tracing:**

1. **Root Cause Analysis**: See exactly where failures occur
2. **Impact Assessment**: Understand how errors affect user experience  
3. **Recovery Guidance**: Automatic retry suggestions and degraded mode handling
4. **Performance Correlation**: Connect errors to system load and timing
5. **Context Preservation**: Maintain trace correlation even during partial failures

### Error Monitoring Dashboards

Create Coralogix dashboards to monitor error patterns:

```sql
-- AI Service Health Dashboard
source spans 
| filter $d.ai exists
| stats 
    count() as total_requests,
    countif($m.status_code == 'ERROR') as failed_requests,
    avg($d.duration) as avg_duration_ms
  by $d.ai.error.type, $d.ai.model
| extend success_rate = (total_requests - failed_requests) / total_requests * 100
| sort success_rate asc

-- Database Performance Under Load  
source spans
| filter $d.db exists
| stats 
    count() as operations,
    countif($d.db.error.locked == true) as lock_conflicts,
    max($d.duration) as max_duration_ms
  by bin($timestamp, 1m)
| extend lock_rate = lock_conflicts / operations * 100
| where lock_rate > 5  -- Alert when > 5% operations are locked

-- Context Propagation Health
source spans
| filter $d.correlation exists  
| stats 
    count() as total_operations,
    countif($d.correlation.success == false) as propagation_failures
  by bin($timestamp, 5m)
| extend failure_rate = propagation_failures / total_operations * 100
| where failure_rate > 1  -- Alert when > 1% context propagation fails
```

### Error Recovery Patterns

**Automatic Retry with Exponential Backoff:**

```python
import time
import random
from functools import wraps

def retry_with_tracing(max_retries=3, base_delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            span = trace.get_current_span()
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                        span.add_event(f"Retrying after {delay:.1f}s (attempt {attempt + 1})")
                        time.sleep(delay)
                    
                    span.set_attribute("retry.attempt", attempt + 1)
                    span.set_attribute("retry.max_attempts", max_retries + 1)
                    
                    result = func(*args, **kwargs)
                    
                    if attempt > 0:
                        span.add_event(f"Retry succeeded on attempt {attempt + 1}")
                        span.set_attribute("retry.succeeded", True)
                    
                    return result
                    
                except Exception as e:
                    span.set_attribute(f"retry.attempt_{attempt + 1}.error", str(e))
                    
                    if attempt == max_retries:
                        span.set_attribute("retry.exhausted", True)
                        span.add_event("All retry attempts exhausted")
                        raise
                    else:
                        span.add_event(f"Attempt {attempt + 1} failed: {str(e)}")
            
        return wrapper
    return decorator

# Usage
@retry_with_tracing(max_retries=3, base_delay=2)
def call_openai_with_retry(messages):
    return openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        timeout=30
    )
```

**Circuit Breaker Pattern:**

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func, *args, **kwargs):
        span = trace.get_current_span()
        span.set_attribute("circuit_breaker.state", self.state.value)
        span.set_attribute("circuit_breaker.failure_count", self.failure_count)
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                span.add_event("Circuit breaker transitioning to HALF_OPEN")
            else:
                span.set_attribute("circuit_breaker.rejected", True)
                raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = func(*args, **kwargs)
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                span.add_event("Circuit breaker recovered - state: CLOSED")
                
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                span.add_event(f"Circuit breaker OPENED after {self.failure_count} failures")
            
            span.set_attribute("circuit_breaker.failure_triggered", True)
            raise

# Usage
openai_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

def call_openai_with_circuit_breaker(messages):
    return openai_circuit_breaker.call(
        openai_client.chat.completions.create,
        model="gpt-4o",
        messages=messages,
        timeout=30
    )
```

## Demo Features: Interactive Performance Testing

The DataPrime Assistant includes built-in demo features to showcase distributed tracing capabilities:

### Keyboard Shortcuts for Live Demos

**Ctrl+S**: Toggle between Smart/Permissive modes
- Demonstrates configuration changes with tracing
- Shows how feature flags can be traced

**Ctrl+D**: Create slow MCP span  
- Simulates slow external service calls
- Perfect for demonstrating external dependency tracking

**Ctrl+B**: Slow database operation demo ⭐ **NEW**
- Simulates realistic database performance issues
- Creates detailed spans showing:
  - Connection pool exhaustion (0.8s wait)
  - Slow query execution (2.7s with full table scan)
  - Result processing overhead (0.5s)

### Slow Database Demo Details

When you press **Ctrl+B**, the system creates a comprehensive trace showing:

```
Slow Database Demo (4.0s total)
├── Database Connection (0.8s)
│   ├── Event: "Waiting for available connection..."
│   └── Event: "Connection acquired from pool"
├── Complex Analytics Query (2.7s)
│   ├── Event: "Starting full table scan..."
│   ├── Event: "Processing aggregations..."
│   ├── Event: "Sorting results..."
│   └── Event: "Query completed"
└── Result Processing (0.5s)
    ├── Event: "Processing complex calculations..."
    └── Event: "Processing completed"
```

**Span Attributes Added:**
- `demo.type`: "slow_database"
- `demo.purpose`: "performance_analysis" 
- `db.operation`: "SELECT"
- `db.using_index`: false
- `db.rows_examined`: 50000
- `db.performance_issue`: true
- `db.optimization_needed`: true

**API Endpoint:** `POST /api/demo/slow-db`
- Supports distributed tracing via `traceparent` headers
- Returns performance analysis and optimization recommendations
- Perfect for demonstrating how tracing identifies bottlenecks

### Demo Script Usage

```bash
# Test the slow database demo programmatically
curl -X POST http://localhost:8000/api/demo/slow-db \
  -H "Content-Type: application/json" \
  -H "traceparent: 00-12345678901234567890123456789012-1111222233334444-01"

# Expected response includes:
# - Detailed performance breakdown
# - Optimization recommendations  
# - Actual query results
# - Trace ID for Coralogix analysis
```

### Expected Coralogix Results

When working correctly, you should see in Coralogix:

**Single Trace View:**
```
Trace ID: 12345678901234567890123456789012
├── 🧠 Generate DataPrime Query (200ms)
│   ├── 📊 Analyze User Intent (50ms)  
│   ├── 🤖 OpenAI Query Generation (120ms)
│   └── ✅ Validate Generated Query (30ms)
├── 👍 Submit User Feedback (15ms)
│   └── 💾 Store Feedback Data (10ms)
└── 🔗 Database Operations (5ms)
```

**Span Attributes Available for Analysis:**
- `ai.model.name = "gpt-4o"`
- `ai.intent.category = "error_analysis"`
- `feedback.type = "thumbs_up"`
- `correlation.success = true`

## Common Pitfalls and Solutions

### 1. Context Propagation Failures

**Problem**: Trace context gets lost between frontend and backend.

```javascript
// ❌ Missing trace headers
fetch('/api/generate-query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
});

// ✅ Proper trace propagation
const traceHeaders = createTraceHeaders();
fetch('/api/generate-query', {
    method: 'POST',  
    headers: { 
        'Content-Type': 'application/json',
        ...traceHeaders  // Include W3C trace context
    },
    body: JSON.stringify(data)
});
```

### 2. Instrumentation Order Issues

**Problem**: Instrumentation libraries conflict when initialized in wrong order.

```python
# ❌ Wrong order - Flask instrumented before telemetry setup
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)  # Too early!
initialize_telemetry()  # Too late!

# ✅ Correct order
initialize_telemetry()  # Setup export and base instrumentation
app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)  # After app creation
```

### 3. Missing AI-Specific Attributes

**Problem**: Generic spans don't provide AI insights.

```python
# ❌ Generic span with no AI context
with tracer.start_span("process_request"):
    result = openai_client.chat.completions.create(...)

# ✅ AI-enriched span with meaningful attributes  
with tracer.start_span("🧠 Generate DataPrime Query") as span:
    span.set_attribute("ai.model", "gpt-4o")
    span.set_attribute("ai.intent", intent_category)
    span.set_attribute("ai.user_input", user_query)
    result = openai_client.chat.completions.create(...)
    span.set_attribute("ai.response_quality", calculate_quality(result))
```

## Performance Considerations

### Sampling Strategy for AI Applications

AI applications generate high trace volumes. Use intelligent sampling:

```python
# Environment-based sampling
sampling_rate = {
    'development': 1.0,    # 100% - trace everything during development
    'staging': 0.1,        # 10% - representative sample for testing
    'production': 0.01     # 1% - cost-effective production monitoring
}.get(os.getenv('ENVIRONMENT'), 0.01)

# AI-aware sampling (higher rate for feedback events)
def should_sample_trace(operation_name):
    if 'feedback' in operation_name.lower():
        return random.random() < 0.1  # 10% for feedback correlation
    elif 'error' in operation_name.lower():
        return random.random() < 0.5  # 50% for error analysis  
    else:
        return random.random() < sampling_rate
```

### Attribute Optimization

Balance observability with performance:

```python
# ✅ Essential attributes only
span.set_attribute("ai.model", model_name)
span.set_attribute("ai.intent", intent)
span.set_attribute("feedback.type", feedback_type)

# ❌ Avoid high-cardinality attributes
span.set_attribute("user.full_query", full_user_input)  # Too much data
span.set_attribute("timestamp.exact_ms", precise_timestamp)  # Redundant
```

## Integration with Coralogix AI Center

### Leveraging AI Center Features

1. **Model Performance Dashboards**: Use `ai.model.*` attributes for automatic model monitoring
2. **Intent Analysis Widgets**: `ai.intent.*` attributes power intent recognition analytics  
3. **Feedback Correlation Views**: `correlation.*` attributes enable satisfaction analysis
4. **Cost Attribution**: Trace AI operations to understand per-query costs

### Custom Dashboards and Alerts

```sql
-- Coralogix DataPrime queries for AI monitoring

-- Model performance by version
source spans 
| filter $d.ai.model.name == 'gpt-4o'
| stats avg($d.duration), count() by $d.ai.model.version
| sort avg_duration desc

-- User satisfaction by intent category  
source spans
| filter $d.feedback.type exists
| stats 
    count() as total_feedback,
    countif($d.feedback.type == 'thumbs_up') as positive_feedback
  by $d.ai.intent.category
| extend satisfaction_rate = positive_feedback / total_feedback * 100
| sort satisfaction_rate desc

-- Trace correlation health
source spans  
| filter $d.correlation exists
| stats 
    count() as total_operations,
    countif($d.correlation.success == true) as successful_correlations
| extend correlation_rate = successful_correlations / total_operations * 100
```

## Conclusion: The AI Observability Advantage

This distributed tracing implementation provides unprecedented visibility into AI application behavior:

**For Developers:**
- **Complete User Journey Visibility**: See exactly how users interact with your AI
- **Performance Optimization**: Identify bottlenecks in AI processing pipelines
- **Quality Assurance**: Monitor model accuracy and user satisfaction in real-time

**For Product Teams:**
- **User Experience Insights**: Understand which AI responses delight vs. frustrate users
- **Feature Impact Analysis**: Measure how AI improvements affect user satisfaction
- **Cost Optimization**: Track AI usage costs per user interaction

**For AI/ML Teams:**
- **Model Performance Monitoring**: Real-time feedback on model quality
- **Intent Recognition Accuracy**: Track and improve natural language understanding
- **Feedback Loop Optimization**: Accelerate model improvement cycles

By implementing distributed tracing thoughtfully, you transform your AI application from a black box into a transparent, optimizable, and continuously improving system. The investment in proper observability pays dividends in faster debugging, better user experiences, and more effective AI model development.

The future of AI applications is observable, traceable, and data-driven. Start building that future today.

---

*This guide demonstrates production-ready distributed tracing patterns using the DataPrime Assistant as a reference implementation. All code examples are battle-tested and optimized for Coralogix AI Center integration.*


