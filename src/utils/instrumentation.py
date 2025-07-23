"""OpenTelemetry instrumentation for DataPrime Assistant."""

import functools
import time
from typing import Any, Callable, Dict, Optional
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from llm_tracekit import setup_export_to_coralogix, OpenAIInstrumentor

from .config import get_config

# Global tracer instance
tracer = None

def initialize_instrumentation() -> None:
    """Initialize OpenTelemetry instrumentation with Coralogix."""
    global tracer
    
    config = get_config()
    
    # Setup Coralogix export using endpoint-based configuration
    setup_export_to_coralogix(
        service_name=config.service_name,
        coralogix_token=config.cx_token,
        coralogix_endpoint=getattr(config, 'cx_endpoint', None),
        application_name=config.application_name,
        subsystem_name=config.subsystem_name,
        capture_content=config.enable_content_capture
    )
    
    # Initialize OpenAI instrumentation
    OpenAIInstrumentor().instrument()
    
    # Get tracer instance
    tracer = trace.get_tracer(__name__)
    
    print(f"✅ Instrumentation initialized for {config.service_name}")

def trace_function(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
) -> Callable:
    """Decorator to trace function execution with custom attributes."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if tracer is None:
                # If tracer not initialized, run function without tracing
                return func(*args, **kwargs)
            
            name = span_name or f"{func.__module__}.{func.__name__}"
            
            with tracer.start_as_current_span(name) as span:
                # Add default attributes
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                
                # Add custom attributes
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    
                    # Record success
                    span.set_attribute("function.duration", time.time() - start_time)
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator

def add_dataprime_attributes(
    span: trace.Span,
    user_input: Optional[str] = None,
    intent_type: Optional[str] = None,
    intent_confidence: Optional[float] = None,
    generated_query: Optional[str] = None,
    validation_score: Optional[float] = None,
    complexity_score: Optional[float] = None,
    examples_count: Optional[int] = None
) -> None:
    """Add DataPrime-specific attributes to a span."""
    
    if user_input:
        span.set_attribute("dataprime.user_input", user_input)
        span.set_attribute("dataprime.input_length", len(user_input))
    
    if intent_type:
        span.set_attribute("dataprime.intent_type", intent_type)
    
    if intent_confidence is not None:
        span.set_attribute("dataprime.intent_confidence", intent_confidence)
    
    if generated_query:
        span.set_attribute("dataprime.generated_query", generated_query)
        span.set_attribute("dataprime.query_length", len(generated_query))
        span.set_attribute("dataprime.query_complexity", generated_query.count("|") + 1)
    
    if validation_score is not None:
        span.set_attribute("dataprime.validation_score", validation_score)
    
    if complexity_score is not None:
        span.set_attribute("dataprime.complexity_score", complexity_score)
    
    if examples_count is not None:
        span.set_attribute("dataprime.examples_used", examples_count)

def trace_intent_classification(func: Callable) -> Callable:
    """Decorator specifically for intent classification."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if tracer is None:
            return func(*args, **kwargs)
        
        with tracer.start_as_current_span("dataprime.intent_classification") as span:
            try:
                # Extract user input from arguments
                user_input = args[1] if len(args) > 1 else kwargs.get("user_input", "")
                span.set_attribute("dataprime.user_input", user_input)
                
                result = func(*args, **kwargs)
                
                # Add result attributes
                if hasattr(result, 'intent_type'):
                    span.set_attribute("dataprime.intent_type", result.intent_type.value)
                    span.set_attribute("dataprime.intent_confidence", result.confidence)
                    span.set_attribute("dataprime.keywords_found", ",".join(result.keywords_found))
                    
                    if result.suggested_timeframe:
                        span.set_attribute("dataprime.suggested_timeframe", result.suggested_timeframe)
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    return wrapper

def trace_query_generation(func: Callable) -> Callable:
    """Decorator specifically for query generation."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if tracer is None:
            return func(*args, **kwargs)
        
        with tracer.start_as_current_span("dataprime.query_generation") as span:
            try:
                # Extract user input from arguments
                user_input = args[1] if len(args) > 1 else kwargs.get("user_input", "")
                span.set_attribute("dataprime.user_input", user_input)
                
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Add result attributes
                span.set_attribute("dataprime.generated_query", result)
                span.set_attribute("dataprime.generation_duration", duration)
                span.set_attribute("dataprime.query_operators", result.count("|") + 1)
                
                # Check for common patterns
                if "filter" in result:
                    span.set_attribute("dataprime.uses_filter", True)
                if "groupby" in result:
                    span.set_attribute("dataprime.uses_groupby", True)
                if "aggregate" in result:
                    span.set_attribute("dataprime.uses_aggregation", True)
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    return wrapper

def trace_query_validation(func: Callable) -> Callable:
    """Decorator specifically for query validation."""
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if tracer is None:
            return func(*args, **kwargs)
        
        with tracer.start_as_current_span("dataprime.query_validation") as span:
            try:
                # Extract query from arguments
                query = args[1] if len(args) > 1 else kwargs.get("query", "")
                span.set_attribute("dataprime.query_to_validate", query)
                
                result = func(*args, **kwargs)
                
                # Add validation result attributes
                if hasattr(result, 'is_valid'):
                    span.set_attribute("dataprime.validation.is_valid", result.is_valid)
                    span.set_attribute("dataprime.validation.syntax_score", result.syntax_score)
                    span.set_attribute("dataprime.validation.complexity_score", result.complexity_score)
                    span.set_attribute("dataprime.validation.estimated_cost", result.estimated_cost)
                    span.set_attribute("dataprime.validation.issues_count", len(result.issues))
                    span.set_attribute("dataprime.validation.warnings_count", len(result.performance_warnings))
                
                span.set_status(Status(StatusCode.OK))
                return result
                
            except Exception as e:
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
    
    return wrapper

def get_current_span_context() -> Dict[str, Any]:
    """Get current span context for logging."""
    span = trace.get_current_span()
    if span and span.is_recording():
        span_context = span.get_span_context()
        return {
            "trace_id": hex(span_context.trace_id),
            "span_id": hex(span_context.span_id),
            "trace_flags": span_context.trace_flags
        }
    return {}

def record_user_feedback(rating: int, comment: Optional[str] = None) -> None:
    """Record user feedback as span events."""
    if tracer is None:
        return
    
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(
            "user_feedback",
            {
                "feedback.rating": rating,
                "feedback.comment": comment or "",
                "feedback.timestamp": time.time()
            }
        )
        span.set_attribute("dataprime.user_rating", rating)