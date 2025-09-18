#!/usr/bin/env python3
"""
Copyright (c) 2024 Coralogix Ltd.

Licensed under the MIT License. See LICENSE file in the project root
for full license information.

This file is part of the Coralogix DataPrime AI Assistant Demo.
"""


"""
⚙️ Processing Service - Background data processing and analysis
Handles complex processing tasks, analytics, and data transformation.
"""

import os
import json
import time
import random
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

# Initialize shared telemetry configuration

# Service stats
processing_stats = {
    "tasks_processed": 0,
    "analysis_completed": 0,
    "transformations_applied": 0,
    "processing_time_total_ms": 0,
    "errors": 0,
    "start_time": datetime.now()
}

def extract_trace_context():
    """Extract trace context from request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

def analyze_query_complexity(query: str):
    """Analyze the complexity of a DataPrime query."""
    complexity_metrics = {
        "operator_count": 0,
        "field_references": 0,
        "aggregation_functions": 0,
        "time_constraints": 0,
        "complexity_level": "simple"
    }
    
    query_lower = query.lower()
    
    # Count operators
    operators = ['filter', 'groupby', 'aggregate', 'top', 'bottom', 'orderby', 'limit', 'choose']
    for op in operators:
        complexity_metrics["operator_count"] += query_lower.count(op)
    
    # Count field references
    import re
    field_pattern = r'\$[mld]\.[a-zA-Z_][a-zA-Z0-9_]*'
    complexity_metrics["field_references"] = len(re.findall(field_pattern, query))
    
    # Count aggregation functions
    agg_functions = ['count', 'sum', 'avg', 'min', 'max']
    for func in agg_functions:
        complexity_metrics["aggregation_functions"] += query_lower.count(func)
    
    # Check for time constraints
    time_patterns = ['last', 'between', 'since', 'until']
    for pattern in time_patterns:
        if pattern in query_lower:
            complexity_metrics["time_constraints"] += 1
    
    # Determine complexity level
    total_complexity = (
        complexity_metrics["operator_count"] * 2 +
        complexity_metrics["field_references"] +
        complexity_metrics["aggregation_functions"] * 3 +
        complexity_metrics["time_constraints"]
    )
    
    if total_complexity >= 10:
        complexity_metrics["complexity_level"] = "complex"
    elif total_complexity >= 5:
        complexity_metrics["complexity_level"] = "moderate"
    else:
        complexity_metrics["complexity_level"] = "simple"
    
    return complexity_metrics

def generate_performance_insights(query_data):
    """Generate performance insights and recommendations."""
    insights = {
        "performance_score": 0.0,
        "recommendations": [],
        "optimizations": [],
        "estimated_execution_time_ms": 0
    }
    
    query = query_data.get("generated_query", "")
    validation = query_data.get("validation_result", {})
    
    # Base performance score from validation
    syntax_score = validation.get("syntax_score", 0.5)
    insights["performance_score"] = syntax_score * 0.8
    
    # Analyze query patterns for performance
    query_lower = query.lower()
    
    # Check for performance anti-patterns
    if "groupby" in query_lower and "limit" not in query_lower:
        insights["recommendations"].append("Consider adding LIMIT to prevent large result sets")
        insights["performance_score"] -= 0.1
    
    if "source logs" in query_lower and "last" not in query_lower:
        insights["recommendations"].append("Add time constraints to improve query performance")
        insights["performance_score"] -= 0.15
    
    if query_lower.count("filter") == 0:
        insights["recommendations"].append("Add filters to reduce data processing overhead")
        insights["performance_score"] -= 0.1
    
    # Check for optimization opportunities
    if "$m.severity" in query:
        insights["optimizations"].append("Severity filtering is well-optimized")
        insights["performance_score"] += 0.05
    
    if "top " in query_lower or "bottom " in query_lower:
        insights["optimizations"].append("Top/bottom queries are efficiently processed")
        insights["performance_score"] += 0.05
    
    # Estimate execution time based on complexity
    complexity_score = validation.get("complexity_score", 0.3)
    base_time = 100  # Base 100ms
    complexity_multiplier = 1 + (complexity_score * 2)
    insights["estimated_execution_time_ms"] = int(base_time * complexity_multiplier)
    
    # Ensure score is between 0 and 1
    insights["performance_score"] = max(0.0, min(1.0, insights["performance_score"]))
    
    return insights

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("processing_service.health_check") as span:
        span.set_attribute("service.component", "processing_service")
        span.set_attribute("service.version", "1.0.0")
        
        # Add small delay to simulate processing
        time.sleep(0.020)  # 20ms
        
        return jsonify({
            "status": "healthy",
            "service": "processing_service",
            "version": "1.0.0",
            "stats": processing_stats,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/process', methods=['POST'])
def process_data():
    """Process query data and generate insights."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("processing_service.process_query_data") as span:
        span.set_attribute("service.component", "processing_service")
        span.set_attribute("operation.name", "process_query_data")
        
        try:
            start_time = time.time()
            processing_stats["tasks_processed"] += 1
            
            # Get processing data
            data = request.get_json()
            if not data:
                processing_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing processing data"))
                return jsonify({"error": "Missing processing data"}), 400
            
            user_input = data.get("user_input", "")
            generated_query = data.get("generated_query", "")
            validation_result = data.get("validation_result", {})
            
            span.set_attribute("processing.user_input_length", len(user_input))
            span.set_attribute("processing.query_length", len(generated_query))
            span.set_attribute("processing.validation_score", validation_result.get("syntax_score", 0))
            
            # Add realistic processing delay based on complexity
            complexity_score = validation_result.get("complexity_score", 0.3)
            processing_delay = 0.100 + (complexity_score * 0.150)  # 100-250ms
            time.sleep(processing_delay)
            
            # Step 1: Query complexity analysis
            with tracer.start_as_current_span("processing_service.analyze_complexity") as complexity_span:
                complexity_analysis = analyze_query_complexity(generated_query)
                
                complexity_span.set_attribute("complexity.level", complexity_analysis["complexity_level"])
                complexity_span.set_attribute("complexity.operator_count", complexity_analysis["operator_count"])
                complexity_span.set_attribute("complexity.field_references", complexity_analysis["field_references"])
                
                processing_stats["analysis_completed"] += 1
                time.sleep(0.030)  # 30ms for complexity analysis
            
            # Step 2: Performance insights generation
            with tracer.start_as_current_span("processing_service.generate_insights") as insights_span:
                performance_insights = generate_performance_insights(data)
                
                insights_span.set_attribute("insights.performance_score", performance_insights["performance_score"])
                insights_span.set_attribute("insights.recommendations_count", len(performance_insights["recommendations"]))
                insights_span.set_attribute("insights.optimizations_count", len(performance_insights["optimizations"]))
                insights_span.set_attribute("insights.estimated_execution_ms", performance_insights["estimated_execution_time_ms"])
                
                time.sleep(0.040)  # 40ms for insights generation
            
            # Step 3: Data transformation and enrichment
            with tracer.start_as_current_span("processing_service.transform_data") as transform_span:
                # Simulate data transformation
                enriched_data = {
                    "original_query": generated_query,
                    "optimized_suggestions": [],
                    "metadata_enrichment": {
                        "query_category": complexity_analysis["complexity_level"],
                        "processing_priority": "high" if complexity_analysis["complexity_level"] == "complex" else "normal",
                        "cache_eligible": "last" in generated_query.lower(),
                        "resource_intensive": complexity_analysis["operator_count"] > 3
                    }
                }
                
                # Add optimization suggestions based on analysis
                if complexity_analysis["operator_count"] > 5:
                    enriched_data["optimized_suggestions"].append("Consider breaking complex query into simpler parts")
                
                if complexity_analysis["field_references"] > 10:
                    enriched_data["optimized_suggestions"].append("Reduce field references for better performance")
                
                transform_span.set_attribute("transform.suggestions_added", len(enriched_data["optimized_suggestions"]))
                transform_span.set_attribute("transform.cache_eligible", enriched_data["metadata_enrichment"]["cache_eligible"])
                
                processing_stats["transformations_applied"] += 1
                time.sleep(0.025)  # 25ms for transformation
            
            # Step 4: Store insights for future analysis (simulate storage call)
            with tracer.start_as_current_span("processing_service.store_insights") as storage_span:
                # Simulate storage operation
                import requests
                
                try:
                    headers = {}
                    propagator = TraceContextTextMapPropagator()
                    propagator.inject(headers)
                    
                    storage_data = {
                        "type": "processing_insights",
                        "user_input": user_input,
                        "query": generated_query,
                        "complexity_analysis": complexity_analysis,
                        "performance_insights": performance_insights,
                        "enriched_data": enriched_data,
                        "processed_at": datetime.now().isoformat()
                    }
                    
                    storage_response = requests.post(
                        "http://localhost:8015/store",
                        json=storage_data,
                        headers=headers,
                        timeout=5
                    )
                    
                    if storage_response.status_code == 200:
                        storage_span.set_attribute("storage.success", True)
                        storage_span.add_event("insights_stored", {"record_id": storage_response.json().get("id", "")})
                    else:
                        storage_span.set_attribute("storage.success", False)
                        storage_span.add_event("storage_failed", {"error": storage_response.text})
                        
                except Exception as e:
                    storage_span.add_event("storage_error", {"error": str(e)})
                
                time.sleep(0.015)  # 15ms for storage operation
            
            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)
            processing_stats["processing_time_total_ms"] += processing_time
            
            # Prepare final response
            result = {
                "success": True,
                "processing_id": str(hash(f"{user_input}_{generated_query}_{datetime.now().isoformat()}"))[:16],
                "complexity_analysis": complexity_analysis,
                "performance_insights": performance_insights,
                "enriched_data": enriched_data,
                "processing_time_ms": processing_time,
                "processed_at": datetime.now().isoformat(),
                "service": "processing_service"
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.processing_time_ms", processing_time)
            span.set_attribute("response.complexity_level", complexity_analysis["complexity_level"])
            
            return jsonify(result)
            
        except Exception as e:
            processing_stats["errors"] += 1
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "service": "processing_service",
                "timestamp": datetime.now().isoformat()
            }), 500
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
    
    with tracer.start_as_current_span("processing_service.get_stats") as span:
        span.set_attribute("service.component", "processing_service")
        
        # Calculate average processing time
        avg_processing_time = 0
        if processing_stats["tasks_processed"] > 0:
            avg_processing_time = processing_stats["processing_time_total_ms"] / processing_stats["tasks_processed"]
        
        enhanced_stats = dict(processing_stats)
        enhanced_stats["average_processing_time_ms"] = round(avg_processing_time, 2)
        
        return jsonify({
            "service": "processing_service",
            "stats": enhanced_stats,
            "timestamp": datetime.now().isoformat()
        })

if __name__ == '__main__':
    # Initialize instrumentation
    
    
    print("⚙️ Processing Service starting on port 5004...")
    app.run(host='0.0.0.0', port=8014, debug=False)