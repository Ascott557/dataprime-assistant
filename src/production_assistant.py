"""Production-ready DataPrime Assistant with all improvements integrated."""

import asyncio
import time
from typing import Dict, Any, List, Optional
from opentelemetry import trace

from .enhanced_assistant import EnhancedDataPrimeAssistant, ConversationContext
from .smart_cache import MultiLevelCache
from .enhanced_intent_classifier import SemanticIntentClassifier
from .enhanced_knowledge_base import EnhancedDataPrimeKnowledgeBase
from .utils.config import get_config
from .utils.instrumentation import trace_function, add_dataprime_attributes

class ProductionDataPrimeAssistant:
    """Production-ready DataPrime Assistant with all enhancements."""
    
    def __init__(self):
        self.config = get_config()
        self.enhanced_assistant = EnhancedDataPrimeAssistant()
        self.cache = MultiLevelCache()
        self.tracer = trace.get_tracer(__name__)
        
        # Performance monitoring
        self.performance_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_response_time": 0.0,
            "error_rate": 0.0,
            "recent_queries": []
        }
        
        print("🚀 Production DataPrime Assistant initialized with:")
        print(f"   ✅ Semantic Intent Classification")
        print(f"   ✅ Multi-level Caching")
        print(f"   ✅ Conversation Context")
        print(f"   ✅ Robust Error Handling")
        print(f"   ✅ Performance Monitoring")
    
    @trace_function("production.generate_query")
    async def generate_query_async(self, user_input: str, user_id: str = "anonymous") -> Dict[str, Any]:
        """Generate query with full production features."""
        
        with self.tracer.start_as_current_span("production.query_generation") as span:
            start_time = time.time()
            
            # Add user context
            span.set_attribute("user_id", user_id)
            add_dataprime_attributes(span, user_input=user_input)
            
            try:
                # Step 1: Check cache first
                cached_result = self.cache.get_query(user_input)
                if cached_result:
                    span.set_attribute("cache_hit", True)
                    span.set_attribute("cache_type", cached_result.get("cache_info", {}).get("cache_hit", "unknown"))
                    
                    self._update_performance_stats(start_time, True, False)
                    return cached_result
                
                span.set_attribute("cache_hit", False)
                
                # Step 2: Generate using enhanced assistant
                result = await self.enhanced_assistant.generate_query_async(user_input)
                
                # Step 3: Cache the result if successful
                if "error" not in result:
                    self.cache.put_query(user_input, result)
                
                # Step 4: Update performance stats
                self._update_performance_stats(start_time, False, "error" in result)
                
                # Step 5: Add production metadata
                result["production_info"] = {
                    "user_id": user_id,
                    "version": "2.0.0",
                    "cache_stats": self.cache.get_stats(),
                    "performance_stats": self.get_performance_summary()
                }
                
                return result
                
            except Exception as e:
                span.set_attribute("error", str(e))
                self._update_performance_stats(start_time, False, True)
                
                return {
                    "user_input": user_input,
                    "error": "An unexpected error occurred. Please try again.",
                    "error_type": "production_error",
                    "user_id": user_id
                }
    
    def generate_query(self, user_input: str, user_id: str = "anonymous") -> Dict[str, Any]:
        """Synchronous wrapper for production query generation."""
        try:
            return asyncio.run(self.generate_query_async(user_input, user_id))
        except Exception as e:
            return {
                "user_input": user_input,
                "error": f"Production system error: {str(e)}",
                "error_type": "system_error",
                "user_id": user_id
            }
    
    def batch_generate_queries(self, queries: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Generate multiple queries efficiently."""
        async def process_batch():
            tasks = []
            for query_info in queries:
                user_input = query_info.get("query", "")
                user_id = query_info.get("user_id", "anonymous")
                tasks.append(self.generate_query_async(user_input, user_id))
            
            return await asyncio.gather(*tasks, return_exceptions=True)
        
        return asyncio.run(process_batch())
    
    def get_conversation_suggestions(self, user_input: str, context: ConversationContext) -> List[str]:
        """Get smart suggestions for continuing the conversation."""
        suggestions = []
        
        # Based on current intent
        if "error" in user_input.lower():
            suggestions.extend([
                "Show me error trends over the last day",
                "Which service has the most errors?",
                "What are the most common error messages?"
            ])
        
        elif "performance" in user_input.lower() or "slow" in user_input.lower():
            suggestions.extend([
                "Show me the slowest endpoints",
                "What's the 95th percentile response time?",
                "Compare performance with yesterday"
            ])
        
        # Based on conversation history
        if context.history:
            last_query = context.history[-1]
            if "groupby" in last_query.get("result", {}).get("generated_query", ""):
                suggestions.append("Show me the top 10 results from that query")
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    def explain_query_difference(self, query1: str, query2: str) -> Dict[str, Any]:
        """Explain the difference between two DataPrime queries."""
        differences = []
        
        # Simple difference detection
        query1_parts = query1.split("|")
        query2_parts = query2.split("|")
        
        if len(query1_parts) != len(query2_parts):
            differences.append(f"Different number of operations: {len(query1_parts)} vs {len(query2_parts)}")
        
        # More sophisticated analysis could be added here
        
        return {
            "query1": query1,
            "query2": query2,
            "differences": differences,
            "similarity_score": self._calculate_query_similarity(query1, query2)
        }
    
    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """Calculate similarity between two queries."""
        # Simple implementation - could be improved with semantic analysis
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0
    
    def _update_performance_stats(self, start_time: float, cache_hit: bool, is_error: bool):
        """Update performance statistics."""
        response_time = time.time() - start_time
        
        self.performance_stats["total_queries"] += 1
        
        if cache_hit:
            self.performance_stats["cache_hits"] += 1
        
        # Update running average
        total = self.performance_stats["total_queries"]
        current_avg = self.performance_stats["avg_response_time"]
        self.performance_stats["avg_response_time"] = (
            (current_avg * (total - 1) + response_time) / total
        )
        
        # Update error rate
        if is_error:
            error_count = self.performance_stats.get("errors", 0) + 1
            self.performance_stats["errors"] = error_count
            self.performance_stats["error_rate"] = error_count / total
        
        # Keep recent queries for analysis
        self.performance_stats["recent_queries"].append({
            "timestamp": time.time(),
            "response_time": response_time,
            "cache_hit": cache_hit,
            "is_error": is_error
        })
        
        # Keep only last 100 queries
        self.performance_stats["recent_queries"] = \
            self.performance_stats["recent_queries"][-100:]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for monitoring."""
        stats = self.performance_stats.copy()
        
        if stats["total_queries"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["total_queries"]
        else:
            stats["cache_hit_rate"] = 0.0
        
        # Recent performance (last 10 queries)
        recent = stats["recent_queries"][-10:]
        if recent:
            stats["recent_avg_response_time"] = sum(q["response_time"] for q in recent) / len(recent)
            stats["recent_cache_hit_rate"] = sum(1 for q in recent if q["cache_hit"]) / len(recent)
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            # Test basic functionality
            test_result = self.generate_query("show me logs from last hour")
            
            # Check cache health
            cache_stats = self.cache.get_stats()
            
            # Check performance
            perf_summary = self.get_performance_summary()
            
            is_healthy = (
                "error" not in test_result and
                perf_summary.get("error_rate", 0) < 0.1 and  # Less than 10% error rate
                perf_summary.get("avg_response_time", 0) < 5.0  # Less than 5s average
            )
            
            return {
                "status": "healthy" if is_healthy else "degraded",
                "timestamp": time.time(),
                "test_query_success": "error" not in test_result,
                "cache_stats": cache_stats,
                "performance": perf_summary,
                "version": "2.0.0"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
    
    def maintenance_cleanup(self) -> Dict[str, Any]:
        """Perform maintenance cleanup."""
        cleanup_results = {
            "timestamp": time.time(),
            "cache_cleanup": self.cache.cleanup_expired(),
            "performance_stats_reset": False
        }
        
        # Reset performance stats if they're getting too large
        if len(self.performance_stats.get("recent_queries", [])) > 1000:
            self.performance_stats["recent_queries"] = \
                self.performance_stats["recent_queries"][-100:]
            cleanup_results["performance_stats_reset"] = True
        
        return cleanup_results
    
    def export_analytics(self) -> Dict[str, Any]:
        """Export analytics data for analysis."""
        return {
            "timestamp": time.time(),
            "performance_stats": self.performance_stats,
            "cache_analytics": {
                "cache_stats": self.cache.get_stats(),
                "cache_exports": self.cache.query_cache.export_cache()
            },
            "conversation_stats": {
                "active_conversations": len(self.enhanced_assistant.conversation_context.history),
                "common_entities": self.enhanced_assistant.conversation_context.common_entities
            }
        } 