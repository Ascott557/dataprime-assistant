"""Main DataPrime Assistant class with full OpenTelemetry instrumentation."""

import time
from typing import Optional, List, Dict, Any
from openai import OpenAI
from opentelemetry import trace

from .knowledge_base import DataPrimeKnowledgeBase, IntentResult, QueryExample
from .utils.validation import DataPrimeValidator, ValidationResult
from .utils.instrumentation import (
    trace_intent_classification,
    trace_query_generation, 
    trace_query_validation,
    add_dataprime_attributes,
    get_current_span_context
)
from .utils.config import get_config

class DataPrimeAssistant:
    """AI-powered DataPrime query generator with full observability."""
    
    def __init__(self):
        """Initialize the DataPrime Assistant."""
        self.config = get_config()
        self.openai_client = OpenAI(api_key=self.config.openai_api_key)
        self.knowledge_base = DataPrimeKnowledgeBase()
        self.validator = DataPrimeValidator()
        self.tracer = trace.get_tracer(__name__)
        
        print(f"🤖 DataPrime Assistant initialized")
        print(f"   Model: {self.config.model_name}")
        print(f"   Service: {self.config.service_name}")
    
    def generate_query(self, user_input: str) -> Dict[str, Any]:
        """Generate a DataPrime query from natural language input."""
        
        with self.tracer.start_as_current_span("dataprime.assistant.generate_query") as span:
            start_time = time.time()
            
            # Add initial attributes
            add_dataprime_attributes(span, user_input=user_input)
            
            try:
                # Step 1: Classify intent
                intent = self._classify_intent(user_input)
                
                # Step 2: Get relevant examples
                examples = self._get_relevant_examples(intent)
                
                # Step 3: Generate query using OpenAI
                generated_query = self._generate_dataprime_query(user_input, intent, examples)
                
                # Step 4: Validate the generated query
                validation = self._validate_query(generated_query)
                
                # Step 5: Add final attributes
                add_dataprime_attributes(
                    span,
                    intent_type=intent.intent_type.value,
                    intent_confidence=intent.confidence,
                    generated_query=generated_query,
                    validation_score=validation.syntax_score,
                    complexity_score=validation.complexity_score,
                    examples_count=len(examples)
                )
                
                # Prepare result
                result = {
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
                            "input": ex.user_input,
                            "output": ex.dataprime_query
                        }
                        for ex in examples
                    ],
                    "generation_time": time.time() - start_time,
                    "trace_context": get_current_span_context()
                }
                
                span.set_attribute("dataprime.generation_success", True)
                span.set_attribute("dataprime.total_duration", result["generation_time"])
                
                return result
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                
                return {
                    "user_input": user_input,
                    "error": str(e),
                    "trace_context": get_current_span_context()
                }
    
    @trace_intent_classification
    def _classify_intent(self, user_input: str) -> IntentResult:
        """Classify the user's intent."""
        return self.knowledge_base.classifier.classify(user_input)
    
    def _get_relevant_examples(self, intent: IntentResult) -> List[QueryExample]:
        """Get relevant examples for the intent."""
        with self.tracer.start_as_current_span("dataprime.get_examples") as span:
            examples = self.knowledge_base.get_relevant_examples(intent, limit=3)
            span.set_attribute("examples.count", len(examples))
            span.set_attribute("examples.intent_type", intent.intent_type.value)
            return examples
    
    @trace_query_generation
    def _generate_dataprime_query(self, user_input: str, intent: IntentResult, examples: List[QueryExample]) -> str:
        """Generate DataPrime query using OpenAI."""
        
        # Build context prompt
        context_prompt = self.knowledge_base.build_context_prompt(user_input, intent, examples)
        
        # Call OpenAI (this will be automatically traced by llm-tracekit)
        response = self.openai_client.chat.completions.create(
            model=self.config.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are a DataPrime query expert. Generate only the DataPrime query, no explanations."
                },
                {
                    "role": "user", 
                    "content": context_prompt
                }
            ],
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature
        )
        
        generated_query = response.choices[0].message.content.strip()
        
        # Clean up the response (remove any extra text)
        if "Output:" in generated_query:
            generated_query = generated_query.split("Output:")[-1].strip()
        
        # Remove any markdown formatting
        generated_query = generated_query.replace("```", "").strip()
        
        return generated_query
    
    @trace_query_validation
    def _validate_query(self, query: str) -> ValidationResult:
        """Validate the generated DataPrime query."""
        return self.validator.validate(query)
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query completion suggestions."""
        with self.tracer.start_as_current_span("dataprime.suggestions") as span:
            span.set_attribute("partial_query", partial_query)
            suggestions = self.knowledge_base.get_query_suggestions(partial_query)
            span.set_attribute("suggestions.count", len(suggestions))
            return suggestions
    
    def explain_query(self, query: str) -> Dict[str, Any]:
        """Explain what a DataPrime query does."""
        with self.tracer.start_as_current_span("dataprime.explain_query") as span:
            span.set_attribute("query_to_explain", query)
            
            try:
                # Validate first
                validation = self._validate_query(query)
                
                # Build explanation prompt
                explanation_prompt = f"""Explain what this DataPrime query does in simple terms:

Query: {query}

Explain:
1. What data source it uses
2. What filters are applied
3. What transformations are performed
4. What the output will contain

Keep it concise and user-friendly."""

                response = self.openai_client.chat.completions.create(
                    model=self.config.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a DataPrime expert. Explain queries clearly and concisely."
                        },
                        {
                            "role": "user",
                            "content": explanation_prompt
                        }
                    ],
                    max_tokens=500,
                    temperature=0.3
                )
                
                explanation = response.choices[0].message.content.strip()
                
                return {
                    "query": query,
                    "explanation": explanation,
                    "validation": {
                        "is_valid": validation.is_valid,
                        "syntax_score": validation.syntax_score,
                        "complexity_score": validation.complexity_score
                    }
                }
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                return {
                    "query": query,
                    "error": f"Could not explain query: {str(e)}"
                }
    
    def record_feedback(self, query_result: Dict[str, Any], rating: int, comment: str = "") -> None:
        """Record user feedback for improving the assistant."""
        with self.tracer.start_as_current_span("dataprime.record_feedback") as span:
            span.set_attribute("feedback.rating", rating)
            span.set_attribute("feedback.comment", comment)
            span.set_attribute("feedback.query", query_result.get("generated_query", ""))
            
            # Add feedback as span event
            span.add_event(
                "user_feedback_recorded",
                {
                    "rating": rating,
                    "comment": comment,
                    "user_input": query_result.get("user_input", ""),
                    "generated_query": query_result.get("generated_query", ""),
                    "validation_score": query_result.get("validation", {}).get("syntax_score", 0)
                }
            )
            
            print(f"📝 Feedback recorded: {rating}/5 - {comment}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get assistant usage statistics."""
        # In a real implementation, this would query the observability backend
        # For now, return basic info
        return {
            "service_name": self.config.service_name,
            "model": self.config.model_name,
            "version": "1.0.0",
            "status": "healthy"
        }