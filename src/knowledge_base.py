"""Knowledge base and intent classification for DataPrime Assistant."""

import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from data.dataprime_examples import (
    INTENT_MAPPINGS, 
    EXAMPLE_QUERIES, 
    get_examples_for_intent,
    get_pattern_for_intent
)

class IntentType(Enum):
    """Supported intent types for DataPrime queries."""
    ERROR_ANALYSIS = "error_analysis"
    PERFORMANCE = "performance"
    AGGREGATION = "aggregation"
    SEARCH = "search"
    TIME_ANALYSIS = "time_analysis"
    UNKNOWN = "unknown"

@dataclass
class IntentResult:
    """Result of intent classification."""
    intent_type: IntentType
    confidence: float
    keywords_found: List[str]
    suggested_timeframe: Optional[str] = None
    entities: Dict[str, Any] = None

@dataclass
class QueryExample:
    """Example query with metadata."""
    user_input: str
    dataprime_query: str
    intent_type: IntentType
    complexity: str = "simple"

class IntentClassifier:
    """Classifies user input to determine DataPrime query intent."""
    
    def __init__(self):
        self.intent_mappings = INTENT_MAPPINGS
        self.time_patterns = {
            r"last (\d+) (hour|hours|h)": lambda m: f"last {m.group(1)}h",
            r"last (\d+) (minute|minutes|m)": lambda m: f"last {m.group(1)}m",
            r"last (\d+) (day|days|d)": lambda m: f"last {m.group(1)}d",
            r"yesterday": lambda m: "between @'now'-1d and @'now'",
            r"today": lambda m: "between @'now'/1d and @'now'",
            r"this week": lambda m: "between @'now'/1w and @'now'"
        }
    
    def classify(self, user_input: str) -> IntentResult:
        """Classify user input and return intent with confidence."""
        user_input_lower = user_input.lower()
        
        # Calculate scores for each intent type
        intent_scores = {}
        keywords_found = {}
        
        for intent_name, intent_data in self.intent_mappings.items():
            keywords = intent_data.get("keywords", [])
            found_keywords = [kw for kw in keywords if kw in user_input_lower]
            
            if found_keywords:
                # Score based on keyword matches and their importance
                score = len(found_keywords) / len(keywords)
                intent_scores[intent_name] = score
                keywords_found[intent_name] = found_keywords
        
        # Determine best intent
        if not intent_scores:
            return IntentResult(
                intent_type=IntentType.UNKNOWN,
                confidence=0.0,
                keywords_found=[]
            )
        
        best_intent = max(intent_scores.keys(), key=lambda k: intent_scores[k])
        confidence = intent_scores[best_intent]
        
        # Extract time frame if present
        timeframe = self._extract_timeframe(user_input)
        if not timeframe:
            timeframe = self.intent_mappings[best_intent].get("default_timeframe")
        
        # Extract entities (services, endpoints, etc.)
        entities = self._extract_entities(user_input)
        
        return IntentResult(
            intent_type=IntentType(best_intent),
            confidence=confidence,
            keywords_found=keywords_found[best_intent],
            suggested_timeframe=timeframe,
            entities=entities
        )
    
    def _extract_timeframe(self, user_input: str) -> Optional[str]:
        """Extract timeframe from user input."""
        for pattern, formatter in self.time_patterns.items():
            match = re.search(pattern, user_input.lower())
            if match:
                return formatter(match)
        return None
    
    def _extract_entities(self, user_input: str) -> Dict[str, Any]:
        """Extract entities like service names, endpoints, etc."""
        entities = {}
        
        # Extract service/application names
        service_patterns = [
            r"from (?:the )?([a-zA-Z][a-zA-Z0-9_-]*) service",
            r"in (?:the )?([a-zA-Z][a-zA-Z0-9_-]*) application",
            r"([a-zA-Z][a-zA-Z0-9_-]*) microservice"
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                entities["service"] = match.group(1)
                break
        
        # Extract endpoints
        endpoint_pattern = r"endpoint[s]? ([/a-zA-Z0-9_-]+)"
        match = re.search(endpoint_pattern, user_input.lower())
        if match:
            entities["endpoint"] = match.group(1)
        
        # Extract status codes
        status_pattern = r"status code[s]? (\d{3})"
        match = re.search(status_pattern, user_input.lower())
        if match:
            entities["status_code"] = int(match.group(1))
        
        return entities

class DataPrimeKnowledgeBase:
    """Knowledge base for DataPrime query generation."""
    
    def __init__(self):
        self.classifier = IntentClassifier()
        self.examples = self._load_examples()
    
    def _load_examples(self) -> List[QueryExample]:
        """Load and categorize example queries."""
        examples = []
        
        for user_input, dataprime_query in EXAMPLE_QUERIES:
            intent_result = self.classifier.classify(user_input)
            
            # Determine complexity based on query structure
            complexity = "simple"
            if "|" in dataprime_query:
                pipe_count = dataprime_query.count("|")
                if pipe_count >= 3:
                    complexity = "complex"
                elif pipe_count >= 2:
                    complexity = "medium"
            
            examples.append(QueryExample(
                user_input=user_input,
                dataprime_query=dataprime_query,
                intent_type=intent_result.intent_type,
                complexity=complexity
            ))
        
        return examples
    
    def get_relevant_examples(self, intent: IntentResult, limit: int = 3) -> List[QueryExample]:
        """Get relevant examples for the given intent."""
        # Filter examples by intent type
        relevant_examples = [
            ex for ex in self.examples 
            if ex.intent_type == intent.intent_type
        ]
        
        # Sort by complexity (simple first) and limit
        relevant_examples.sort(key=lambda x: {"simple": 0, "medium": 1, "complex": 2}[x.complexity])
        
        return relevant_examples[:limit]
    
    def build_context_prompt(self, user_input: str, intent: IntentResult, examples: List[QueryExample]) -> str:
        """Build context prompt for OpenAI with examples and intent."""
        
        context = f"""You are a DataPrime query generator. Convert natural language to DataPrime syntax.

DataPrime is a query language similar to bash pipes. Basic structure:
source <dataset> [timeframe] | operator1 | operator2 | ...

Key operators:
- source: Set data source (logs, spans)
- filter: Filter events ($m.severity == 'Error', $d.response_time > 1000)
- groupby: Group and aggregate (groupby $l.subsystemname aggregate count())
- top: Get top results (top 10 by $d.response_time)
- orderby: Sort results (orderby $d.timestamp desc)

Field prefixes:
- $m.*: Metadata (timestamp, severity, logid)
- $l.*: Labels (applicationname, subsystemname)
- $d.*: User data (response_time, status_code, endpoint, message)

User Intent: {intent.intent_type.value}
Confidence: {intent.confidence:.2f}
Keywords found: {', '.join(intent.keywords_found)}
"""

        if intent.suggested_timeframe:
            context += f"Suggested timeframe: {intent.suggested_timeframe}\n"
        
        if intent.entities:
            context += f"Entities found: {intent.entities}\n"
        
        context += "\nRelevant examples:\n"
        for i, example in enumerate(examples, 1):
            context += f"{i}. Input: \"{example.user_input}\"\n"
            context += f"   Output: {example.dataprime_query}\n\n"
        
        context += f"""Now convert this input to DataPrime:
Input: "{user_input}"
Output: """
        
        return context
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query completion suggestions."""
        suggestions = []
        
        if not partial_query.strip():
            suggestions = ["source logs", "source spans", "source logs last 1h"]
        elif partial_query.strip() == "source logs":
            suggestions = [
                "source logs last 1h",
                "source logs last 1d", 
                "source logs | filter"
            ]
        elif "filter" in partial_query and not any(op in partial_query for op in ["groupby", "orderby", "top"]):
            suggestions = [
                partial_query + " | groupby $l.subsystemname aggregate count()",
                partial_query + " | orderby $m.timestamp desc",
                partial_query + " | top 10 by $d.response_time"
            ]
        
        return suggestions