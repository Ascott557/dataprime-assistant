"""DataPrime query validation utilities."""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ValidationLevel(Enum):
    """Validation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

@dataclass
class ValidationIssue:
    """A validation issue found in a DataPrime query."""
    level: ValidationLevel
    message: str
    position: Optional[int] = None
    suggestion: Optional[str] = None

@dataclass
class ValidationResult:
    """Result of DataPrime query validation."""
    is_valid: bool
    syntax_score: float  # 0.0 to 1.0
    issues: List[ValidationIssue]
    complexity_score: float  # 0.0 to 1.0 (simple to complex)
    estimated_cost: str  # low, medium, high
    performance_warnings: List[str]

class DataPrimeValidator:
    """Validates DataPrime query syntax and provides optimization suggestions."""
    
    def __init__(self):
        self.valid_operators = {
            "source", "filter", "groupby", "aggregate", "orderby", "top", "bottom",
            "limit", "choose", "create", "remove", "distinct", "count", "countby",
            "join", "union", "explode", "extract", "redact", "replace"
        }
        
        self.valid_sources = {"logs", "spans"}
        
        self.valid_field_prefixes = ["$m.", "$l.", "$d."]
        
        self.aggregation_functions = {
            "count", "sum", "avg", "min", "max", "distinct_count", 
            "percentile", "stddev", "variance", "any_value", "collect"
        }
        
        self.time_units = {"s", "m", "h", "d", "ms", "us", "ns"}
    
    def validate(self, query: str) -> ValidationResult:
        """Validate a DataPrime query and return detailed results."""
        issues = []
        syntax_score = 1.0
        
        # Basic structure validation
        issues.extend(self._validate_structure(query))
        
        # Operator validation
        issues.extend(self._validate_operators(query))
        
        # Field reference validation
        issues.extend(self._validate_field_references(query))
        
        # Syntax validation
        issues.extend(self._validate_syntax(query))
        
        # Performance analysis
        performance_warnings = self._analyze_performance(query)
        
        # Calculate scores
        error_count = len([i for i in issues if i.level == ValidationLevel.ERROR])
        warning_count = len([i for i in issues if i.level == ValidationLevel.WARNING])
        
        is_valid = error_count == 0
        syntax_score = max(0.0, 1.0 - (error_count * 0.3) - (warning_count * 0.1))
        
        complexity_score = self._calculate_complexity(query)
        estimated_cost = self._estimate_cost(query, complexity_score)
        
        return ValidationResult(
            is_valid=is_valid,
            syntax_score=syntax_score,
            issues=issues,
            complexity_score=complexity_score,
            estimated_cost=estimated_cost,
            performance_warnings=performance_warnings
        )
    
    def _validate_structure(self, query: str) -> List[ValidationIssue]:
        """Validate basic query structure."""
        issues = []
        query = query.strip()
        
        if not query:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Query cannot be empty"
            ))
            return issues
        
        if not query.startswith("source"):
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Query must start with 'source' operator",
                suggestion="Start your query with 'source logs' or 'source spans'"
            ))
        
        # Check for proper pipe usage
        if "|" in query:
            parts = query.split("|")
            for i, part in enumerate(parts):
                part = part.strip()
                if not part:
                    issues.append(ValidationIssue(
                        level=ValidationLevel.ERROR,
                        message=f"Empty operator at position {i + 1}",
                        suggestion="Remove empty pipes or add missing operators"
                    ))
        
        return issues
    
    def _validate_operators(self, query: str) -> List[ValidationIssue]:
        """Validate operator usage."""
        issues = []
        
        # Extract operators from query
        operators = []
        if "|" in query:
            parts = query.split("|")
            operators = [part.strip().split()[0] for part in parts if part.strip()]
        else:
            first_word = query.strip().split()[0] if query.strip() else ""
            if first_word:
                operators = [first_word]
        
        for op in operators:
            if op not in self.valid_operators:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Unknown operator: '{op}'",
                    suggestion=f"Valid operators: {', '.join(sorted(self.valid_operators))}"
                ))
        
        # Check operator sequence logic
        if "aggregate" in query and "groupby" not in query:
            if not any(agg in query for agg in ["count()", "sum(", "avg(", "min(", "max("]):
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message="'aggregate' usually follows 'groupby'",
                    suggestion="Consider using 'groupby <field> aggregate <function>'"
                ))
        
        return issues
    
    def _validate_field_references(self, query: str) -> List[ValidationIssue]:
        """Validate field references ($m., $l., $d.)."""
        issues = []
        
        # Find all field references
        field_pattern = r'\$[mld]\.[a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*'
        fields = re.findall(field_pattern, query)
        
        for field in fields:
            prefix = field[:3]  # $m., $l., or $d.
            if prefix not in self.valid_field_prefixes:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Invalid field prefix in '{field}'",
                    suggestion="Use $m. for metadata, $l. for labels, $d. for data"
                ))
        
        # Check for common field naming issues
        common_mistakes = {
            "$m.message": "$d.message",
            "$l.severity": "$m.severity",
            "$d.timestamp": "$m.timestamp"
        }
        
        for mistake, correction in common_mistakes.items():
            if mistake in query:
                issues.append(ValidationIssue(
                    level=ValidationLevel.WARNING,
                    message=f"Field '{mistake}' should probably be '{correction}'",
                    suggestion=f"Use '{correction}' instead"
                ))
        
        return issues
    
    def _validate_syntax(self, query: str) -> List[ValidationIssue]:
        """Validate DataPrime syntax."""
        issues = []
        
        # Check for unmatched quotes
        single_quotes = query.count("'")
        double_quotes = query.count('"')
        
        if single_quotes % 2 != 0:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Unmatched single quotes",
                suggestion="Ensure all strings are properly quoted"
            ))
        
        if double_quotes % 2 != 0:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Unmatched double quotes",
                suggestion="Ensure all strings are properly quoted"
            ))
        
        # Check for unmatched parentheses
        open_parens = query.count("(")
        close_parens = query.count(")")
        
        if open_parens != close_parens:
            issues.append(ValidationIssue(
                level=ValidationLevel.ERROR,
                message="Unmatched parentheses",
                suggestion="Check function calls and grouping"
            ))
        
        # Validate time expressions
        time_pattern = r'last \d+[smhd]'
        time_matches = re.findall(time_pattern, query)
        for match in time_matches:
            unit = match[-1]
            if unit not in self.time_units:
                issues.append(ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f"Invalid time unit in '{match}'",
                    suggestion="Use s, m, h, or d for time units"
                ))
        
        return issues
    
    def _analyze_performance(self, query: str) -> List[str]:
        """Analyze query for performance issues."""
        warnings = []
        
        # Check for missing time filters
        if "source logs" in query and not any(time_word in query for time_word in ["last", "between", "around"]):
            warnings.append("Consider adding a time filter to improve performance")
        
        # Check for wildcards in filters
        if "~~" in query or "*" in query:
            warnings.append("Wildcard searches can be slow on large datasets")
        
        # Check for complex aggregations
        if query.count("aggregate") > 1:
            warnings.append("Multiple aggregations can be resource-intensive")
        
        # Check for missing filters before groupby
        if "groupby" in query and "filter" not in query:
            warnings.append("Consider filtering data before grouping for better performance")
        
        return warnings
    
    def _calculate_complexity(self, query: str) -> float:
        """Calculate query complexity score (0.0 to 1.0)."""
        score = 0.0
        
        # Base complexity
        pipe_count = query.count("|")
        score += min(pipe_count * 0.2, 0.6)
        
        # Operator complexity
        complex_operators = ["groupby", "join", "union", "extract"]
        for op in complex_operators:
            if op in query:
                score += 0.1
        
        # Function complexity
        function_count = query.count("(")
        score += min(function_count * 0.05, 0.2)
        
        # Field reference complexity
        field_count = len(re.findall(r'\$[mld]\.', query))
        score += min(field_count * 0.02, 0.1)
        
        return min(score, 1.0)
    
    def _estimate_cost(self, query: str, complexity_score: float) -> str:
        """Estimate query execution cost."""
        if complexity_score < 0.3:
            return "low"
        elif complexity_score < 0.7:
            return "medium"
        else:
            return "high"
    
    def suggest_improvements(self, query: str) -> List[str]:
        """Suggest query improvements."""
        suggestions = []
        
        # Suggest time filters
        if "source logs" in query and not any(time_word in query for time_word in ["last", "between"]):
            suggestions.append("Add a time filter like 'last 1h' for better performance")
        
        # Suggest field selection
        if "choose" not in query and len(query.split("|")) > 2:
            suggestions.append("Use 'choose' to select only needed fields")
        
        # Suggest ordering
        if "groupby" in query and "orderby" not in query and "top" not in query:
            suggestions.append("Consider adding 'orderby' or 'top' to sort results")
        
        return suggestions