#!/usr/bin/env python3
"""
✅ Validation Service - DataPrime query validation and enhancement
Validates query syntax, checks for common patterns, and provides suggestions.
"""

import os
import json
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

# Initialize shared telemetry configuration

# Service stats
validation_stats = {
    "queries_validated": 0,
    "valid_queries": 0,
    "invalid_queries": 0,
    "warnings_issued": 0,
    "errors": 0,
    "start_time": datetime.now()
}

# DataPrime validation patterns
DATAPRIME_PATTERNS = {
    "source_patterns": [
        r"source\s+logs",
        r"source\s+spans", 
        r"source\s+metrics"
    ],
    "operator_patterns": [
        r"\|\s*filter",
        r"\|\s*groupby",
        r"\|\s*aggregate",
        r"\|\s*top\s+\d+",
        r"\|\s*bottom\s+\d+",
        r"\|\s*orderby",
        r"\|\s*limit\s+\d+",
        r"\|\s*count",
        r"\|\s*choose"
    ],
    "field_patterns": [
        r"\$m\.[a-zA-Z_][a-zA-Z0-9_]*",  # Metadata fields
        r"\$l\.[a-zA-Z_][a-zA-Z0-9_]*",  # Label fields
        r"\$d\.[a-zA-Z_][a-zA-Z0-9_]*"   # Data fields
    ],
    "time_patterns": [
        r"last\s+\d+[hmsd]",
        r"last\s+\d+\s+(hour|hours|minute|minutes|second|seconds|day|days)",
        r"between\s+\d{4}-\d{2}-\d{2}.*and.*\d{4}-\d{2}-\d{2}"
    ]
}

def extract_trace_context():
    """Extract trace context from request headers."""
    propagator = TraceContextTextMapPropagator()
    return propagator.extract(dict(request.headers))

def validate_dataprime_syntax(query: str):
    """Comprehensive DataPrime syntax validation."""
    validation_result = {
        "is_valid": True,
        "warnings": [],
        "errors": [],
        "syntax_score": 0.0,
        "complexity_score": 0.0,
        "suggestions": []
    }
    
    # Normalize query for analysis
    query_lower = query.lower().strip()
    
    # Check if query starts with source
    has_source = False
    for pattern in DATAPRIME_PATTERNS["source_patterns"]:
        if re.search(pattern, query_lower):
            has_source = True
            validation_result["syntax_score"] += 0.3
            break
    
    if not has_source:
        validation_result["errors"].append("Query must start with 'source logs', 'source spans', or 'source metrics'")
        validation_result["is_valid"] = False
        validation_result["suggestions"].append("Start your query with 'source logs' or 'source spans'")
    
    # Check for pipe operators
    operator_count = 0
    for pattern in DATAPRIME_PATTERNS["operator_patterns"]:
        matches = re.findall(pattern, query_lower)
        operator_count += len(matches)
    
    if operator_count > 0:
        validation_result["syntax_score"] += min(0.4, operator_count * 0.1)
        validation_result["complexity_score"] = min(1.0, operator_count * 0.2)
    else:
        validation_result["warnings"].append("Query lacks operators like filter, groupby, or aggregate")
        validation_result["suggestions"].append("Consider adding operators like '| filter' or '| groupby' to refine your query")
    
    # Check for field references
    field_count = 0
    for pattern in DATAPRIME_PATTERNS["field_patterns"]:
        matches = re.findall(pattern, query)
        field_count += len(matches)
    
    if field_count > 0:
        validation_result["syntax_score"] += min(0.3, field_count * 0.05)
    else:
        validation_result["warnings"].append("Query doesn't reference specific fields ($m, $l, or $d)")
        validation_result["suggestions"].append("Use field references like $m.severity, $l.subsystemname, or $d.response_time")
    
    # Check for time constraints
    has_time = False
    for pattern in DATAPRIME_PATTERNS["time_patterns"]:
        if re.search(pattern, query_lower):
            has_time = True
            validation_result["syntax_score"] += 0.1
            break
    
    if not has_time:
        validation_result["warnings"].append("Query lacks time constraints")
        validation_result["suggestions"].append("Consider adding time constraints like 'last 1h' or 'last 24h'")
    
    # Check for common syntax issues
    if "==" not in query and "!=" not in query and ">" not in query and "<" not in query:
        if "filter" in query_lower:
            validation_result["warnings"].append("Filter operator found but no comparison operators")
            validation_result["suggestions"].append("Use comparison operators like ==, !=, >, < in filter conditions")
    
    # Check for severity level format
    severity_levels = ["debug", "info", "warn", "warning", "error", "critical"]
    for level in severity_levels:
        if level in query_lower and f"'{level}'" not in query_lower and f'"{level}"' not in query_lower:
            validation_result["warnings"].append(f"Severity level '{level}' should be quoted")
            validation_result["suggestions"].append(f"Use '{level.title()}' instead of {level}")
    
    # Final score calculation
    validation_result["syntax_score"] = min(1.0, validation_result["syntax_score"])
    
    # Overall validity check
    if validation_result["syntax_score"] < 0.3:
        validation_result["is_valid"] = False
        validation_result["errors"].append("Query syntax score too low - likely invalid DataPrime syntax")
    
    return validation_result

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("validation_service.health_check") as span:
        span.set_attribute("service.name", "validation_service")
        span.set_attribute("service.version", "1.0.0")
        
        # Add small delay to simulate processing
        time.sleep(0.015)  # 15ms
        
        return jsonify({
            "status": "healthy",
            "service": "validation_service",
            "version": "1.0.0",
            "stats": validation_stats,
            "timestamp": datetime.now().isoformat()
        })

