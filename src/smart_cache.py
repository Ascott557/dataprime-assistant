"""Smart caching system for DataPrime Assistant with semantic similarity."""

import time
import hashlib
import json
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

@dataclass
class CacheEntry:
    """Cached query generation result."""
    user_input: str
    result: Dict[str, Any]
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0.0
    embedding: Optional[np.ndarray] = None

class SemanticQueryCache:
    """Smart cache that finds similar queries using semantic similarity."""
    
    def __init__(self, max_size: int = 1000, similarity_threshold: float = 0.85, ttl_hours: int = 24):
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_hours * 3600
        
        # Storage
        self.cache: Dict[str, CacheEntry] = {}
        self.embeddings_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "semantic_matches": 0
        }
    
    def _generate_key(self, user_input: str) -> str:
        """Generate cache key from user input."""
        return hashlib.sha256(user_input.lower().strip().encode()).hexdigest()[:16]
    
    def get(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Get cached result, checking for exact and semantic matches."""
        current_time = time.time()
        
        # Try exact match first
        exact_key = self._generate_key(user_input)
        if exact_key in self.cache:
            entry = self.cache[exact_key]
            
            # Check if not expired
            if current_time - entry.timestamp < self.ttl_seconds:
                entry.access_count += 1
                entry.last_accessed = current_time
                self.stats["hits"] += 1
                
                # Add cache metadata to result
                result = entry.result.copy()
                result["cache_info"] = {
                    "cache_hit": "exact",
                    "original_query": entry.user_input,
                    "age_seconds": current_time - entry.timestamp,
                    "access_count": entry.access_count
                }
                return result
            else:
                # Expired, remove
                del self.cache[exact_key]
        
        # Try semantic similarity match
        semantic_result = self._find_semantic_match(user_input)
        if semantic_result:
            entry, similarity = semantic_result
            entry.access_count += 1
            entry.last_accessed = current_time
            self.stats["hits"] += 1
            self.stats["semantic_matches"] += 1
            
            # Modify result to reflect the semantic match
            result = entry.result.copy()
            result["cache_info"] = {
                "cache_hit": "semantic",
                "similarity": similarity,
                "original_query": entry.user_input,
                "age_seconds": current_time - entry.timestamp,
                "access_count": entry.access_count
            }
            return result
        
        self.stats["misses"] += 1
        return None
    
    def put(self, user_input: str, result: Dict[str, Any]) -> None:
        """Cache a query generation result."""
        current_time = time.time()
        key = self._generate_key(user_input)
        
        # Generate embedding for semantic matching
        embedding = self.embeddings_model.encode([user_input])[0]
        
        entry = CacheEntry(
            user_input=user_input,
            result=result,
            timestamp=current_time,
            last_accessed=current_time,
            embedding=embedding
        )
        
        # Check if we need to evict
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = entry
    
    def _find_semantic_match(self, user_input: str) -> Optional[Tuple[CacheEntry, float]]:
        """Find semantically similar cached query."""
        if not self.cache:
            return None
        
        # Get embedding for input
        input_embedding = self.embeddings_model.encode([user_input])
        
        best_match = None
        best_similarity = 0.0
        current_time = time.time()
        
        for entry in self.cache.values():
            # Skip expired entries
            if current_time - entry.timestamp >= self.ttl_seconds:
                continue
            
            if entry.embedding is not None:
                # Calculate similarity
                similarity = cosine_similarity(
                    input_embedding, 
                    entry.embedding.reshape(1, -1)
                )[0][0]
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = entry
        
        return (best_match, best_similarity) if best_match else None
    
    def _evict_oldest(self) -> None:
        """Evict least recently used entries."""
        if not self.cache:
            return
        
        # Sort by last accessed time
        sorted_entries = sorted(
            self.cache.items(), 
            key=lambda x: x[1].last_accessed
        )
        
        # Remove oldest 20%
        evict_count = max(1, len(sorted_entries) // 5)
        
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self.cache[key]
            self.stats["evictions"] += 1
    
    def invalidate_expired(self) -> int:
        """Remove expired entries and return count."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry.timestamp >= self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total_requests if total_requests > 0 else 0.0
        
        return {
            **self.stats,
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "semantic_hit_rate": self.stats["semantic_matches"] / self.stats["hits"] if self.stats["hits"] > 0 else 0.0
        }
    
    def clear(self) -> None:
        """Clear all cached entries."""
        self.cache.clear()
        self.stats = {key: 0 for key in self.stats.keys()}
    
    def export_cache(self) -> List[Dict[str, Any]]:
        """Export cache entries for analysis."""
        exports = []
        for entry in self.cache.values():
            export_entry = {
                "user_input": entry.user_input,
                "timestamp": entry.timestamp,
                "access_count": entry.access_count,
                "last_accessed": entry.last_accessed,
                "intent_type": entry.result.get("intent", {}).get("type"),
                "generated_query": entry.result.get("generated_query"),
                "validation_score": entry.result.get("validation", {}).get("syntax_score")
            }
            exports.append(export_entry)
        
        return exports

class MultiLevelCache:
    """Multi-level cache system for different types of data."""
    
    def __init__(self):
        # L1: Intent classification cache
        self.intent_cache: Dict[str, Any] = {}
        
        # L2: Query generation cache (semantic)
        self.query_cache = SemanticQueryCache(max_size=500)
        
        # L3: Validation results cache
        self.validation_cache: Dict[str, Any] = {}
        
        # L4: Examples cache
        self.examples_cache: Dict[str, List[Any]] = {}
    
    def get_intent(self, user_input: str) -> Optional[Any]:
        """Get cached intent classification."""
        key = hashlib.sha256(user_input.lower().encode()).hexdigest()[:16]
        return self.intent_cache.get(key)
    
    def put_intent(self, user_input: str, intent: Any) -> None:
        """Cache intent classification result."""
        key = hashlib.sha256(user_input.lower().encode()).hexdigest()[:16]
        self.intent_cache[key] = {
            "intent": intent,
            "timestamp": time.time()
        }
        
        # Keep cache size manageable
        if len(self.intent_cache) > 1000:
            # Remove oldest 200 entries
            sorted_items = sorted(
                self.intent_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for i in range(200):
                del self.intent_cache[sorted_items[i][0]]
    
    def get_query(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Get cached query generation result."""
        return self.query_cache.get(user_input)
    
    def put_query(self, user_input: str, result: Dict[str, Any]) -> None:
        """Cache query generation result."""
        self.query_cache.put(user_input, result)
    
    def get_validation(self, query: str) -> Optional[Any]:
        """Get cached validation result."""
        key = hashlib.sha256(query.encode()).hexdigest()[:16]
        cached = self.validation_cache.get(key)
        if cached and time.time() - cached["timestamp"] < 3600:  # 1 hour TTL
            return cached["validation"]
        return None
    
    def put_validation(self, query: str, validation: Any) -> None:
        """Cache validation result."""
        key = hashlib.sha256(query.encode()).hexdigest()[:16]
        self.validation_cache[key] = {
            "validation": validation,
            "timestamp": time.time()
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        return {
            "intent_cache_size": len(self.intent_cache),
            "query_cache_stats": self.query_cache.get_stats(),
            "validation_cache_size": len(self.validation_cache),
            "examples_cache_size": len(self.examples_cache)
        }
    
    def cleanup_expired(self) -> Dict[str, int]:
        """Clean up expired entries across all caches."""
        current_time = time.time()
        
        # Intent cache cleanup (1 hour TTL)
        intent_expired = []
        for key, value in self.intent_cache.items():
            if current_time - value["timestamp"] > 3600:
                intent_expired.append(key)
        
        for key in intent_expired:
            del self.intent_cache[key]
        
        # Validation cache cleanup (1 hour TTL) 
        validation_expired = []
        for key, value in self.validation_cache.items():
            if current_time - value["timestamp"] > 3600:
                validation_expired.append(key)
        
        for key in validation_expired:
            del self.validation_cache[key]
        
        # Query cache cleanup (handled internally)
        query_expired = self.query_cache.invalidate_expired()
        
        return {
            "intent_expired": len(intent_expired),
            "validation_expired": len(validation_expired),
            "query_expired": query_expired
        } 