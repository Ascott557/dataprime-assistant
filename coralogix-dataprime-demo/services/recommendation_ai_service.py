#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Recommendation AI Service - E-commerce Product Recommendations with OpenAI

Uses OpenAI GPT-4-Turbo with custom tool `get_product_data` to provide
personalized product recommendations based on user preferences.

IMPORTANT: Coralogix AI Center handles all evaluations automatically.
This code only structures the OpenAI calls properly using llm-tracekit.
"""

import os
import sys
import json
import time
from datetime import datetime
from flask import Flask, request, jsonify
import requests
from openai import OpenAI
from opentelemetry import trace, metrics, context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.shared_telemetry import ensure_telemetry_initialized

# Initialize telemetry for this service (handles OTLP export to Coralogix)
# Note: shared_telemetry.py already instruments OpenAI with llm-tracekit
# DO NOT instrument OpenAI again here - it causes double instrumentation
telemetry_enabled = ensure_telemetry_initialized()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key or openai_api_key == "your_openai_api_key_here":
    print("❌ OPENAI_API_KEY not configured")
    client = None
else:
    client = OpenAI(api_key=openai_api_key)
    print("✅ OpenAI client initialized")

# Initialize OpenTelemetry
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

# Initialize Flask app
app = Flask(__name__)

# Metrics for tool call tracking
tool_call_success_counter = meter.create_counter(
    "ai.tool_call.success",
    description="Successful tool calls",
    unit="calls"
)

tool_call_failure_counter = meter.create_counter(
    "ai.tool_call.failure",
    description="Failed tool calls",
    unit="calls"
)

tool_call_duration_histogram = meter.create_histogram(
    "ai.tool_call.duration_ms",
    description="Tool call duration in milliseconds",
    unit="ms"
)

# Service URLs
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8014")

# Tool definition for OpenAI
get_product_data_tool = {
    "type": "function",
    "function": {
        "name": "get_product_data",
        "description": "Fetches real-time product catalog from database based on category and price range",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Product category (e.g., 'Wireless Headphones', 'Kitchen', 'Fitness', 'Pet Supplies', 'Office')"
                },
                "price_min": {
                    "type": "number",
                    "description": "Minimum price in USD"
                },
                "price_max": {
                    "type": "number",
                    "description": "Maximum price in USD"
                }
            },
            "required": ["category", "price_min", "price_max"]
        }
    }
}


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "recommendation_ai_service",
        "openai_configured": client is not None,
        "llm_tracekit_enabled": True,  # Instrumented via shared_telemetry.py
        "telemetry_initialized": telemetry_enabled,
        "timestamp": datetime.now().isoformat()
    })


@app.route('/recommendations', methods=['POST'])
def get_recommendations():
    """
    Generate AI recommendations using OpenAI + product data tool.
    
    Request body:
        {
            "user_id": "customer_123",
            "user_context": "Looking for wireless headphones, $50-150 range",
            "category": "Wireless Headphones",  # Optional, can be inferred
            "price_range": [50, 150]  # Optional, can be inferred
        }
    
    Coralogix AI Center will automatically:
    - Capture the full message exchange
    - Calculate Context Adherence score (0.12 when tool fails, 0.95+ when succeeds)
    - Calculate Tool Parameter Correctness (PASSED/FAILED)
    - Calculate Issue Rate (% of calls with problems)
    """
    # Extract trace context from incoming request
    propagator = TraceContextTextMapPropagator()
    ctx = propagator.extract(dict(request.headers))
    
    if not client:
        return jsonify({
            "error": "OpenAI client not configured",
            "recommendations": "Please configure OPENAI_API_KEY"
        }), 500
    
    with tracer.start_as_current_span("ai_recommendation_generation", context=ctx) as span:
        try:
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({"error": "Missing request body"}), 400
            
            user_id = data.get("user_id", "anonymous")
            user_context = data.get("user_context", "")
            
            if not user_context:
                return jsonify({"error": "Missing user_context"}), 400
            
            # Add span attributes for visibility (NOT evaluations - Coralogix does that)
            span.set_attribute("user.id", user_id)
            span.set_attribute("user.context", user_context)
            span.set_attribute("ai.model", "gpt-4-turbo")
            span.set_attribute("ai.tool_available", "get_product_data")
            
            # Initial messages
            messages = [
                {
                    "role": "system",
                    "content": """You are an e-commerce recommendation assistant. Use the get_product_data tool to fetch real-time product information from the database. 

Recommend products that match the user's stated preferences (category, price range, features). 

