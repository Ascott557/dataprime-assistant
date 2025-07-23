"""DataPrime knowledge base with operators, patterns, and examples."""

from typing import Dict, List, Tuple, Any

# Core DataPrime operators with syntax and descriptions
OPERATORS = {
    "source": {
        "description": "Set the data source for your query",
        "syntax": "source <dataset> [<timeframe>]",
        "examples": [
            "source logs",
            "source logs last 1h",
            "source logs between @'2024-01-01' and @'2024-01-02'",
            "source spans last 30m"
        ]
    },
    "filter": {
        "description": "Filter events based on conditions",
        "syntax": "filter <condition>",
        "examples": [
            "filter $m.severity == 'Error'",
            "filter $d.response_time > 1000",
            "filter $l.applicationname == 'web-api'",
            "filter $d.status_code >= 400"
        ]
    },
    "groupby": {
        "description": "Group results by expressions and calculate aggregations",
        "syntax": "groupby <expression> aggregate <aggregation>",
        "examples": [
            "groupby $l.subsystemname aggregate count()",
            "groupby $m.severity aggregate avg($d.duration)",
            "groupby $d.endpoint aggregate max($d.response_time)"
        ]
    },
    "orderby": {
        "description": "Sort data by expressions",
        "syntax": "orderby <expression> [asc|desc]",
        "examples": [
            "orderby $d.response_time desc",
            "orderby $m.timestamp asc",
            "orderby count() desc"
        ]
    },
    "top": {
        "description": "Get top N results ordered by expression",
        "syntax": "top <limit> by <expression>",
        "examples": [
            "top 10 by $d.response_time",
            "top 5 $l.subsystemname by count()",
            "top 20 by $d.duration desc"
        ]
    },
    "aggregate": {
        "description": "Calculate aggregations over input",
        "syntax": "aggregate <aggregation_expression>",
        "examples": [
            "aggregate count() as total_events",
            "aggregate avg($d.response_time) as avg_latency",
            "aggregate sum($d.bytes) as total_bytes"
        ]
    },
    "create": {
        "description": "Create new fields with calculated values",
        "syntax": "create <keypath> from <expression>",
        "examples": [
            "create $d.is_slow from $d.response_time > 1000",
            "create $d.hour from $m.timestamp.extractTime('hour')",
            "create $d.status_category from case { $d.status_code < 400 -> 'success', _ -> 'error' }"
        ]
    }
}

# Common query patterns for different use cases
COMMON_PATTERNS = {
    "time_filtering": {
        "last_hour": "source logs last 1h",
        "last_day": "source logs last 1d",
        "last_week": "source logs last 7d",
        "yesterday": "source logs between @'now'-1d and @'now'",
        "this_week": "source logs between @'now'/1w and @'now'",
        "custom_range": "source logs between @'2024-01-01' and @'2024-01-02'"
    },
    "error_analysis": {
        "all_errors": "filter $m.severity == 'Error'",
        "warnings_and_errors": "filter $m.severity in ('Warning', 'Error')",
        "http_errors": "filter $d.status_code >= 400",
        "server_errors": "filter $d.status_code >= 500",
        "client_errors": "filter $d.status_code >= 400 && $d.status_code < 500"
    },
    "performance_analysis": {
        "slow_requests": "filter $d.response_time > 1000",
        "high_latency": "filter $d.duration > 5000",
        "timeout_errors": "filter $d.error_type == 'timeout'",
        "high_cpu": "filter $d.cpu_usage > 80"
    },
    "aggregation_patterns": {
        "count_by_service": "groupby $l.subsystemname aggregate count()",
        "avg_response_time": "groupby $l.subsystemname aggregate avg($d.response_time)",
        "error_rate": "groupby $l.subsystemname aggregate count_if($m.severity == 'Error') / count() * 100",
        "top_endpoints": "groupby $d.endpoint aggregate count() | top 10 by count()"
    }
}

# Intent classification mappings
INTENT_MAPPINGS = {
    "error_analysis": {
        "keywords": ["error", "errors", "failed", "failure", "exception", "crash", "bug", "issue"],
        "patterns": COMMON_PATTERNS["error_analysis"],
        "default_timeframe": "last 1h"
    },
    "performance": {
        "keywords": ["slow", "fast", "latency", "response time", "performance", "timeout", "duration"],
        "patterns": COMMON_PATTERNS["performance_analysis"],
        "default_timeframe": "last 1h"
    },
    "aggregation": {
        "keywords": ["count", "sum", "average", "total", "group by", "aggregate", "statistics"],
        "patterns": COMMON_PATTERNS["aggregation_patterns"],
        "default_timeframe": "last 1d"
    },
    "search": {
        "keywords": ["show", "find", "get", "list", "display", "search"],
        "patterns": {"basic_search": "filter"},
        "default_timeframe": "last 1h"
    },
    "time_analysis": {
        "keywords": ["trend", "over time", "timeline", "hourly", "daily", "history"],
        "patterns": {"time_series": "groupby $m.timestamp.roundTime(1h) aggregate count()"},
        "default_timeframe": "last 1d"
    }
}

