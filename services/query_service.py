#!/usr/bin/env python3
"""
🧠 Query Service - LLM-powered DataPrime query generation
Handles intent classification and query generation using OpenAI.
"""

import os
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify
from openai import OpenAI
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize tracer and OpenAI client
tracer = trace.get_tracer(__name__)
openai_client = None

app = Flask(__name__)

# Initialize Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

# Initialize shared telemetry configuration

# Initialize Flask instrumentation immediately



# Service stats
query_stats = {
    "queries_generated": 0,
    "intents_classified": 0,
    "openai_calls": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def initialize_openai():
    """Initialize OpenAI client with error handling."""
    global openai_client
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY not found in environment")
            return False
        
        openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize OpenAI client: {e}")
        return False

def extract_trace_context():
    """Extract trace context from request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

def classify_intent(user_input: str):
    """Simple intent classification based on keywords."""
    user_input_lower = user_input.lower()
    
    # Error analysis intent
    if any(word in user_input_lower for word in ['error', 'exception', 'fail', 'crash', 'bug']):
        return {
            "intent": "error_analysis",
            "confidence": 0.85,
            "keywords": ["error", "analysis"]
        }
    
    # Performance analysis intent
    if any(word in user_input_lower for word in ['slow', 'performance', 'latency', 'response time', 'timeout']):
        return {
            "intent": "performance_analysis", 
            "confidence": 0.80,
            "keywords": ["performance", "analysis"]
        }
    
    # Monitoring intent
    if any(word in user_input_lower for word in ['monitor', 'alert', 'dashboard', 'metric']):
        return {
            "intent": "monitoring",
            "confidence": 0.75,
            "keywords": ["monitoring"]
        }
    
    # Default unknown
    return {
        "intent": "unknown",
        "confidence": 0.0,
        "keywords": []
    }

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("query_service.health_check") as span:
        span.set_attribute("service.name", "query_service")
        span.set_attribute("service.version", "1.0.0")
        
        # Add small delay to simulate processing
        time.sleep(0.010)  # 10ms
        
        return jsonify({
            "status": "healthy",
            "service": "query_service",
            "version": "1.0.0",
            "openai_available": openai_client is not None,
            "stats": query_stats,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/generate', methods=['POST'])
def generate_query():
    """Generate DataPrime query from user input."""
    # Extract and set trace context
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    try:
        with tracer.start_as_current_span("query_service.generate_dataprime_query") as span:
            span.set_attribute("service.name", "query_service")
        span.set_attribute("operation.name", "generate_dataprime_query")
        
        try:
            query_stats["queries_generated"] += 1
            
            # Get user input
            data = request.get_json()
            if not data or 'user_input' not in data:
                query_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing user_input"))
                return jsonify({"error": "Missing 'user_input' in request"}), 400
                
            user_input = data['user_input'].strip()
            if not user_input:
                query_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Empty user_input"))
                return jsonify({"error": "Empty user input"}), 400
            
            span.set_attribute("user.input.length", len(user_input))
            span.set_attribute("user.input.query", user_input[:100])
            
            # Add query service processing delay
            time.sleep(0.050)  # 50ms for processing
            
            # Step 1: Intent classification
            with tracer.start_as_current_span("query_service.classify_intent") as intent_span:
                query_stats["intents_classified"] += 1
                intent_info = classify_intent(user_input)
                
                intent_span.set_attribute("intent.type", intent_info["intent"])
                intent_span.set_attribute("intent.confidence", intent_info["confidence"])
                intent_span.set_attribute("intent.keywords_count", len(intent_info["keywords"]))
                
                time.sleep(0.020)  # 20ms for intent processing
            
            # Step 2: Generate query using OpenAI
            with tracer.start_as_current_span("query_service.openai_generation") as openai_span:
                if not openai_client:
                    query_stats["errors"] += 1
                    raise Exception("OpenAI client not available")
                
                query_stats["openai_calls"] += 1
                
                # Choose system prompt based on intent
                if intent_info["intent"] == "error_analysis":
                    system_prompt = """You are an expert in converting error analysis questions into DataPrime query language.

Focus on error detection and analysis patterns. Generate ONLY the query syntax, no explanations.

Use this format:
- source logs [timeframe] | filter [condition] | ...
- Severity levels: 'Debug', 'Info', 'Warn', 'Error', 'Critical'  
- Common fields: $m.severity, $l.subsystemname, $d.response_time, $d.status_code, $d.error_message
- Time formats: last 1h, last 24h, last 1d

Examples:
- "Show errors from last hour" → source logs last 1h | filter $m.severity == 'Error'
- "Count errors by service" → source logs | filter $m.severity == 'Error' | groupby $l.subsystemname aggregate count()
- "Top error messages" → source logs | filter $m.severity == 'Error' | top 10 $d.error_message by count()
"""
                elif intent_info["intent"] == "performance_analysis":
                    system_prompt = """You are an expert in converting performance analysis questions into DataPrime query language.

Focus on performance metrics and slow operations. Generate ONLY the query syntax, no explanations.

Use this format:
- source logs [timeframe] | filter [condition] | ...
- Common fields: $d.response_time, $d.duration, $d.cpu_usage, $d.memory_usage, $l.subsystemname
- Time formats: last 1h, last 24h, last 1d

Examples:
- "Show slow requests" → source logs | filter $d.response_time > 1000 | orderby $d.response_time desc
- "Average response time by service" → source logs | groupby $l.subsystemname aggregate avg($d.response_time)
- "Top slow endpoints" → source logs | top 10 $d.endpoint by $d.response_time
"""
                else:
                    # Default permissive mode
                    system_prompt = """You are an expert in converting any user question into DataPrime query language syntax.

Always generate a query using this format, regardless of the topic:
- source logs [timeframe] | filter [condition] | ...
- source spans [timeframe] | filter [condition] | ...
- Severity levels: 'Debug', 'Info', 'Warn', 'Error', 'Critical'  
- Common fields: $m.severity, $l.subsystemname, $d.response_time, $d.status_code, $d.duration
- Time formats: last 1h, last 24h, last 1d, between timestamps
- Operators: filter, groupby, aggregate, top, bottom, count, countby, orderby, limit

Examples:
- "Show errors from last hour" → source logs last 1h | filter $m.severity == 'Error'
- "Count by service" → source logs | groupby $l.subsystemname aggregate count()
- "Top slow requests" → source logs | top 10 $d.endpoint by $d.duration

Generate ONLY the query syntax, no explanations. Make your best attempt to create a valid DataPrime query for any input.
"""
                
                openai_span.set_attribute("openai.model", "gpt-4o")
                openai_span.set_attribute("openai.max_tokens", 200)
                openai_span.set_attribute("openai.temperature", 0.3)
                
                # Simulate realistic OpenAI response time
                start_time = time.time()
                
                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_input}
                    ],
                    max_tokens=200,
                    temperature=0.3
                )
                
                response_time = time.time() - start_time
                openai_span.set_attribute("openai.response_time_ms", int(response_time * 1000))
                
                generated_query = response.choices[0].message.content.strip()
                openai_span.set_attribute("openai.tokens_used", response.usage.total_tokens if response.usage else 0)
                openai_span.set_attribute("query.generated_length", len(generated_query))
            
            # Prepare response
            result = {
                "success": True,
                "query": generated_query,
                "intent": intent_info["intent"],
                "intent_confidence": intent_info["confidence"],
                "keywords_found": intent_info["keywords"],
                "demo_mode": "permissive",  # Could be made configurable
                "knowledge_base_used": False,  # Simple implementation for now
                "processing_time_ms": int((time.time() * 1000) % 1000),
                "service": "query_service"
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.query_length", len(generated_query))
            span.set_attribute("response.intent", intent_info["intent"])
            
            return jsonify(result)
            
        except Exception as e:
            query_stats["errors"] += 1
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "service": "query_service",
                "timestamp": datetime.now().isoformat()
            }), 500
    finally:
        # Detach the context token
        if token:
            context.detach(token)

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get service statistics."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("query_service.get_stats") as span:
        span.set_attribute("service.name", "query_service")
        
        return jsonify({
            "service": "query_service",
            "stats": query_stats,
            "timestamp": datetime.now().isoformat()
        })

if __name__ == '__main__':
    # Initialize OpenAI client
    if not initialize_openai():
        print("❌ Failed to initialize OpenAI client. Service will have limited functionality.")
    
    # Initialize instrumentation
    
    
    print("🧠 Query Service starting on port 5001...")
    app.run(host='0.0.0.0', port=8011, debug=False)