When you call get_product_data:
1. Parse the user's category preference
2. Parse their price range
3. Call the tool with these exact parameters
4. Use the returned products to make personalized recommendations

If the tool call fails or times out, acknowledge that you cannot access real-time inventory and provide general guidance instead."""
                },
                {
                    "role": "user",
                    "content": f"User preferences: {user_context}"
                }
            ]
            
            # STEP 3: Call OpenAI with tool (llm-tracekit traces this automatically)
            # Mark this as initial phase of the conversation
            print(f"🤖 Calling OpenAI for user: {user_id}")
            span.set_attribute("ai.conversation.phase", "initial_with_tool")
            span.set_attribute("ai.conversation.id", user_id)
            
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                tools=[get_product_data_tool],
                tool_choice="auto"  # Let AI decide if tool is needed
            )
            
            tool_call_success = False
            tool_call_attempted = False
            tool_call_details = []
            
            # Handle tool calls
            if response.choices[0].message.tool_calls:
                tool_call_attempted = True
                span.set_attribute("ai.tool_called", True)
                
                for tool_call in response.choices[0].message.tool_calls:
                    if tool_call.function.name == "get_product_data":
                        args = json.loads(tool_call.function.arguments)
                        
                        # Add span attributes (helps explain failures in traces)
                        span.set_attribute("ai.tool_name", "get_product_data")
                        span.set_attribute("ai.tool_parameters.category", args.get("category", "unknown"))
                        span.set_attribute("ai.tool_parameters.price_min", args.get("price_min", 0))
                        span.set_attribute("ai.tool_parameters.price_max", args.get("price_max", 0))
                        
                        tool_start = time.time()
                        
                        try:
                            # Call Product Service with explicit span for visibility
                            with tracer.start_as_current_span("http.get_product_data") as http_span:
                                http_span.set_attribute("http.method", "GET")
                                http_span.set_attribute("http.url", f"{PRODUCT_SERVICE_URL}/products")
                                http_span.set_attribute("service.name", "product-service")
                                http_span.set_attribute("tool.function", "get_product_data")
                                http_span.set_attribute("tool.parameters.category", args.get("category", "unknown"))
                                http_span.set_attribute("tool.parameters.price_min", args.get("price_min", 0))
                                http_span.set_attribute("tool.parameters.price_max", args.get("price_max", 0))
                                
                                # Inject trace context for downstream service
                                headers = {}
                                TraceContextTextMapPropagator().inject(headers)
                                
                                print(f"🔧 Calling Product Service: category={args.get('category')}, price={args.get('price_min')}-{args.get('price_max')}")
                                
                                product_response = requests.get(
                                    f"{PRODUCT_SERVICE_URL}/products",
                                    params=args,
                                    headers=headers,
                                    timeout=3.0  # 3-second timeout (catches 2950ms DB queries)
                                )
                                
                                http_span.set_attribute("http.status_code", product_response.status_code)
                            
                            tool_duration_ms = (time.time() - tool_start) * 1000
                            tool_call_duration_histogram.record(tool_duration_ms, {
                                "tool": "get_product_data",
                                "status": "success" if product_response.status_code == 200 else "error"
                            })
                            
                            if product_response.status_code == 200:
                                products = product_response.json().get("products", [])
                                tool_call_success = True
                                
                                print(f"✅ Tool call succeeded: {len(products)} products returned")
                                
                                # Add tool result to conversation
                                messages.append({
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [tool_call.model_dump()]
                                })
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps({
                                        "products": products,
                                        "count": len(products),
                                        "category": args.get("category")
                                    })
                                })
                                
                                tool_call_success_counter.add(1, {"tool": "get_product_data"})
                                span.set_attribute("ai.tool_status", "success")
                                span.set_attribute("ai.tool_products_returned", len(products))
                                
                                tool_call_details.append({
                                    "status": "success",
                                    "products_count": len(products),
                                    "duration_ms": round(tool_duration_ms, 2)
                                })
                                
                            else:
                                # Tool call failed (503 from Product Service)
                                tool_call_success = False
                                
                                print(f"❌ Tool call failed: HTTP {product_response.status_code}")
                                
                                tool_call_failure_counter.add(1, {
                                    "tool": "get_product_data",
                                    "reason": "service_error"
                                })
                                
                                # Add error to conversation
                                messages.append({
                                    "role": "assistant",
                                    "content": None,
                                    "tool_calls": [tool_call.model_dump()]
                                })
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": json.dumps({
                                        "error": "Product database unavailable",
                                        "status_code": product_response.status_code,
                                        "note": "Unable to fetch real-time inventory. Please provide general recommendations."
                                    })
                                })
                                
                                span.set_attribute("ai.tool_status", "failed")
                                span.set_attribute("ai.tool_error", f"HTTP {product_response.status_code}")
                                
                                tool_call_details.append({
                                    "status": "failed",
                                    "reason": "service_error",
                                    "duration_ms": round(tool_duration_ms, 2)
                                })
                                
                        except requests.Timeout:
                            # Tool call timeout (Scene 4: get_product_data TIMEOUT)
                            tool_call_success = False
                            tool_duration_ms = (time.time() - tool_start) * 1000
                            
                            print(f"⏱️ Tool call timed out after {tool_duration_ms:.0f}ms")
                            
                            tool_call_duration_histogram.record(tool_duration_ms, {
                                "tool": "get_product_data",
                                "status": "timeout"
                            })
                            
                            tool_call_failure_counter.add(1, {
                                "tool": "get_product_data",
                                "reason": "timeout"
                            })
                            
                            # Add timeout to conversation
                            messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [tool_call.model_dump()]
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({
                                    "error": "Product database timeout after 3000ms",
                                    "note": "Database response took too long. Please provide recommendations based on general product knowledge."
                                })
                            })
                            
                            span.set_attribute("ai.tool_status", "timeout")
                            span.set_attribute("ai.tool_error", "timeout_after_3000ms")
                            span.set_attribute("ai.tool_duration_ms", tool_duration_ms)
                            
                            tool_call_details.append({
                                "status": "timeout",
                                "duration_ms": round(tool_duration_ms, 2)
                            })
                        
                        except Exception as e:
                            # Other errors
                            tool_duration_ms = (time.time() - tool_start) * 1000
                            
                            print(f"❌ Tool call error: {str(e)}")
                            
                            tool_call_failure_counter.add(1, {
                                "tool": "get_product_data",
                                "reason": "exception"
                            })
                            
                            messages.append({
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [tool_call.model_dump()]
                            })
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": json.dumps({
                                    "error": f"Tool execution error: {str(e)}",
                                    "note": "Unable to access product database."
                                })
                            })
                            
                            span.set_attribute("ai.tool_status", "error")
                            span.set_attribute("ai.tool_error", str(e))
                            
                            tool_call_details.append({
                                "status": "error",
                                "error": str(e),
                                "duration_ms": round(tool_duration_ms, 2)
                            })
            else:
                span.set_attribute("ai.tool_called", False)
            
            # Get final AI response (with real data or fallback to training data)
            # This call is within the same parent span to ensure AI Center shows unified conversation
            print(f"🤖 Getting final AI response...")
            
            with tracer.start_as_current_span("ai_final_response") as final_span:
                final_span.set_attribute("ai.conversation.phase", "final_response")
                final_span.set_attribute("ai.tool_call_completed", tool_call_attempted)
                
                final_response = client.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=messages
                )
                
                recommendations_text = final_response.choices[0].message.content
            
            # Add span attributes (helps correlate with evaluations)
            span.set_attribute("ai.tool_call_success", tool_call_success)
            span.set_attribute("ai.fallback_used", not tool_call_success)
            span.set_attribute("ai.response_length", len(recommendations_text))
            span.set_attribute("ai.conversation.complete", True)
            
            # When tool fails, Coralogix evaluations will automatically show:
            # - Context Adherence: 0.12 (low, because AI used training data instead of real products)
            # - Tool Parameter Correctness: FAILED
            # No code needed - Coralogix calculates this server-side
            
            # Get trace ID for response
            trace_id = format(span.get_span_context().trace_id, '032x')
            
            result = {
                "recommendations": recommendations_text,
                "tool_call_attempted": tool_call_attempted,
                "tool_call_success": tool_call_success,
                "tool_call_details": tool_call_details,
                "ai_fallback_used": not tool_call_success,
                "trace_id": trace_id,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"✅ Recommendation generation complete (trace: {trace_id})")
            
            return jsonify(result)
            
        except Exception as e:
            span.record_exception(e)
            span.set_attribute("error", str(e))
            print(f"❌ Error generating recommendations: {e}")
            
            return jsonify({
                "error": str(e),
                "service": "recommendation_ai_service"
            }), 500


if __name__ == '__main__':
    print("🤖 Recommendation AI Service starting on port 8011...")
    print(f"   Telemetry initialized: {telemetry_enabled}")
    print(f"   OpenAI configured: {client is not None}")
    print(f"   llm-tracekit: Instrumented via shared_telemetry.py")
    print(f"   Product Service URL: {PRODUCT_SERVICE_URL}")
    app.run(host='0.0.0.0', port=8011, debug=False)

