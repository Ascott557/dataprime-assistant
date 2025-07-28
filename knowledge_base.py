#!/usr/bin/env python3
"""
📚 DataPrime Knowledge Base for Enhanced Query Generation

Incorporates comprehensive DataPrime documentation to provide:
- Intent classification
- Query validation  
- Enhanced examples and context
- Operator and function reference
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """DataPrime query intent classifications."""
    ERROR_ANALYSIS = "error_analysis"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    AGGREGATION = "aggregation"
    FILTERING = "filtering"
    TIME_ANALYSIS = "time_analysis"
    TEXT_SEARCH = "text_search"
    COUNT_ANALYSIS = "count_analysis"
    TOP_BOTTOM_ANALYSIS = "top_bottom_analysis"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent_type: IntentType
    confidence: float
    keywords_found: List[str]
    suggested_operators: List[str]


@dataclass
class ValidationIssue:
    """Query validation issue."""
    level: str  # "error", "warning", "info"
    message: str
    position: Optional[int] = None


@dataclass
class ValidationResult:
    """Query validation result."""
    is_valid: bool
    syntax_score: float
    complexity_score: float
    issues: List[ValidationIssue]


class DataPrimeKnowledgeBase:
    """
    Comprehensive DataPrime knowledge base with documentation integration.
    """
    
    def __init__(self):
        """Initialize the knowledge base with DataPrime documentation."""
        self.classifier = IntentClassifier()
        self.validator = DataPrimeQueryValidator()
        self.operators = self._load_operators()
        self.functions = self._load_functions()
        self.examples = self._load_examples()
    
    def _load_operators(self) -> Dict[str, Dict[str, Any]]:
        """Load DataPrime operators with their documentation."""
        return {
            # Core data processing operators
            "source": {
                "description": "Set the data source (logs, spans) with optional timeframe",
                "syntax": "source <dataset> [<timeframe>]",
                "examples": ["source logs", "source logs last 1h", "source spans between @'2021-01-01' and @'2021-01-02'"],
                "category": "source"
            },
            "filter": {
                "description": "Filter events based on conditions",
                "syntax": "filter <condition-expression>",
                "examples": ["filter $m.severity == 'Error'", "filter $d.status_code >= 400"],
                "category": "filtering"
            },
            "groupby": {
                "description": "Group results and calculate aggregations",
                "syntax": "groupby <expression> [aggregate <aggregation>]",
                "examples": ["groupby $l.subsystemname aggregate count()", "groupby $m.severity aggregate avg($d.duration)"],
                "category": "aggregation"
            },
            "aggregate": {
                "description": "Calculate aggregations over input",
                "syntax": "aggregate <aggregation_expression> [as <alias>]",
                "examples": ["aggregate count() as total", "aggregate max($d.duration) as max_duration"],
                "category": "aggregation"
            },
            "top": {
                "description": "Get top N results ordered by expression",
                "syntax": "top <limit> <expressions> by <orderby_expression>",
                "examples": ["top 10 $m.severity by $d.duration", "top 5 $l.subsystemname by count()"],
                "category": "ranking"
            },
            "bottom": {
                "description": "Get bottom N results ordered by expression", 
                "syntax": "bottom <limit> <expressions> by <orderby_expression>",
                "examples": ["bottom 5 $m.severity by $d.duration"],
                "category": "ranking"
            },
            "count": {
                "description": "Count rows or non-null values",
                "syntax": "count [into <keypath>]",
                "examples": ["count", "count into $d.total_rows"],
                "category": "aggregation"
            },
            "countby": {
                "description": "Count rows grouped by expression",
                "syntax": "countby <expression> [into <keypath>]",
                "examples": ["countby $m.severity", "countby $l.subsystemname into $d.service_count"],
                "category": "aggregation"
            },
            "orderby": {
                "description": "Sort data by expression values",
                "syntax": "orderby <expression> [(asc|desc)]",
                "examples": ["orderby $d.duration desc", "orderby $m.timestamp asc"],
                "category": "sorting"
            },
            "sortby": {
                "description": "Sort data by expression values (alias for orderby)",
                "syntax": "sortby <expression> [(asc|desc)]",
                "examples": ["sortby $d.duration desc", "sortby $m.timestamp asc"],
                "category": "sorting"
            },
            "limit": {
                "description": "Limit output to first N events",
                "syntax": "limit <event-count>",
                "examples": ["limit 100", "limit 1000"],
                "category": "limiting"
            },
            "choose": {
                "description": "Select only specified keypaths",
                "syntax": "choose <keypath1> [as <alias>], <keypath2>...",
                "examples": ["choose $d.message, $m.severity", "choose $d.duration as response_time"],
                "category": "projection"
            },
            "create": {
                "description": "Create new fields from expressions",
                "syntax": "create <keypath> from <expression>",
                "examples": ["create $d.is_error from $d.status_code >= 400"],
                "category": "transformation"
            }
        }
    
    def _load_functions(self) -> Dict[str, Dict[str, Any]]:
        """Load DataPrime functions with their documentation."""
        return {
            # Aggregation functions
            "count": {"type": "aggregation", "description": "Count non-null values"},
            "sum": {"type": "aggregation", "description": "Sum numerical values"},
            "avg": {"type": "aggregation", "description": "Average of numerical values"},
            "min": {"type": "aggregation", "description": "Minimum value"},
            "max": {"type": "aggregation", "description": "Maximum value"},
            "distinct_count": {"type": "aggregation", "description": "Count distinct values"},
            "percentile": {"type": "aggregation", "description": "Calculate percentile"},
            
            # String functions
            "contains": {"type": "string", "description": "Check if string contains substring"},
            "startsWith": {"type": "string", "description": "Check if string starts with prefix"},
            "endsWith": {"type": "string", "description": "Check if string ends with suffix"},
            "toLowerCase": {"type": "string", "description": "Convert to lowercase"},
            "toUpperCase": {"type": "string", "description": "Convert to uppercase"},
            "trim": {"type": "string", "description": "Remove whitespace"},
            "length": {"type": "string", "description": "Get string length"},
            
            # Time functions
            "now": {"type": "time", "description": "Current timestamp"},
            "formatTimestamp": {"type": "time", "description": "Format timestamp to string"},
            "parseTimestamp": {"type": "time", "description": "Parse string to timestamp"},
            "extractTime": {"type": "time", "description": "Extract time unit from timestamp"},
            "roundTime": {"type": "time", "description": "Round timestamp to interval"},
            
            # Numeric functions
            "abs": {"type": "numeric", "description": "Absolute value"},
            "round": {"type": "numeric", "description": "Round to decimal places"},
            "floor": {"type": "numeric", "description": "Round down"},
            "ceil": {"type": "numeric", "description": "Round up"}
        }
    
    def _load_examples(self) -> Dict[str, List[str]]:
        """Load comprehensive DataPrime query examples by category."""
        return {
            "error_analysis": [
                "source logs last 1h | filter $m.severity == 'Error'",
                "source logs | filter $m.severity in ('Error', 'Critical') | groupby $l.subsystemname aggregate count()",
                "source logs last 24h | filter $m.severity == 'Error' | countby $l.applicationname",
                "source logs | filter $d.status_code >= 400 | top 10 $d.url by count()",
                "source logs | filter $m.severity == 'Error' | choose $d.message, $m.timestamp, $l.subsystemname"
            ],
            "performance_analysis": [
                "source logs | filter $d.duration > 1000 | top 10 $d.endpoint by $d.duration",
                "source logs last 1h | groupby $l.subsystemname aggregate avg($d.response_time) as avg_response",
                "source logs | filter $d.response_time > 500 | countby $l.subsystemname",
                "source spans last 1h | filter $d.duration > 1000000 | orderby $d.duration desc",
                "source logs | groupby $d.endpoint aggregate percentile(0.95, $d.duration) as p95_latency"
            ],
            "aggregation": [
                "source logs | groupby $m.severity aggregate count()",
                "source logs last 24h | groupby $l.subsystemname aggregate count() as request_count",
                "source logs | groupby $l.applicationname, $m.severity aggregate count()",
                "source logs | countby $l.subsystemname",
                "source logs | aggregate count() as total_logs, distinct_count($l.subsystemname) as unique_services"
            ],
            "time_analysis": [
                "source logs last 1h",
                "source logs between @'2023-01-01T00:00:00Z' and @'2023-01-02T00:00:00Z'",
                "source logs last 24h | groupby $m.timestamp.roundTime(1h) aggregate count()",
                "source logs around @'2023-01-01T12:00:00Z' interval 30m",
                "source logs | filter $m.timestamp > @'now'-1d"
            ],
            "text_search": [
                "source logs | filter $d.message ~ 'error'",
                "source logs | find 'exception' in $d.message",
                "source logs | wildtext 'timeout'",
                "source logs | lucene 'status_code:404'",
                "source logs | filter $d.message.contains('failed')"
            ],
            "top_analysis": [
                "source logs | top 10 $l.subsystemname by count()",
                "source logs | top 5 $d.endpoint by avg($d.duration)",
                "source logs last 1h | top 10 $d.user_id by count() as request_count",
                "source logs | groupby $l.subsystemname aggregate count() | orderby count desc | limit 10"
            ]
        }
    
    def get_enhanced_prompt_context(self, user_input: str, intent: IntentType) -> str:
        """Generate focused, effective prompts based on intent (simplified for better results)."""
        
        # Simplified, more effective base prompt
        base_context = """You are an expert DataPrime query generator. 

