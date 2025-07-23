"""DataPrime Assistant with OpenTelemetry GenAI Semantic Conventions.

This module implements a DataPrime Assistant that follows the official OpenTelemetry
GenAI semantic conventions for comprehensive observability of GenAI operations.
"""

import time
import uuid
from typing import Optional, List, Dict, Any
from openai import OpenAI
from opentelemetry import trace, baggage

from .knowledge_base import DataPrimeKnowledgeBase, IntentResult, QueryExample
from .utils.validation import DataPrimeValidator, ValidationResult
from .utils.config import get_config
from .utils.genai_instrumentation import (
    GenAISpanManager,
    GenAIOperationName,
    GenAISystem,
    GenAIOutputType,
    GenAIRequestConfig,
    GenAIResponse,
    GenAIPromptEvent,
    GenAICompletionEvent,
    add_genai_prompt_event,
    add_genai_completion_event,
    set_genai_response_attributes,
    genai_agent_decorator,
    genai_inference_decorator
)

class GenAIDataPrimeAssistant:
    """DataPrime Assistant with OpenTelemetry GenAI semantic conventions."""
    
    def __init__(self):
        """Initialize the GenAI DataPrime Assistant."""
        self.config = get_config()
        self.openai_client = OpenAI(api_key=self.config.openai_api_key)
        self.knowledge_base = DataPrimeKnowledgeBase()
        self.validator = DataPrimeValidator()
        self.tracer = trace.get_tracer(__name__)
        
        # Agent configuration following GenAI conventions
        self.agent_name = "DataPrime Query Generator"
        self.agent_id = "dataprime-assistant-v2"
        self.agent_description = "AI agent that converts natural language to DataPrime queries for log analysis"
        
        print(f"🤖 GenAI DataPrime Assistant initialized")
        print(f"   Agent: {self.agent_name}")
        print(f"   Model: {self.config.model_name}")
        print(f"   Service: {self.config.service_name}")
    
    @genai_agent_decorator(
        operation_name=GenAIOperationName.INVOKE_AGENT,
        agent_name="DataPrime Query Generator",
        agent_description="AI agent that converts natural language to DataPrime queries for log analysis",
        system=GenAISystem.CUSTOM
    )
    def generate_query(self, user_input: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a DataPrime query from natural language input."""
        
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:16]}"
            
        # Add conversation ID to baggage for context propagation
        baggage.set_baggage("conversation.id", conversation_id)
        baggage.set_baggage("user.query", user_input)
        
        start_time = time.time()
        
        try:
            # Step 1: Classify intent (tool execution)
            intent = self._classify_intent(user_input)
            
            # Step 2: Get relevant examples (tool execution)
            examples = self._get_relevant_examples(intent)
            
            # Step 3: Generate query using OpenAI (GenAI inference)
            generated_query = self._generate_dataprime_query(
                user_input, intent, examples, conversation_id
            )
            
            # Step 4: Validate the generated query (tool execution)
            validation = self._validate_query(generated_query)
            
            # Prepare result with GenAI context
            result = {
                "user_input": user_input,
                "generated_query": generated_query,
                "conversation_id": conversation_id,
                "agent_info": {
                    "name": self.agent_name,
                    "id": self.agent_id,
                    "description": self.agent_description
                },
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
                "model": self.config.model_name,
                "system": GenAISystem.OPENAI
            }
            
            return result
            
        except Exception as e:
            return {
                "user_input": user_input,
                "conversation_id": conversation_id,
                "error": str(e),
                "agent_info": {
                    "name": self.agent_name,
                    "id": self.agent_id
                }
            }
    
    def _classify_intent(self, user_input: str) -> IntentResult:
        """Classify the user's intent using tool execution span."""
        with GenAISpanManager.create_tool_execution_span(
            tool_name="intent_classifier",
            tool_description="Classifies user intent for DataPrime query generation"
        ) as span:
            if span:
                span.set_attribute("input.text", user_input)
                span.set_attribute("input.length", len(user_input))
            
            result = self.knowledge_base.classifier.classify(user_input)
            
            if span:
                span.set_attribute("intent.type", result.intent_type.value)
                span.set_attribute("intent.confidence", result.confidence)
                span.set_attribute("intent.keywords_count", len(result.keywords_found))
                if result.suggested_timeframe:
                    span.set_attribute("intent.timeframe", result.suggested_timeframe)
                    
            return result
    
    def _get_relevant_examples(self, intent: IntentResult) -> List[QueryExample]:
        """Get relevant examples using tool execution span."""
        with GenAISpanManager.create_tool_execution_span(
            tool_name="example_retriever",
            tool_description="Retrieves relevant examples from DataPrime knowledge base"
        ) as span:
            if span:
                span.set_attribute("intent.type", intent.intent_type.value)
                
            examples = self.knowledge_base.get_relevant_examples(intent, limit=3)
            
            if span:
                span.set_attribute("examples.count", len(examples))
                span.set_attribute("examples.limit", 3)
                
            return examples
    
    def _generate_dataprime_query(
        self, 
        user_input: str, 
        intent: IntentResult, 
        examples: List[QueryExample],
        conversation_id: str
    ) -> str:
        """Generate DataPrime query using OpenAI with GenAI semantic conventions."""
        
        # Build request configuration
        request_config = GenAIRequestConfig(
            model=self.config.model_name,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens
        )
        
        with GenAISpanManager.create_inference_span(
            operation_name=GenAIOperationName.CHAT,
            request_config=request_config,
            system=GenAISystem.OPENAI,
            conversation_id=conversation_id,
            output_type=GenAIOutputType.TEXT
        ) as span:
            
            # Build context prompt
            context_prompt = self.knowledge_base.build_context_prompt(user_input, intent, examples)
            
            # Add prompt event
            if span:
                add_genai_prompt_event(
                    span, 
                    GenAIPromptEvent(
                        prompt=context_prompt,
                        role="user"
                    )
                )
            
            # Call OpenAI API
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
            
            # Extract generated query
            generated_query = response.choices[0].message.content.strip()
            
            # Clean up the response
            if "Output:" in generated_query:
                generated_query = generated_query.split("Output:")[-1].strip()
            generated_query = generated_query.replace("```", "").strip()
            
            # Add completion event
            if span:
                add_genai_completion_event(
                    span,
                    GenAICompletionEvent(
                        completion=generated_query,
                        role="assistant"
                    )
                )
                
                # Set response attributes
                genai_response = GenAIResponse(
                    id=response.id,
                    model=response.model,
                    finish_reasons=[choice.finish_reason for choice in response.choices if choice.finish_reason],
                    input_tokens=response.usage.prompt_tokens if response.usage else None,
                    output_tokens=response.usage.completion_tokens if response.usage else None
                )
                
                if hasattr(response, 'system_fingerprint'):
                    genai_response.system_fingerprint = response.system_fingerprint
                    
                set_genai_response_attributes(span, genai_response)
            
            return generated_query
    
    def _validate_query(self, query: str) -> ValidationResult:
        """Validate the generated DataPrime query using tool execution span."""
        with GenAISpanManager.create_tool_execution_span(
            tool_name="query_validator",
            tool_description="Validates DataPrime query syntax and performance"
        ) as span:
            if span:
                span.set_attribute("query.text", query)
                span.set_attribute("query.length", len(query))
                span.set_attribute("query.operators_count", query.count("|") + 1)
            
            result = self.validator.validate(query)
            
            if span:
                span.set_attribute("validation.is_valid", result.is_valid)
                span.set_attribute("validation.syntax_score", result.syntax_score)
                span.set_attribute("validation.complexity_score", result.complexity_score)
                span.set_attribute("validation.estimated_cost", result.estimated_cost)
                span.set_attribute("validation.issues_count", len(result.issues))
                span.set_attribute("validation.warnings_count", len(result.performance_warnings))
                
            return result
    
    def get_query_suggestions(self, partial_query: str) -> List[str]:
        """Get query completion suggestions."""
        with GenAISpanManager.create_tool_execution_span(
            tool_name="query_suggester",
            tool_description="Provides DataPrime query completion suggestions"
        ) as span:
            if span:
                span.set_attribute("partial_query", partial_query)
                
            suggestions = self.knowledge_base.get_query_suggestions(partial_query)
            
            if span:
                span.set_attribute("suggestions.count", len(suggestions))
                
            return suggestions
    
    def explain_query(self, query: str, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """Explain what a DataPrime query does using GenAI."""
        
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:16]}"
        
        # Build request configuration
        request_config = GenAIRequestConfig(
            model=self.config.model_name,
            temperature=0.3,
            max_tokens=500
        )
        
        with GenAISpanManager.create_inference_span(
            operation_name=GenAIOperationName.CHAT,
            request_config=request_config,
            system=GenAISystem.OPENAI,
            conversation_id=conversation_id,
            output_type=GenAIOutputType.TEXT
        ) as span:
            
            try:
                # First validate the query
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

                # Add prompt event
                if span:
                    add_genai_prompt_event(
                        span,
                        GenAIPromptEvent(
                            prompt=explanation_prompt,
                            role="user"
                        )
                    )

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
                
                # Add completion event
                if span:
                    add_genai_completion_event(
                        span,
                        GenAICompletionEvent(
                            completion=explanation,
                            role="assistant"
                        )
                    )
                    
                    # Set response attributes
                    genai_response = GenAIResponse(
                        id=response.id,
                        model=response.model,
                        finish_reasons=[choice.finish_reason for choice in response.choices if choice.finish_reason],
                        input_tokens=response.usage.prompt_tokens if response.usage else None,
                        output_tokens=response.usage.completion_tokens if response.usage else None
                    )
                    
                    set_genai_response_attributes(span, genai_response)
                
                return {
                    "query": query,
                    "explanation": explanation,
                    "conversation_id": conversation_id,
                    "validation": {
                        "is_valid": validation.is_valid,
                        "syntax_score": validation.syntax_score,
                        "complexity_score": validation.complexity_score
                    },
                    "model": self.config.model_name
                }
                
            except Exception as e:
                if span:
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                return {
                    "query": query,
                    "conversation_id": conversation_id,
                    "error": f"Could not explain query: {str(e)}"
                }
    
    def record_feedback(
        self, 
        query_result: Dict[str, Any], 
        rating: int, 
        comment: str = "",
        conversation_id: Optional[str] = None
    ) -> None:
        """Record user feedback with GenAI context."""
        
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            # Add feedback as span event following GenAI conventions
            current_span.add_event(
                "gen_ai.user.feedback",
                {
                    "feedback.rating": rating,
                    "feedback.comment": comment,
                    "feedback.query": query_result.get("generated_query", ""),
                    "feedback.conversation_id": conversation_id or query_result.get("conversation_id", ""),
                    "feedback.agent_id": self.agent_id,
                    "feedback.agent_name": self.agent_name,
                    "feedback.timestamp": time.time(),
                    "feedback.user_input": query_result.get("user_input", ""),
                    "feedback.validation_score": query_result.get("validation", {}).get("syntax_score", 0)
                }
            )
            
        print(f"📝 Feedback recorded: {rating}/5 - {comment}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get assistant usage statistics."""
        return {
            "service_name": self.config.service_name,
            "agent_name": self.agent_name,
            "agent_id": self.agent_id,
            "agent_description": self.agent_description,
            "model": self.config.model_name,
            "system": GenAISystem.OPENAI,
            "version": "2.0.0",
            "genai_conventions": "OpenTelemetry 1.36.0",
            "status": "healthy"
        } 