@app.route('/validate', methods=['POST'])
def validate_query():
    """Validate DataPrime query syntax and provide suggestions."""
    # Extract and set trace context for proper distributed tracing
    trace_context = extract_trace_context()
    token = None
    if trace_context:
        token = context.attach(trace_context)
    
    with tracer.start_as_current_span("validation_service.validate_dataprime_query") as span:
        span.set_attribute("service.name", "validation_service")
        span.set_attribute("operation.name", "validate_dataprime_query")
        
        try:
            validation_stats["queries_validated"] += 1
            
            # Get query to validate
            data = request.get_json()
            if not data or 'query' not in data:
                validation_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Missing query"))
                return jsonify({"error": "Missing 'query' in request"}), 400
                
            query = data['query'].strip()
            if not query:
                validation_stats["errors"] += 1
                span.set_status(trace.Status(trace.StatusCode.ERROR, "Empty query"))
                return jsonify({"error": "Empty query"}), 400
            
            span.set_attribute("query.length", len(query))
            span.set_attribute("query.content", query[:100])  # First 100 chars
            
            # Add validation processing delay
            time.sleep(0.075)  # 75ms for comprehensive validation
            
            # Perform comprehensive validation
            with tracer.start_as_current_span("validation_service.syntax_analysis") as syntax_span:
                validation_result = validate_dataprime_syntax(query)
                
                syntax_span.set_attribute("validation.is_valid", validation_result["is_valid"])
                syntax_span.set_attribute("validation.syntax_score", validation_result["syntax_score"])
                syntax_span.set_attribute("validation.complexity_score", validation_result["complexity_score"])
                syntax_span.set_attribute("validation.warnings_count", len(validation_result["warnings"]))
                syntax_span.set_attribute("validation.errors_count", len(validation_result["errors"]))
                syntax_span.set_attribute("validation.suggestions_count", len(validation_result["suggestions"]))
                
                # Update stats
                if validation_result["is_valid"]:
                    validation_stats["valid_queries"] += 1
                else:
                    validation_stats["invalid_queries"] += 1
                
                validation_stats["warnings_issued"] += len(validation_result["warnings"])
                
                time.sleep(0.025)  # 25ms for analysis processing
            
            # Add enhancement suggestions based on query pattern
            with tracer.start_as_current_span("validation_service.enhancement_suggestions") as enhance_span:
                enhancements = []
                
                # Suggest performance optimizations
                if "groupby" in query.lower() and "limit" not in query.lower():
                    enhancements.append("Consider adding '| limit 100' to prevent large result sets")
                
                if "source logs" in query.lower() and "last" not in query.lower():
                    enhancements.append("Add time constraints like 'last 1h' to improve query performance")
                
                if "$d." in query and "$m.severity" not in query:
                    enhancements.append("Consider filtering by severity level to focus results")
                
                validation_result["enhancements"] = enhancements
                enhance_span.set_attribute("enhancements.count", len(enhancements))
                
                time.sleep(0.015)  # 15ms for enhancement processing
            
            # Prepare final response
            result = {
                "success": True,
                "is_valid": validation_result["is_valid"],
                "syntax_score": validation_result["syntax_score"],
                "complexity_score": validation_result["complexity_score"],
                "warnings": validation_result["warnings"],
                "errors": validation_result["errors"],
                "suggestions": validation_result["suggestions"],
                "enhancements": validation_result.get("enhancements", []),
                "processing_time_ms": int((time.time() * 1000) % 1000),
                "service": "validation_service"
            }
            
            span.set_attribute("response.success", True)
            span.set_attribute("response.is_valid", validation_result["is_valid"])
            span.set_attribute("response.score", validation_result["syntax_score"])
            
            return jsonify(result)
            
        except Exception as e:
            validation_stats["errors"] += 1
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            
            return jsonify({
                "success": False,
                "error": str(e),
                "service": "validation_service",
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
    
    with tracer.start_as_current_span("validation_service.get_stats") as span:
        span.set_attribute("service.name", "validation_service")
        
        return jsonify({
            "service": "validation_service",
            "stats": validation_stats,
            "timestamp": datetime.now().isoformat()
        })

if __name__ == '__main__':
    # Initialize instrumentation
    
    
    print("✅ Validation Service starting on port 5002...")
    app.run(host='0.0.0.0', port=8012, debug=False)