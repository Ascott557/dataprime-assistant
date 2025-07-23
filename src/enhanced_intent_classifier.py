"""Enhanced intent classification using semantic similarity."""

import numpy as np
from typing import Dict, List, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass

from .knowledge_base import IntentType, IntentResult

@dataclass
class IntentPattern:
    intent_type: IntentType
    examples: List[str]
    confidence_threshold: float = 0.7

class SemanticIntentClassifier:
    """Enhanced intent classifier using semantic embeddings."""
    
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.intent_patterns = self._initialize_patterns()
        self.pattern_embeddings = self._compute_embeddings()
    
    def _initialize_patterns(self) -> Dict[str, IntentPattern]:
        """Initialize intent patterns with semantic examples."""
        return {
            "error_analysis": IntentPattern(
                intent_type=IntentType.ERROR_ANALYSIS,
                examples=[
                    "show me all errors",
                    "find failed requests",
                    "what went wrong",
                    "exceptions in the last hour",
                    "application crashes",
                    "failed transactions",
                    "server errors today"
                ]
            ),
            "performance": IntentPattern(
                intent_type=IntentType.PERFORMANCE,
                examples=[
                    "slow requests",
                    "high latency calls",
                    "response times",
                    "performance issues",
                    "timeout errors",
                    "which endpoints are slowest",
                    "database query performance"
                ]
            ),
            "aggregation": IntentPattern(
                intent_type=IntentType.AGGREGATION,
                examples=[
                    "count logs by service",
                    "total requests per hour",
                    "sum of all events",
                    "average response time",
                    "group by application",
                    "statistics by region",
                    "top 10 busiest endpoints"
                ]
            ),
            "search": IntentPattern(
                intent_type=IntentType.SEARCH,
                examples=[
                    "find logs containing",
                    "search for specific user",
                    "locate transaction ID",
                    "filter by message",
                    "events matching pattern",
                    "logs with specific field",
                    "find all occurrences"
                ]
            ),
            "time_analysis": IntentPattern(
                intent_type=IntentType.TIME_ANALYSIS,
                examples=[
                    "trends over time",
                    "events per hour",
                    "daily patterns",
                    "time series analysis",
                    "hourly breakdown",
                    "compare yesterday vs today",
                    "peak usage times"
                ]
            )
        }
    
    def _compute_embeddings(self) -> Dict[str, np.ndarray]:
        """Compute embeddings for all intent patterns."""
        embeddings = {}
        
        for intent_name, pattern in self.intent_patterns.items():
            pattern_embeddings = self.model.encode(pattern.examples)
            # Use mean embedding as the representative embedding
            embeddings[intent_name] = np.mean(pattern_embeddings, axis=0)
        
        return embeddings
    
    def classify(self, user_input: str) -> IntentResult:
        """Classify user input using semantic similarity."""
        # Get embedding for user input
        input_embedding = self.model.encode([user_input])
        
        # Calculate similarities with all intent patterns
        similarities = {}
        for intent_name, pattern_embedding in self.pattern_embeddings.items():
            similarity = cosine_similarity(
                input_embedding, 
                pattern_embedding.reshape(1, -1)
            )[0][0]
            similarities[intent_name] = similarity
        
        # Find best match
        best_intent = max(similarities, key=similarities.get)
        confidence = similarities[best_intent]
        
        # Extract additional information
        timeframe = self._extract_timeframe_enhanced(user_input)
        entities = self._extract_entities_enhanced(user_input)
        keywords = self._extract_relevant_keywords(user_input, best_intent)
        
        return IntentResult(
            intent_type=IntentType(best_intent),
            confidence=confidence,
            keywords_found=keywords,
            suggested_timeframe=timeframe,
            entities=entities
        )
    
    def _extract_timeframe_enhanced(self, user_input: str) -> str:
        """Enhanced timeframe extraction with more patterns."""
        import re
        
        patterns = {
            r"last (\d+) (hour|hours|h)": lambda m: f"last {m.group(1)}h",
            r"last (\d+) (minute|minutes|min|m)": lambda m: f"last {m.group(1)}m",
            r"last (\d+) (day|days|d)": lambda m: f"last {m.group(1)}d",
            r"past (\d+) (week|weeks|w)": lambda m: f"last {int(m.group(1)) * 7}d",
            r"yesterday": lambda m: "between @'now'-1d and @'now'",
            r"today": lambda m: "between @'now'/1d and @'now'",
            r"this week": lambda m: "between @'now'/1w and @'now'",
            r"this month": lambda m: "between @'now'/1M and @'now'",
            r"(\d+) minutes? ago": lambda m: f"last {m.group(1)}m",
            r"(\d+) hours? ago": lambda m: f"last {m.group(1)}h"
        }
        
        for pattern, formatter in patterns.items():
            match = re.search(pattern, user_input.lower())
            if match:
                return formatter(match)
        
        return "last 1h"  # Default fallback
    
    def _extract_entities_enhanced(self, user_input: str) -> Dict[str, any]:
        """Enhanced entity extraction with more patterns."""
        import re
        entities = {}
        
        # Service names
        service_patterns = [
            r"from (?:the )?([a-zA-Z][a-zA-Z0-9_-]*) service",
            r"in (?:the )?([a-zA-Z][a-zA-Z0-9_-]*) (?:app|application|microservice)",
            r"([a-zA-Z][a-zA-Z0-9_-]*)-service",
            r"service ([a-zA-Z][a-zA-Z0-9_-]*)"
        ]
        
        for pattern in service_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                entities["service"] = match.group(1)
                break
        
        # HTTP status codes
        status_patterns = [
            r"(?:status )?(?:code[s]? )?([45]\d{2})",  # 4xx/5xx errors
            r"(?:http )?([1-5]\d{2})",  # Any HTTP status
        ]
        
        for pattern in status_patterns:
            match = re.search(pattern, user_input)
            if match:
                entities["status_code"] = int(match.group(1))
                break
        
        # Endpoints/paths
        endpoint_patterns = [
            r"endpoint[s]? ([/a-zA-Z0-9_-]+)",
            r"path ([/a-zA-Z0-9_-]+)",
            r"(/api/[a-zA-Z0-9_/-]+)",
            r"(/v\d+/[a-zA-Z0-9_/-]+)"
        ]
        
        for pattern in endpoint_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                entities["endpoint"] = match.group(1)
                break
        
        # Performance thresholds
        perf_patterns = [
            r"(?:slower than|> |over )(\d+)(?:ms|milliseconds?)",
            r"(?:faster than|< |under )(\d+)(?:ms|milliseconds?)",
            r"latency (?:over|above) (\d+)(?:ms|milliseconds?)"
        ]
        
        for pattern in perf_patterns:
            match = re.search(pattern, user_input.lower())
            if match:
                entities["threshold_ms"] = int(match.group(1))
                break
        
        return entities
    
    def _extract_relevant_keywords(self, user_input: str, intent_type: str) -> List[str]:
        """Extract keywords relevant to the detected intent."""
        keywords = []
        words = user_input.lower().split()
        
        # Intent-specific keyword sets
        intent_keywords = {
            "error_analysis": ["error", "failed", "exception", "crash", "bug", "issue"],
            "performance": ["slow", "fast", "latency", "response", "timeout", "performance"],
            "aggregation": ["count", "sum", "average", "total", "group", "top", "statistics"],
            "search": ["find", "search", "filter", "contains", "match", "locate"],
            "time_analysis": ["trend", "over", "time", "hourly", "daily", "pattern", "series"]
        }
        
        relevant_keywords = intent_keywords.get(intent_type, [])
        keywords = [word for word in words if word in relevant_keywords]
        
        return keywords 