"""Enhanced knowledge base with comprehensive DataPrime cheat sheet integration."""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .cheat_sheet_parser import load_enhanced_knowledge, DataPrimeOperator, DataPrimeFunction
from .knowledge_base import IntentType, IntentResult, QueryExample
from .enhanced_intent_classifier import SemanticIntentClassifier

@dataclass
class EnhancedQueryExample:
    """Enhanced query example with more context."""
    user_input: str
    dataprime_query: str
    intent_type: IntentType
    complexity: str
    operators_used: List[str]
    functions_used: List[str]
    explanation: str
    category: str

class EnhancedDataPrimeKnowledgeBase:
    """Enhanced knowledge base with comprehensive DataPrime knowledge."""
    
    def __init__(self):
        self.semantic_classifier = SemanticIntentClassifier()
        
        # Load enhanced knowledge from cheat sheet
        self.cheat_sheet_knowledge = load_enhanced_knowledge()
        
        # Organize operators and functions for quick lookup
        self.operators_by_name = self._index_operators()
        self.functions_by_name = self._index_functions()
        self.operators_by_category = self._group_operators_by_category()
        self.functions_by_category = self._group_functions_by_category()
        
        # Enhanced examples
        self.enhanced_examples = self._build_enhanced_examples()
        self.examples_by_intent = self._group_examples_by_intent()
        
        print(f"✅ Enhanced Knowledge Base loaded:")
        print(f"   📚 {len(self.operators_by_name)} operators")
        print(f"   🔧 {len(self.functions_by_name)} functions")
        print(f"   💡 {len(self.enhanced_examples)} enhanced examples")
    
    def _index_operators(self) -> Dict[str, Dict[str, Any]]:
        """Create operator lookup by name and aliases."""
        operators = {}
        
        for op_data in self.cheat_sheet_knowledge['operators']:
            operators[op_data['name']] = op_data
            # Also index by aliases
            for alias in op_data['aliases']:
                if alias != op_data['name']:
                    operators[alias] = op_data
        
        return operators
    
    def _index_functions(self) -> Dict[str, Dict[str, Any]]:
        """Create function lookup by name."""
        functions = {}
        
        for func_data in self.cheat_sheet_knowledge['functions']:
            functions[func_data['name']] = func_data
        
        return functions
    
    def _group_operators_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group operators by category."""
        categories = {}
        
        for op_data in self.cheat_sheet_knowledge['operators']:
            category = op_data['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(op_data)
        
        return categories
    
    def _group_functions_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Group functions by category."""
        categories = {}
        
        for func_data in self.cheat_sheet_knowledge['functions']:
            category = func_data['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(func_data)
        
        return categories
    
    def _build_enhanced_examples(self) -> List[EnhancedQueryExample]:
        """Build enhanced examples from cheat sheet and intent mappings."""
        enhanced_examples = []
        
        # Start with examples from the cheat sheet
        for category, examples in self.cheat_sheet_knowledge['examples_by_category'].items():
            for example in examples:
                if self._is_valid_dataprime_query(example):
                    intent_type = self._classify_example_intent(example)
                    
                    enhanced_example = EnhancedQueryExample(
                        user_input=self._generate_natural_language_for_query(example),
                        dataprime_query=example,
                        intent_type=intent_type,
                        complexity=self._assess_query_complexity(example),
                        operators_used=self._extract_operators_from_query(example),
                        functions_used=self._extract_functions_from_query(example),
                        explanation=self._generate_query_explanation(example),
                        category=category
                    )
                    enhanced_examples.append(enhanced_example)
        
        # Add hand-crafted high-quality examples for common use cases
        enhanced_examples.extend(self._create_curated_examples())
        
        return enhanced_examples
    
    def _create_curated_examples(self) -> List[EnhancedQueryExample]:
        """Create curated high-quality examples for common use cases."""
        curated_examples = [
            # Error Analysis Examples
            EnhancedQueryExample(
                user_input="Show me all errors from the last hour",
                dataprime_query="source logs last 1h | filter $m.severity == 'Error'",
                intent_type=IntentType.ERROR_ANALYSIS,
                complexity="simple",
                operators_used=["source", "filter"],
                functions_used=[],
                explanation="Gets recent logs and filters for error severity",
                category="error_analysis"
            ),
            EnhancedQueryExample(
                user_input="Find error logs from web-api service with status code 500",
                dataprime_query="source logs | filter $l.subsystemname == 'web-api' && $d.status_code == 500",
                intent_type=IntentType.ERROR_ANALYSIS,
                complexity="medium",
                operators_used=["source", "filter"],
                functions_used=[],
                explanation="Filters logs by service name and HTTP status code",
                category="error_analysis"
            ),
            
            # Performance Analysis Examples
            EnhancedQueryExample(
                user_input="Show me slow requests over 1000ms",
                dataprime_query="source logs | filter $d.response_time > 1000",
                intent_type=IntentType.PERFORMANCE,
                complexity="simple",
                operators_used=["source", "filter"],
                functions_used=[],
                explanation="Filters logs for requests exceeding response time threshold",
                category="performance"
            ),
            EnhancedQueryExample(
                user_input="What's the 95th percentile response time by service?",
                dataprime_query="source logs | groupby $l.subsystemname aggregate percentile(0.95, $d.response_time) as p95_latency",
                intent_type=IntentType.PERFORMANCE,
                complexity="advanced",
                operators_used=["source", "groupby", "aggregate"],
                functions_used=["percentile"],
                explanation="Calculates 95th percentile latency grouped by service",
                category="performance"
            ),
            
            # Aggregation Examples
            EnhancedQueryExample(
                user_input="Count logs by severity level",
                dataprime_query="source logs | groupby $m.severity aggregate count()",
                intent_type=IntentType.AGGREGATION,
                complexity="simple",
                operators_used=["source", "groupby", "aggregate"],
                functions_used=["count"],
                explanation="Groups and counts logs by severity level",
                category="aggregation"
            ),
            EnhancedQueryExample(
                user_input="Show me the top 10 busiest endpoints by request count",
                dataprime_query="source logs | groupby $d.endpoint aggregate count() | top 10 by count()",
                intent_type=IntentType.AGGREGATION,
                complexity="medium",
                operators_used=["source", "groupby", "aggregate", "top"],
                functions_used=["count"],
                explanation="Groups by endpoint, counts requests, and shows top 10",
                category="aggregation"
            ),
            
            # Time Analysis Examples
            EnhancedQueryExample(
                user_input="Show hourly error trends for the last day",
                dataprime_query="source logs last 1d | filter $m.severity == 'Error' | groupby $m.timestamp.roundTime(1h) aggregate count() | orderby $m.timestamp",
                intent_type=IntentType.TIME_ANALYSIS,
                complexity="advanced",
                operators_used=["source", "filter", "groupby", "aggregate", "orderby"],
                functions_used=["roundTime", "count"],
                explanation="Analyzes error count trends by hour over the last day",
                category="time_analysis"
            ),
            
            # Search Examples
            EnhancedQueryExample(
                user_input="Find logs containing 'database connection failed'",
                dataprime_query="source logs | filter $d.message.contains('database connection failed')",
                intent_type=IntentType.SEARCH,
                complexity="simple",
                operators_used=["source", "filter"],
                functions_used=["contains"],
                explanation="Searches for logs with specific error message",
                category="search"
            )
        ]
        
        return curated_examples
    
    def _is_valid_dataprime_query(self, query: str) -> bool:
        """Check if a string looks like a valid DataPrime query."""
        query = query.strip()
        
        # Must start with 'source' or be a pipeline continuation
        if not query.startswith('source') and '|' not in query:
            return False
        
        # Must contain DataPrime operators
        known_operators = set(self.operators_by_name.keys())
        query_words = query.lower().split()
        
        return any(word in known_operators for word in query_words)
    
    def _classify_example_intent(self, query: str) -> IntentType:
        """Classify the intent of a DataPrime query example."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['error', 'severity', 'failed']):
            return IntentType.ERROR_ANALYSIS
        elif any(word in query_lower for word in ['response_time', 'duration', 'latency', 'percentile']):
            return IntentType.PERFORMANCE
        elif any(word in query_lower for word in ['groupby', 'count', 'sum', 'avg', 'top']):
            return IntentType.AGGREGATION
        elif any(word in query_lower for word in ['roundtime', 'last', 'between', 'formattime']):
            return IntentType.TIME_ANALYSIS
        elif any(word in query_lower for word in ['contains', 'find', 'lucene', 'matches']):
            return IntentType.SEARCH
        else:
            return IntentType.UNKNOWN
    
    def _generate_natural_language_for_query(self, query: str) -> str:
        """Generate a natural language description for a DataPrime query."""
        # This is a simplified version - could be made much more sophisticated
        query_lower = query.lower()
        
        if 'filter' in query_lower and 'severity' in query_lower:
            return "Show me error logs"
        elif 'groupby' in query_lower and 'count' in query_lower:
            return "Count events by category"
        elif 'response_time' in query_lower or 'duration' in query_lower:
            return "Analyze performance metrics"
        elif 'last' in query and ('h' in query or 'd' in query):
            return "Show recent activity"
        else:
            return "Analyze log data"
    
    def _assess_query_complexity(self, query: str) -> str:
        """Assess the complexity of a DataPrime query."""
        operator_count = query.count('|')
        function_count = len(self._extract_functions_from_query(query))
        
        if operator_count <= 2 and function_count <= 1:
            return "simple"
        elif operator_count <= 4 and function_count <= 3:
            return "medium"
        else:
            return "advanced"
    
    def _extract_operators_from_query(self, query: str) -> List[str]:
        """Extract DataPrime operators used in a query."""
        operators = []
        query_words = query.lower().split()
        
        for word in query_words:
            if word in self.operators_by_name:
                if word not in operators:
                    operators.append(word)
        
        return operators
    
    def _extract_functions_from_query(self, query: str) -> List[str]:
        """Extract DataPrime functions used in a query."""
        functions = []
        
        for func_name in self.functions_by_name.keys():
            if func_name.lower() in query.lower():
                if func_name not in functions:
                    functions.append(func_name)
        
        return functions
    
    def _generate_query_explanation(self, query: str) -> str:
        """Generate an explanation of what a DataPrime query does."""
        parts = []
        operators = self._extract_operators_from_query(query)
        functions = self._extract_functions_from_query(query)
        
        if 'source' in operators:
            parts.append("retrieves data from logs")
        if 'filter' in operators:
            parts.append("filters based on conditions")
        if 'groupby' in operators:
            parts.append("groups results")
        if 'aggregate' in operators:
            parts.append("calculates aggregations")
        if functions:
            parts.append(f"uses functions: {', '.join(functions[:2])}")
        
        return "Query " + ", then ".join(parts) if parts else "Processes log data"
    
    def _group_examples_by_intent(self) -> Dict[IntentType, List[EnhancedQueryExample]]:
        """Group examples by intent type."""
        grouped = {}
        
        for example in self.enhanced_examples:
            if example.intent_type not in grouped:
                grouped[example.intent_type] = []
            grouped[example.intent_type].append(example)
        
        return grouped
    
    def get_relevant_examples_enhanced(self, intent: IntentResult, limit: int = 3) -> List[EnhancedQueryExample]:
        """Get relevant examples for an intent with enhanced context."""
        examples = self.examples_by_intent.get(intent.intent_type, [])
        
        # Score examples by relevance
        scored_examples = []
        for example in examples:
            score = self._calculate_example_relevance(intent, example)
            scored_examples.append((score, example))
        
        # Sort by score and return top examples
        scored_examples.sort(key=lambda x: x[0], reverse=True)
        return [example for _, example in scored_examples[:limit]]
    
    def _calculate_example_relevance(self, intent: IntentResult, example: EnhancedQueryExample) -> float:
        """Calculate how relevant an example is to the given intent."""
        score = 0.0
        
        # Base score for matching intent type
        if intent.intent_type == example.intent_type:
            score += 1.0
        
        # Bonus for matching keywords
        for keyword in intent.keywords_found:
            if keyword in example.user_input.lower() or keyword in example.dataprime_query.lower():
                score += 0.3
        
        # Bonus for matching entities
        if intent.entities:
            for entity_value in intent.entities.values():
                if str(entity_value) in example.dataprime_query:
                    score += 0.5
        
        # Prefer simpler examples for lower confidence intents
        if intent.confidence < 0.7:
            if example.complexity == "simple":
                score += 0.2
            elif example.complexity == "advanced":
                score -= 0.1
        
        return score
    
    def build_enhanced_context_prompt(self, user_input: str, intent: IntentResult, examples: List[EnhancedQueryExample]) -> str:
        """Build an enhanced context prompt with comprehensive DataPrime knowledge."""
        
        # Get relevant operators for the intent
        relevant_operators = self._get_relevant_operators_for_intent(intent)
        relevant_functions = self._get_relevant_functions_for_intent(intent)
        
        prompt_parts = [
            "You are an expert DataPrime query generator. Convert natural language to DataPrime syntax.",
            "",
            f"User Request: {user_input}",
            f"Detected Intent: {intent.intent_type.value} (confidence: {intent.confidence:.2f})",
        ]
        
        if intent.entities:
            entities_str = ", ".join(f"{k}={v}" for k, v in intent.entities.items())
            prompt_parts.append(f"Extracted Entities: {entities_str}")
        
        if intent.suggested_timeframe:
            prompt_parts.append(f"Suggested Timeframe: {intent.suggested_timeframe}")
        
        # Add relevant operators
        if relevant_operators:
            prompt_parts.extend([
                "",
                "Relevant DataPrime Operators:",
            ])
            
            for op in relevant_operators[:5]:  # Limit to top 5
                op_info = self.operators_by_name[op['name']]
                prompt_parts.append(f"- {op_info['name']}: {op_info['description']}")
                if op_info['syntax']:
                    prompt_parts.append(f"  Syntax: {op_info['syntax']}")
        
        # Add relevant functions
        if relevant_functions:
            prompt_parts.extend([
                "",
                "Relevant Functions:",
            ])
            
            for func in relevant_functions[:3]:  # Limit to top 3
                func_info = self.functions_by_name[func['name']]
                prompt_parts.append(f"- {func_info['name']}: {func_info['description']}")
        
        # Add examples
        if examples:
            prompt_parts.extend([
                "",
                "Similar Examples:",
            ])
            
            for i, example in enumerate(examples, 1):
                prompt_parts.append(f"{i}. \"{example.user_input}\" → {example.dataprime_query}")
                if example.explanation:
                    prompt_parts.append(f"   Explanation: {example.explanation}")
        
        # Add key concepts
        prompt_parts.extend([
            "",
            "Key DataPrime Concepts:",
            "- All queries start with 'source logs' or 'source spans'",
            "- Use | (pipe) to chain operators",
            "- Field references: $m (metadata), $l (labels), $d (user data)",
            "- Time ranges: last 1h, last 1d, between timestamps",
            "- Filters use == for equality, contains() for text search",
            "",
            "Generate ONLY the DataPrime query. No explanations or markdown."
        ])
        
        return "\n".join(prompt_parts)
    
    def _get_relevant_operators_for_intent(self, intent: IntentResult) -> List[Dict[str, Any]]:
        """Get operators most relevant to the user's intent."""
        intent_to_operators = {
            IntentType.ERROR_ANALYSIS: ["source", "filter", "groupby", "aggregate", "orderby"],
            IntentType.PERFORMANCE: ["source", "filter", "groupby", "aggregate", "top", "percentile"],
            IntentType.AGGREGATION: ["source", "groupby", "aggregate", "count", "top", "bottom"],
            IntentType.SEARCH: ["source", "filter", "find", "lucene", "contains"],
            IntentType.TIME_ANALYSIS: ["source", "last", "between", "groupby", "roundTime"]
        }
        
        operator_names = intent_to_operators.get(intent.intent_type, ["source", "filter"])
        
        relevant_ops = []
        for op_name in operator_names:
            if op_name in self.operators_by_name:
                relevant_ops.append(self.operators_by_name[op_name])
        
        return relevant_ops
    
    def _get_relevant_functions_for_intent(self, intent: IntentResult) -> List[Dict[str, Any]]:
        """Get functions most relevant to the user's intent."""
        intent_to_functions = {
            IntentType.ERROR_ANALYSIS: ["contains", "count"],
            IntentType.PERFORMANCE: ["avg", "percentile", "max", "min"],
            IntentType.AGGREGATION: ["count", "sum", "avg", "distinct_count"],
            IntentType.SEARCH: ["contains", "matches", "startsWith"],
            IntentType.TIME_ANALYSIS: ["roundTime", "formatTimestamp", "now"]
        }
        
        function_names = intent_to_functions.get(intent.intent_type, ["contains"])
        
        relevant_funcs = []
        for func_name in function_names:
            if func_name in self.functions_by_name:
                relevant_funcs.append(self.functions_by_name[func_name])
        
        return relevant_funcs
    
    def get_operator_help(self, operator_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed help for a specific operator."""
        return self.operators_by_name.get(operator_name.lower())
    
    def get_function_help(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed help for a specific function."""
        return self.functions_by_name.get(function_name.lower())
    
    def suggest_query_completions(self, partial_query: str) -> List[str]:
        """Suggest query completions based on partial input."""
        suggestions = []
        
        # If query ends with |, suggest next operators
        if partial_query.strip().endswith('|'):
            common_next_ops = ['filter', 'groupby', 'aggregate', 'orderby', 'limit', 'top']
            suggestions.extend([f"{partial_query} {op}" for op in common_next_ops])
        
        # If query contains filter but no condition, suggest common filters
        elif 'filter' in partial_query and '==' not in partial_query:
            common_filters = [
                '$m.severity == \'Error\'',
                '$d.status_code >= 400',
                '$l.subsystemname == \'web-api\'',
                '$d.response_time > 1000'
            ]
            suggestions.extend([f"{partial_query} {filt}" for filt in common_filters])
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get a summary of the knowledge base contents."""
        return {
            "operators": {
                "total": len(self.operators_by_name),
                "categories": list(self.operators_by_category.keys())
            },
            "functions": {
                "total": len(self.functions_by_name),
                "categories": list(self.functions_by_category.keys())
            },
            "examples": {
                "total": len(self.enhanced_examples),
                "by_intent": {intent.value: len(examples) 
                            for intent, examples in self.examples_by_intent.items()}
            },
            "cheat_sheet_stats": self.cheat_sheet_knowledge["summary"]
        } 