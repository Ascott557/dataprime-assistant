"""Enhanced DataPrime Assistant with robust error handling and recovery."""

import asyncio
import time
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass
from enum import Enum
from openai import OpenAI, OpenAIError
from opentelemetry import trace

from .dataprime_assistant import DataPrimeAssistant
from .enhanced_intent_classifier import SemanticIntentClassifier
from .enhanced_knowledge_base import EnhancedDataPrimeKnowledgeBase
from .knowledge_base import IntentResult, QueryExample
from .utils.validation import ValidationResult
from .utils.config import get_config

class ErrorType(Enum):
    """Types of errors that can occur."""
    OPENAI_API_ERROR = "openai_api_error"
    INTENT_CLASSIFICATION_ERROR = "intent_classification_error"
    QUERY_GENERATION_ERROR = "query_generation_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"

@dataclass
class QueryGenerationError:
    """Structured error information."""
    error_type: ErrorType
    message: str
    recovery_suggestions: List[str]
    user_friendly_message: str
    retry_possible: bool = True

class ConversationContext:
    """Manages conversation history and context."""
    
    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.user_preferences = {}
        self.common_entities = {}  # Frequently mentioned services, endpoints, etc.
    
    def add_interaction(self, user_input: str, result: Dict[str, Any]):
        """Add an interaction to the conversation history."""
        self.history.append({
            "timestamp": time.time(),
            "user_input": user_input,
            "result": result,
            "intent": result.get("intent", {}),
            "entities": result.get("intent", {}).get("entities", {})
        })
        
        # Update common entities
        self._update_common_entities(result.get("intent", {}).get("entities", {}))
        
        # Keep only last 10 interactions
        self.history = self.history[-10:]
    
    def _update_common_entities(self, entities: Dict[str, Any]):
        """Track frequently mentioned entities."""
        for key, value in entities.items():
            if key not in self.common_entities:
                self.common_entities[key] = {}
            if value not in self.common_entities[key]:
                self.common_entities[key][value] = 0
            self.common_entities[key][value] += 1
    
    def get_context_for_prompt(self) -> str:
        """Generate context string for query generation."""
        if not self.history:
            return ""
        
        context_parts = ["Previous queries in this conversation:"]
        
        for interaction in self.history[-3:]:  # Last 3 interactions
            context_parts.append(f"User: {interaction['user_input']}")
            if "generated_query" in interaction["result"]:
                context_parts.append(f"Query: {interaction['result']['generated_query']}")
        
        # Add common entities
        if self.common_entities:
            context_parts.append("Frequently mentioned:")
            for entity_type, values in self.common_entities.items():
                most_common = max(values.items(), key=lambda x: x[1])
                context_parts.append(f"- {entity_type}: {most_common[0]}")
        
        return "\n".join(context_parts)

