#!/usr/bin/env python3
"""
🔧 Create Simple Working Services
Create minimal working versions of all services that focus on the core functionality.
"""

import os

def create_api_gateway():
    """Create a simple API Gateway service."""
    content = '''#!/usr/bin/env python3
"""
🌐 API Gateway Service - Simple working version
"""

import os
import time
import requests
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Initialize tracer
tracer = trace.get_tracer(__name__)
app = Flask(__name__)

# Service endpoints
QUERY_SERVICE_URL = "http://localhost:8011"
VALIDATION_SERVICE_URL = "http://localhost:8012"

# Initialize Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

# Stats tracking
gateway_stats = {
    "requests_processed": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def propagate_trace_context(headers=None):
    """Inject current trace context into headers for downstream services."""
    if headers is None:
        headers = {}
    
    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for the API Gateway."""
    with tracer.start_as_current_span("api_gateway.health_check") as span:
        span.set_attribute("service.name", "api_gateway")
        span.set_attribute("service.version", "1.0.0")
        
        time.sleep(0.005)  # 5ms
        
        return jsonify({
            "status": "healthy",
            "service": "api_gateway",
            "version": "1.0.0",
            "stats": gateway_stats,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/api/generate-query', methods=['POST'])
def generate_query():
    """Main endpoint for query generation - orchestrates the full pipeline."""
    # Extract incoming trace context
    propagator = TraceContextTextMapPropagator()
    incoming_context = propagator.extract(dict(request.headers))
    
    token = None
    if incoming_context:
        token = context.attach(incoming_context)
    
    try:
        with tracer.start_as_current_span("api_gateway.generate_query_pipeline") as span:
            span.set_attribute("service.name", "api_gateway")
            span.set_attribute("operation.name", "generate_query_pipeline")
            
            gateway_stats["requests_processed"] += 1
            
            # Get user input
            data = request.get_json()
            if not data or 'user_input' not in data:
                gateway_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing user_input"))
                return jsonify({"error": "Missing 'user_input' in request"}), 400
                
            user_input = data['user_input'].strip()
            if not user_input:
                gateway_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Empty user_input"))
                return jsonify({"error": "Empty user input"}), 400
            
            span.set_attribute("user.input.length", len(user_input))
            span.set_attribute("user.input.query", user_input[:100])
            
            time.sleep(0.008)  # 8ms gateway processing
            
            # Step 1: Generate query via Query Service
            with tracer.start_as_current_span("api_gateway.call_query_service") as query_span:
                headers = propagate_trace_context()
                
                query_response = requests.post(
                    f"{QUERY_SERVICE_URL}/generate",
                    json={"user_input": user_input},
                    headers=headers,
                    timeout=30
                )
                
                if query_response.status_code != 200:
                    raise Exception(f"Query service error: {query_response.text}")
                
                query_result = query_response.json()
                query_span.set_attribute("query.generated", query_result.get("query", "")[:100])
                query_span.set_attribute("query.intent", query_result.get("intent", "unknown"))
            
            # Step 2: Validate query via Validation Service
            with tracer.start_as_current_span("api_gateway.call_validation_service") as validation_span:
                headers = propagate_trace_context()
                
                validation_response = requests.post(
                    f"{VALIDATION_SERVICE_URL}/validate",
                    json={"query": query_result.get("query", "")},
                    headers=headers,
                    timeout=10
                )
                
                if validation_response.status_code != 200:
                    raise Exception(f"Validation service error: {validation_response.text}")
                
                validation_result = validation_response.json()
                validation_span.set_attribute("validation.is_valid", validation_result.get("is_valid", False))
                validation_span.set_attribute("validation.score", validation_result.get("syntax_score", 0))
            
            # Combine results
            final_result = {
                "success": True,
                "query": query_result.get("query", ""),
                "intent": query_result.get("intent", "unknown"),
                "intent_confidence": query_result.get("intent_confidence", 0.0),
                "validation": validation_result,
                "demo_mode": "permissive",
                "services_called": ["query_service", "validation_service"]
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.query_length", len(final_result["query"]))
            
            return jsonify(final_result)
            
    except Exception as e:
        gateway_stats["errors"] += 1
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "api_gateway"
        }), 500
    
    finally:
        if token:
            context.detach(token)

if __name__ == '__main__':
    print("🌐 API Gateway starting on port 8010...")
    app.run(host='0.0.0.0', port=8010, debug=False)
'''
    
    with open('services/api_gateway.py', 'w') as f:
        f.write(content)
    print("✅ Created simple API Gateway")