# Example queries with natural language input and expected DataPrime output
EXAMPLE_QUERIES = [
    # Error Analysis Examples
    ("Show me all errors from the last hour", 
     "source logs last 1h | filter $m.severity == 'Error'"),
    
    ("Find failed API calls", 
     "source logs | filter $d.status_code >= 400"),
    
    ("Show me server errors from yesterday", 
     "source logs between @'now'-1d and @'now' | filter $d.status_code >= 500"),
    
    # Performance Examples
    ("Find slow database queries", 
     "source logs | filter $d.query_duration > 1000"),
    
    ("Show high response time requests from last 30 minutes", 
     "source logs last 30m | filter $d.response_time > 2000"),
    
    ("Get timeout errors", 
     "source logs | filter $d.error_type == 'timeout'"),
    
    # Aggregation Examples
    ("Count logs by service", 
     "source logs | groupby $l.subsystemname aggregate count()"),
    
    ("Average response time by endpoint", 
     "source logs | groupby $d.endpoint aggregate avg($d.response_time)"),
    
    ("Top 10 busiest services", 
     "source logs | groupby $l.subsystemname aggregate count() | top 10 by count()"),
    
    # Search Examples
    ("Show me logs from the payment service", 
     "source logs | filter $l.subsystemname == 'payment'"),
    
    ("Find logs containing 'authentication'", 
     "source logs | filter $d.message ~~ 'authentication'"),
    
    # Time Analysis Examples
    ("Show error trends over the last day", 
     "source logs last 1d | filter $m.severity == 'Error' | groupby $m.timestamp.roundTime(1h) aggregate count()"),
    
    ("Hourly request count for last 24 hours", 
     "source logs last 1d | groupby $m.timestamp.roundTime(1h) aggregate count()"),
    
    # Complex Examples
    ("Show me the top 5 slowest endpoints with error rates", 
     "source logs | groupby $d.endpoint aggregate avg($d.response_time) as avg_time, count_if($d.status_code >= 400) / count() * 100 as error_rate | top 5 by avg_time"),
    
    ("Find services with high error rates in the last hour", 
     "source logs last 1h | groupby $l.subsystemname aggregate count() as total, count_if($m.severity == 'Error') as errors | create $d.error_rate from $d.errors / $d.total * 100 | filter $d.error_rate > 5"),
]

# Validation rules for DataPrime queries
VALIDATION_RULES = {
    "required_source": {
        "rule": "Query must start with 'source'",
        "check": lambda query: query.strip().startswith("source")
    },
    "valid_operators": {
        "rule": "Only use valid DataPrime operators",
        "valid_ops": list(OPERATORS.keys()) + ["limit", "distinct", "choose", "remove"]
    },
    "proper_syntax": {
        "rule": "Proper operator syntax and field references",
        "field_prefixes": ["$m.", "$l.", "$d."]
    }
}

def get_operator_info(operator_name: str) -> Dict[str, Any]:
    """Get information about a specific DataPrime operator."""
    return OPERATORS.get(operator_name, {})

def get_examples_for_intent(intent: str, limit: int = 5) -> List[Tuple[str, str]]:
    """Get example queries for a specific intent."""
    intent_keywords = INTENT_MAPPINGS.get(intent, {}).get("keywords", [])
    examples = []
    
    for input_text, output_query in EXAMPLE_QUERIES:
        if any(keyword in input_text.lower() for keyword in intent_keywords):
            examples.append((input_text, output_query))
            if len(examples) >= limit:
                break
    
    return examples

def get_pattern_for_intent(intent: str, specific_pattern: str = None) -> str:
    """Get a DataPrime pattern for a specific intent."""
    intent_data = INTENT_MAPPINGS.get(intent, {})
    patterns = intent_data.get("patterns", {})
    
    if specific_pattern and specific_pattern in patterns:
        return patterns[specific_pattern]
    
    # Return first available pattern
    return next(iter(patterns.values())) if patterns else ""