class EnhancedDataPrimeAssistant:
    """Enhanced DataPrime Assistant with robust error handling."""
    
    def __init__(self):
        self.config = get_config()
        self.openai_client = OpenAI(api_key=self.config.openai_api_key)
        self.semantic_classifier = SemanticIntentClassifier()
        self.enhanced_knowledge_base = EnhancedDataPrimeKnowledgeBase()
        self.conversation_context = ConversationContext()
        self.tracer = trace.get_tracer(__name__)
        
        # Fallback assistant for simple cases
        self.simple_assistant = DataPrimeAssistant()
        
        print(f"🤖 Enhanced DataPrime Assistant initialized with comprehensive knowledge base")
    
    async def generate_query_async(self, user_input: str, max_retries: int = 3) -> Dict[str, Any]:
        """Generate query with async support and retry logic."""
        
        with self.tracer.start_as_current_span("enhanced.generate_query") as span:
            span.set_attribute("user_input", user_input)
            span.set_attribute("max_retries", max_retries)
            
            start_time = time.time()
            
            for attempt in range(max_retries):
                try:
                    span.set_attribute("attempt_number", attempt + 1)
                    
                    # Step 1: Enhanced intent classification
                    intent = await self._classify_intent_with_timeout(user_input)
                    
                    # Step 2: Get relevant examples with context
                    examples = await self._get_contextual_examples(intent, user_input)
                    
                    # Step 3: Generate query with enhanced prompting
                    generated_query = await self._generate_query_with_context(
                        user_input, intent, examples
                    )
                    
                    # Step 4: Validate with enhanced checks
                    validation = await self._validate_query_enhanced(generated_query)
                    
                    # Step 5: Build result
                    result = self._build_result(
                        user_input, intent, generated_query, validation, 
                        examples, time.time() - start_time
                    )
                    
                    # Add to conversation context
                    self.conversation_context.add_interaction(user_input, result)
                    
                    span.set_attribute("generation_success", True)
                    return result
                    
                except Exception as e:
                    error_info = self._classify_error(e)
                    span.set_attribute(f"attempt_{attempt + 1}_error", str(e))
                    
                    if not error_info.retry_possible or attempt == max_retries - 1:
                        # Final failure
                        return self._handle_final_error(user_input, error_info)
                    
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(2 ** attempt)
    
    def generate_query(self, user_input: str) -> Dict[str, Any]:
        """Synchronous wrapper for async generation."""
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in an event loop, need to use a different approach
                import concurrent.futures
                import nest_asyncio
                
                # Try to install nest_asyncio to allow nested event loops
                try:
                    nest_asyncio.apply()
                    return loop.run_until_complete(self.generate_query_async(user_input))
                except:
                    # If nest_asyncio doesn't work, run in thread pool
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self.generate_query_async(user_input))
                        return future.result()
            except RuntimeError:
                # No event loop running, safe to create one
                return asyncio.run(self.generate_query_async(user_input))
        except Exception as e:
            # Fall back to simple assistant
            print(f"⚠️ Falling back to simple assistant due to: {e}")
            return self.simple_assistant.generate_query(user_input)
    
    async def _classify_intent_with_timeout(self, user_input: str, timeout: int = 10) -> IntentResult:
        """Classify intent with timeout protection."""
        try:
            return await asyncio.wait_for(
                asyncio.create_task(self._classify_intent_async(user_input)),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise TimeoutError(f"Intent classification timed out after {timeout}s")
    
    async def _classify_intent_async(self, user_input: str) -> IntentResult:
        """Async intent classification."""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.semantic_classifier.classify, user_input
        )
    
    async def _get_contextual_examples(self, intent: IntentResult, user_input: str) -> List:
        """Get examples with conversation context using enhanced knowledge base."""
        # Get enhanced examples from the comprehensive knowledge base
        enhanced_examples = self.enhanced_knowledge_base.get_relevant_examples_enhanced(intent, limit=2)
        
        # Add contextually relevant examples from conversation history
        contextual_examples = []
        for interaction in self.conversation_context.history:
            if interaction["intent"].get("type") == intent.intent_type.value:
                contextual_examples.append({
                    "user_input": interaction["user_input"],
                    "dataprime_query": interaction["result"].get("generated_query", ""),
                    "explanation": "From conversation history"
                })
        
        # Convert enhanced examples to simple format for compatibility
        simple_examples = []
        for ex in enhanced_examples:
            simple_examples.append({
                "user_input": ex.user_input,
                "dataprime_query": ex.dataprime_query,
                "explanation": ex.explanation
            })
        
        return simple_examples + contextual_examples[:1]  # Limit total examples
    
    async def _generate_query_with_context(
        self, user_input: str, intent: IntentResult, examples: List
    ) -> str:
        """Generate query with conversation context using enhanced knowledge base."""
        
        # Build enhanced prompt using the comprehensive knowledge base
        enhanced_prompt = self.enhanced_knowledge_base.build_enhanced_context_prompt(
            user_input, intent, examples
        )
        
        # Add conversation context if available
        if self.conversation_context.history:
            context = self.conversation_context.get_context_for_prompt()
            enhanced_prompt += f"\n\nConversation Context:\n{context}"
        
        try:
            response = await self._call_openai_with_retry(
                messages=[
                    {"role": "system", "content": "You are an expert DataPrime query generator. Generate ONLY the DataPrime query, no explanations."},
                    {"role": "user", "content": enhanced_prompt}
                ]
            )
            
            generated_query = response.choices[0].message.content.strip()
            return self._clean_generated_query(generated_query)
            
        except Exception as e:
            raise QueryGenerationError(
                error_type=ErrorType.QUERY_GENERATION_ERROR,
                message=f"Failed to generate query: {str(e)}",
                recovery_suggestions=[
                    "Try rephrasing your request",
                    "Be more specific about what you're looking for",
                    "Include a time range in your request"
                ],
                user_friendly_message="I had trouble understanding your request. Could you try rephrasing it?"
            )
    
    async def _call_openai_with_retry(self, messages: List[Dict], max_retries: int = 2) -> Any:
        """Call OpenAI with retry logic for rate limits."""
        for attempt in range(max_retries):
            try:
                response = await asyncio.create_task(
                    asyncio.to_thread(
                        self.openai_client.chat.completions.create,
                        model=self.config.model_name,
                        messages=messages,
                        max_tokens=self.config.max_tokens,
                        temperature=self.config.temperature
                    )
                )
                return response
                
            except OpenAIError as e:
                if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
    
    def _classify_error(self, error: Exception) -> QueryGenerationError:
        """Classify error and provide recovery suggestions."""
        error_str = str(error).lower()
        
        if "rate_limit" in error_str or "quota" in error_str:
            return QueryGenerationError(
                error_type=ErrorType.RATE_LIMIT_ERROR,
                message="Rate limit exceeded",
                recovery_suggestions=[
                    "Wait a moment and try again",
                    "Check your OpenAI API usage"
                ],
                user_friendly_message="I'm getting too many requests right now. Please try again in a moment.",
                retry_possible=True
            )
        
        elif "timeout" in error_str:
            return QueryGenerationError(
                error_type=ErrorType.TIMEOUT_ERROR,
                message="Request timed out",
                recovery_suggestions=[
                    "Try a simpler request",
                    "Check your internet connection"
                ],
                user_friendly_message="The request took too long. Could you try a simpler query?",
                retry_possible=True
            )
        
        elif "api" in error_str or "openai" in error_str:
            return QueryGenerationError(
                error_type=ErrorType.OPENAI_API_ERROR,
                message=f"OpenAI API error: {error}",
                recovery_suggestions=[
                    "Check your API key configuration",
                    "Verify your OpenAI account status"
                ],
                user_friendly_message="There's an issue with the AI service. Please check your configuration.",
                retry_possible=False
            )
        
        else:
            return QueryGenerationError(
                error_type=ErrorType.QUERY_GENERATION_ERROR,
                message=f"Unknown error: {error}",
                recovery_suggestions=[
                    "Try rephrasing your request",
                    "Contact support if the issue persists"
                ],
                user_friendly_message="Something unexpected happened. Could you try rephrasing your request?",
                retry_possible=True
            )
    
    def _handle_final_error(self, user_input: str, error_info: QueryGenerationError) -> Dict[str, Any]:
        """Handle final error after all retries failed."""
        return {
            "user_input": user_input,
            "error": error_info.user_friendly_message,
            "error_type": error_info.error_type.value,
            "recovery_suggestions": error_info.recovery_suggestions,
            "technical_message": error_info.message
        }
    
    def _clean_generated_query(self, query: str) -> str:
        """Clean and validate generated query format."""
        # Remove markdown formatting
        query = query.replace("```sql", "").replace("```", "").strip()
        
        # Remove common prefixes
        if query.startswith("Query:"):
            query = query[6:].strip()
        if query.startswith("DataPrime:"):
            query = query[10:].strip()
        
        return query
    
    def _format_examples(self, examples: List) -> str:
        """Format examples for prompt."""
        if not examples:
            return "No specific examples available."
        
        formatted = []
        for i, example in enumerate(examples, 1):
            if isinstance(example, dict):
                # Handle dict format (from enhanced knowledge base or conversation history)
                user_input = example.get('user_input', '')
                query = example.get('dataprime_query', '')
                explanation = example.get('explanation', '')
                
                formatted.append(f"{i}. \"{user_input}\" → {query}")
                if explanation:
                    formatted.append(f"   Explanation: {explanation}")
            else:
                # Handle object format (fallback)
                if hasattr(example, 'user_input') and hasattr(example, 'dataprime_query'):
                    formatted.append(f"{i}. \"{example.user_input}\" → {example.dataprime_query}")
        
        return "\n".join(formatted)
    
    async def _validate_query_enhanced(self, query: str) -> ValidationResult:
        """Enhanced validation with async support."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.simple_assistant._validate_query, query
        )
    
    def _build_result(self, user_input: str, intent: IntentResult, generated_query: str, 
                     validation: ValidationResult, examples: List, generation_time: float) -> Dict[str, Any]:
        """Build standardized result dictionary."""
        return {
            "user_input": user_input,
            "generated_query": generated_query,
            "intent": {
                "type": intent.intent_type.value,
                "confidence": intent.confidence,
                "keywords": intent.keywords_found,
                "timeframe": intent.suggested_timeframe,
                "entities": intent.entities or {}
            },
            "validation": {
                "is_valid": validation.is_valid,
                "syntax_score": validation.syntax_score,
                "complexity_score": validation.complexity_score,
                "estimated_cost": validation.estimated_cost,
                "issues": [
                    {
                        "level": issue.level.value,
                        "message": issue.message,
                        "suggestion": issue.suggestion
                    }
                    for issue in validation.issues
                ],
                "performance_warnings": validation.performance_warnings
            },
            "examples_used": [
                {
                    "input": getattr(ex, 'user_input', ex.get('user_input', '')),
                    "output": getattr(ex, 'dataprime_query', ex.get('dataprime_query', ''))
                }
                for ex in examples
            ],
            "generation_time": generation_time,
            "conversation_context": len(self.conversation_context.history) > 0
        } 

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for the enhanced assistant."""
        # Enhanced assistant doesn't have smart cache, it uses the knowledge base
        return {
            "assistant_type": "enhanced",
            "model": self.config.model_name,
            "knowledge_base_operators": len(getattr(self.enhanced_knowledge_base, 'operators', {})),
            "knowledge_base_examples": len(getattr(self.enhanced_knowledge_base, 'enhanced_examples', [])),
            "cache_enabled": False,
            "cache_stats": {"status": "not_implemented_in_enhanced_assistant"},
            "conversation_history_length": len(self.conversation_context.history),
            "features": {
                "semantic_intent_classification": True,
                "enhanced_knowledge_base": True,
                "smart_caching": False,
                "conversation_context": True,
                "performance_monitoring": True
            }
        } 