def create_query_service():
    """Create a simple Query Service."""
    content = '''#!/usr/bin/env python3
"""
🧠 Query Service - Simple working version
"""

import os
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
app = Flask(__name__)

# Initialize Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

# Initialize OpenAI client
openai_client = None
try:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        openai_client = OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
except Exception as e:
    print(f"❌ Failed to initialize OpenAI client: {e}")

# Service stats
query_stats = {
    "queries_generated": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def extract_trace_context():
    """Extract trace context from request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    with tracer.start_as_current_span("query_service.health_check") as span:
        span.set_attribute("service.name", "query_service")
        
        time.sleep(0.010)  # 10ms
        
        return jsonify({
            "status": "healthy",
            "service": "query_service",
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
            
            query_stats["queries_generated"] += 1
            
            # Get user input
            data = request.get_json()
            if not data or 'user_input' not in data:
                query_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing user_input"))
                return jsonify({"error": "Missing 'user_input' in request"}), 400
                
            user_input = data['user_input'].strip()
            span.set_attribute("user.input.length", len(user_input))
            
            time.sleep(0.050)  # 50ms processing
            
            # Simple intent classification
            intent = "unknown"
            confidence = 0.5
            if "error" in user_input.lower():
                intent = "error_analysis"
                confidence = 0.85
            elif "slow" in user_input.lower() or "performance" in user_input.lower():
                intent = "performance_analysis"
                confidence = 0.80
            
            # Generate query using OpenAI
            if openai_client:
                with tracer.start_as_current_span("query_service.openai_generation") as openai_span:
                    system_prompt = """You are an expert in converting questions into DataPrime query language.

Generate ONLY the query syntax, no explanations. Use this format:
- source logs [timeframe] | filter [condition] | ...
- Severity levels: 'Debug', 'Info', 'Warn', 'Error', 'Critical'  
- Common fields: $m.severity, $l.subsystemname, $d.response_time
- Time formats: last 1h, last 24h, last 1d

Examples:
- "Show errors from last hour" → source logs last 1h | filter $m.severity == 'Error'
- "Count by service" → source logs | groupby $l.subsystemname aggregate count()
"""
                    
                    # Simulate realistic OpenAI response time
                    time.sleep(0.800)  # 800ms for LLM call
                    
                    response = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_input}
                        ],
                        max_tokens=200,
                        temperature=0.3
                    )
                    
                    generated_query = response.choices[0].message.content.strip()
                    openai_span.set_attribute("openai.tokens_used", response.usage.total_tokens if response.usage else 0)
            else:
                # Fallback query generation
                generated_query = "source logs last 1h | filter $m.severity == 'Error'"
            
            result = {
                "success": True,
                "query": generated_query,
                "intent": intent,
                "intent_confidence": confidence,
                "service": "query_service"
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.query_length", len(generated_query))
            
            return jsonify(result)
            
    except Exception as e:
        query_stats["errors"] += 1
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "query_service"
        }), 500
    
    finally:
        if token:
            context.detach(token)

if __name__ == '__main__':
    print("🧠 Query Service starting on port 8011...")
    app.run(host='0.0.0.0', port=8011, debug=False)
'''
    
    with open('services/query_service.py', 'w') as f:
        f.write(content)
    print("✅ Created simple Query Service")