CRITICAL RULES:
1. Generate ONLY the query syntax, no explanations
2. Always start with "source logs" or "source spans"  
3. For time references like "last hour", "last 4 hours", "yesterday" use: last 1h, last 4h, last 24h
4. For service names, use single words without spaces: "frontend", "backend", "api"
5. Severity levels: 'Debug', 'Info', 'Warn', 'Error', 'Critical'

KEY FIELDS:
- $m.severity (severity level)
- $l.subsystemname (service name like 'frontend', 'backend') 
- $d.status_code, $d.duration, $d.message (user data)

QUICK EXAMPLES:
- "errors last hour" → source logs last 1h | filter $m.severity == 'Error'
- "frontend errors" → source logs | filter $m.severity == 'Error' and $l.subsystemname == 'frontend'
- "slow requests" → source logs | filter $d.duration > 1000
- "count by service" → source logs | groupby $l.subsystemname aggregate count()
- "slowest spans" → source spans | sortby $d.duration desc
- "top 10 errors" → source logs | filter $m.severity == 'Error' | sortby $m.timestamp desc | limit 10

"""
        
        # Intent-specific guidance (much simpler)
        if intent == IntentType.ERROR_ANALYSIS:
            return base_context + """For ERROR queries: Always include time scope and service filter when mentioned."""
            
        elif intent == IntentType.PERFORMANCE_ANALYSIS:
            return base_context + """For PERFORMANCE queries: Focus on duration, response_time fields. Use sortby for ranking (e.g., 'sortby $d.duration desc') and top/groupby for analysis."""
            
        elif intent == IntentType.AGGREGATION:
            return base_context + """For AGGREGATION queries: Use groupby with aggregate functions or countby for simple counts."""
            
        else:
            return base_context
    
    def get_validation_rules(self) -> List[str]:
        """Get validation rules for DataPrime queries."""
        return [
            "Must start with 'source logs' or 'source spans'",
            "Use pipe (|) to separate operators",
            "Field references must use $m, $l, or $d prefixes",
            "Time intervals use format: last 1h, last 24h, last 1d",
            "Severity values: 'Debug', 'Info', 'Warn', 'Error', 'Critical'",
            "String values must be quoted with single quotes",
            "Aggregation functions need aggregate keyword or groupby",
            "Comparison operators: ==, !=, <, <=, >, >=",
            "Logical operators: &&, ||, !",
            "Time functions available: now(), formatTimestamp(), etc."
        ]


class IntentClassifier:
    """Classifies user intent for DataPrime queries."""
    
    def __init__(self):
        """Initialize intent classification patterns."""
        self.patterns = {
            IntentType.ERROR_ANALYSIS: [
                r'\b(error|errors|exception|exceptions|failure|failures|bug|bugs)\b',
                r'\b(failed|failing|crashed|crash)\b',
                r'\bstatus.code.*(4\d\d|5\d\d)\b',
                r'\bseverity.*(error|critical)\b'
            ],
            IntentType.PERFORMANCE_ANALYSIS: [
                r'\b(slow|performance|latency|duration|response.time)\b',
                r'\b(timeout|timeouts|bottleneck|bottlenecks)\b',
                r'\b(p95|p99|percentile|average|avg)\b',
                r'\b(memory|cpu|throughput|optimization)\b'
            ],
            IntentType.AGGREGATION: [
                r'\b(count|sum|average|total|group|aggregate)\b',
                r'\b(by.service|by.application|breakdown)\b',
                r'\b(statistics|stats|metrics)\b'
            ],
            IntentType.TIME_ANALYSIS: [
                r'\b(yesterday|today|last.hour|last.day|last.week)\b',
                r'\b(between|from|since|until|during)\b',
                r'\b(timeline|over.time|hourly|daily)\b'
            ],
            IntentType.TEXT_SEARCH: [
                r'\b(search|find|contains|message|text)\b',
                r'\b(logs?.containing|grep|match)\b'
            ],
            IntentType.TOP_BOTTOM_ANALYSIS: [
                r'\b(top|bottom|highest|lowest|most|least)\b',
                r'\b(ranking|rank|best|worst)\b'
            ]
        }
    
    def classify(self, user_input: str) -> IntentResult:
        """Classify user input to determine intent."""
        user_lower = user_input.lower()
        scores = {}
        found_keywords = []
        
        # Score each intent type
        for intent_type, patterns in self.patterns.items():
            score = 0
            intent_keywords = []
            
            for pattern in patterns:
                matches = re.findall(pattern, user_lower)
                if matches:
                    score += len(matches)
                    intent_keywords.extend(matches)
            
            if score > 0:
                scores[intent_type] = score
                found_keywords.extend(intent_keywords)
        
        # Determine best intent
        if not scores:
            return IntentResult(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                keywords_found=[],
                suggested_operators=["filter", "groupby"]
            )
        
        best_intent = max(scores.keys(), key=lambda k: scores[k])
        max_score = scores[best_intent]
        confidence = min(max_score / 3.0, 1.0)  # Normalize confidence
        
        # Suggest operators based on intent
        operator_suggestions = self._get_suggested_operators(best_intent)
        
        return IntentResult(
            intent_type=best_intent,
            confidence=confidence,
            keywords_found=list(set(found_keywords)),
            suggested_operators=operator_suggestions
        )
    
    def _get_suggested_operators(self, intent: IntentType) -> List[str]:
        """Get suggested operators for an intent type."""
        suggestions = {
            IntentType.ERROR_ANALYSIS: ["filter", "groupby", "countby", "choose"],
            IntentType.PERFORMANCE_ANALYSIS: ["filter", "top", "groupby", "aggregate"],
            IntentType.AGGREGATION: ["groupby", "countby", "aggregate", "sum", "avg"],
            IntentType.TIME_ANALYSIS: ["source", "filter", "groupby"],
            IntentType.TEXT_SEARCH: ["filter", "find", "lucene", "wildtext"],
            IntentType.TOP_BOTTOM_ANALYSIS: ["top", "bottom", "orderby", "limit"],
            IntentType.UNKNOWN: ["filter", "groupby", "source"]
        }
        return suggestions.get(intent, ["filter", "groupby"])


class DataPrimeQueryValidator:
    """Validates DataPrime query syntax and semantics."""
    
    def __init__(self):
        """Initialize validator with DataPrime rules."""
        self.required_operators = ["source"]
        self.valid_sources = ["logs", "spans"]
        self.valid_severities = ["Debug", "Info", "Warn", "Error", "Critical", "Verbose"]
        self.field_prefixes = ["$m", "$l", "$d"]
    
    def validate(self, query: str) -> ValidationResult:
        """Validate a DataPrime query comprehensively."""
        query = query.strip()
        issues = []
        syntax_score = 1.0
        complexity_score = 0.0
        
        # Basic structure validation
        if not query:
            issues.append(ValidationIssue("error", "Query is empty"))
            return ValidationResult(False, 0.0, 0.0, issues)
        
        # Must start with source
        if not re.match(r'^\s*source\s+', query, re.IGNORECASE):
            issues.append(ValidationIssue("error", "Query must start with 'source'"))
            syntax_score -= 0.5
        
        # Check for valid data source
        source_match = re.search(r'source\s+(logs|spans)', query, re.IGNORECASE)
        if not source_match:
            issues.append(ValidationIssue("warning", "Data source should be 'logs' or 'spans'"))
            syntax_score -= 0.2
        
        # Check pipe operator usage
        if '|' not in query and len(query.split()) > 2:
            issues.append(ValidationIssue("warning", "Consider using pipe (|) to separate operators"))
            syntax_score -= 0.1
        
        # Validate field references
        field_refs = re.findall(r'\$[mld]\.[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*', query)
        if field_refs:
            complexity_score += 0.2
        
        # Check for proper string quoting
        unquoted_strings = re.findall(r'==\s*([a-zA-Z][a-zA-Z0-9_]*)\b(?!\s*\()', query)
        for string in unquoted_strings:
            if string not in self.valid_severities:
                issues.append(ValidationIssue("warning", f"String '{string}' should be quoted"))
                syntax_score -= 0.1
        
        # Validate severity values
        severity_refs = re.findall(r"'(Debug|Info|Warn|Error|Critical|Verbose)'", query)
        if severity_refs:
            complexity_score += 0.1
        
        # Check for aggregation without groupby
        if re.search(r'\b(count|sum|avg|min|max)\s*\(', query, re.IGNORECASE):
            if not re.search(r'\b(groupby|aggregate)\b', query, re.IGNORECASE):
                issues.append(ValidationIssue("info", "Consider using 'groupby' or 'aggregate' with aggregation functions"))
            complexity_score += 0.3
        
        # Calculate complexity based on operators
        operators = re.findall(r'\b(filter|groupby|aggregate|top|bottom|orderby|limit|count|sum|avg)\b', query, re.IGNORECASE)
        complexity_score += len(set(operators)) * 0.1
        
        # Normalize scores
        syntax_score = max(0.0, min(1.0, syntax_score))
        complexity_score = max(0.0, min(1.0, complexity_score))
        
        # Overall validity
        is_valid = len([i for i in issues if i.level == "error"]) == 0 and syntax_score > 0.5
        
        return ValidationResult(
            is_valid=is_valid,
            syntax_score=syntax_score,
            complexity_score=complexity_score,
            issues=issues
        ) 