def create_validation_service():
    """Create a simple Validation Service."""
    content = '''#!/usr/bin/env python3
"""
✅ Validation Service - Simple working version
"""

import time
import re
from datetime import datetime
from flask import Flask, request, jsonify
from opentelemetry import trace, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Initialize tracer
tracer = trace.get_tracer(__name__)
app = Flask(__name__)

# Initialize Flask instrumentation
try:
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    FlaskInstrumentor().instrument_app(app)
except ImportError:
    pass

# Service stats
validation_stats = {
    "queries_validated": 0,
    "valid_queries": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def extract_trace_context():
    """Extract trace context from request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

def validate_dataprime_syntax(query: str):
    """Simple DataPrime syntax validation."""
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "syntax_score": 0.0
    }
    
    query_lower = query.lower().strip()
    
    # Check if query starts with source
    if re.search(r"source\s+(logs|spans|metrics)", query_lower):
        validation_result["syntax_score"] += 0.4
    else:
        validation_result["is_valid"] = False
        validation_result["warnings"].append("Query must start with 'source logs', 'source spans', or 'source metrics'")
    
    # Check for operators
    operators = ['filter', 'groupby', 'aggregate', 'top', 'orderby']
    operator_count = sum(1 for op in operators if op in query_lower)
    validation_result["syntax_score"] += min(0.4, operator_count * 0.1)
    
    # Check for field references
    field_count = len(re.findall(r'\\$[mld]\\.[a-zA-Z_][a-zA-Z0-9_]*', query))
    validation_result["syntax_score"] += min(0.2, field_count * 0.05)
    
    validation_result["syntax_score"] = min(1.0, validation_result["syntax_score"])
    
    if validation_result["syntax_score"] < 0.3:
        validation_result["is_valid"] = False
    
    return validation_result

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    with tracer.start_as_current_span("validation_service.health_check") as span:
        span.set_attribute("service.name", "validation_service")
        
        time.sleep(0.015)  # 15ms
        
        return jsonify({
            "status": "healthy",
            "service": "validation_service",
            "stats": validation_stats,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/validate', methods=['POST'])
def validate_query():
    """Validate DataPrime query syntax."""
    # Extract and set trace context
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    try:
        with tracer.start_as_current_span("validation_service.validate_dataprime_query") as span:
            span.set_attribute("service.name", "validation_service")
            span.set_attribute("operation.name", "validate_dataprime_query")
            
            validation_stats["queries_validated"] += 1
            
            # Get query to validate
            data = request.get_json()
            if not data or 'query' not in data:
                validation_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing query"))
                return jsonify({"error": "Missing 'query' in request"}), 400
                
            query = data['query'].strip()
            span.set_attribute("query.length", len(query))
            
            time.sleep(0.075)  # 75ms for validation
            
            # Perform validation
            validation_result = validate_dataprime_syntax(query)
            
            if validation_result["is_valid"]:
                validation_stats["valid_queries"] += 1
            
            span.set_attribute("validation.is_valid", validation_result["is_valid"])
            span.set_attribute("validation.syntax_score", validation_result["syntax_score"])
            
            result = {
                "success": True,
                "is_valid": validation_result["is_valid"],
                "syntax_score": validation_result["syntax_score"],
                "warnings": validation_result["warnings"],
                "service": "validation_service"
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.is_valid", validation_result["is_valid"])
            
            return jsonify(result)
            
    except Exception as e:
        validation_stats["errors"] += 1
        if 'span' in locals():
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
        
        return jsonify({
            "success": False,
            "error": str(e),
            "service": "validation_service"
        }), 500
    
    finally:
        if token:
            context.detach(token)

if __name__ == '__main__':
    print("✅ Validation Service starting on port 8012...")
    app.run(host='0.0.0.0', port=8012, debug=False)
'''
    
    with open('services/validation_service.py', 'w') as f:
        f.write(content)
    print("✅ Created simple Validation Service")

def main():
    """Create all simple working services."""
    print("🔧 Creating Simple Working Services")
    print("=" * 40)
    
    # Create services directory if it doesn't exist
    os.makedirs('services', exist_ok=True)
    
    create_api_gateway()
    create_query_service()
    create_validation_service()
    
    print("\n✅ All simple services created!")
    print("🚀 Ready to test distributed system with proper tracing")

if __name__ == '__main__':
    main()
'''
