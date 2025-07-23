"""Enhanced OpenTelemetry instrumentation following semantic conventions."""

import functools
import time
import os
from typing import Any, Callable, Dict, Optional, List
from opentelemetry import trace, metrics, baggage
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.semconv.trace import SpanAttributes
from llm_tracekit import setup_export_to_coralogix, OpenAIInstrumentor

from .config import get_config

# Global instances
tracer = None
meter = None

# Semantic Convention Constants
class DataPrimeAttributes:
    """DataPrime-specific attribute constants following semantic conventions."""
    
    # Namespace following the pattern: {product}.{feature}.{attribute}
    NAMESPACE = "dataprime"
    
    # User interaction attributes
    USER_INPUT = f"{NAMESPACE}.user.input"
    USER_INPUT_LENGTH = f"{NAMESPACE}.user.input.length"
    USER_ID = f"{NAMESPACE}.user.id"
    USER_SESSION_ID = f"{NAMESPACE}.user.session.id"
    
    # Intent classification attributes
    INTENT_TYPE = f"{NAMESPACE}.intent.type"
    INTENT_CONFIDENCE = f"{NAMESPACE}.intent.confidence"
    INTENT_KEYWORDS = f"{NAMESPACE}.intent.keywords"
    INTENT_ENTITIES = f"{NAMESPACE}.intent.entities"
    INTENT_TIMEFRAME = f"{NAMESPACE}.intent.timeframe"
    
    # Query generation attributes
    QUERY_GENERATED = f"{NAMESPACE}.query.generated"
    QUERY_LENGTH = f"{NAMESPACE}.query.length"
    QUERY_COMPLEXITY = f"{NAMESPACE}.query.complexity"
    QUERY_OPERATORS_COUNT = f"{NAMESPACE}.query.operators.count"
    QUERY_FUNCTIONS_COUNT = f"{NAMESPACE}.query.functions.count"
    
    # Validation attributes
    VALIDATION_VALID = f"{NAMESPACE}.validation.is_valid"
    VALIDATION_SYNTAX_SCORE = f"{NAMESPACE}.validation.syntax_score"
    VALIDATION_COMPLEXITY_SCORE = f"{NAMESPACE}.validation.complexity_score"
    VALIDATION_COST = f"{NAMESPACE}.validation.estimated_cost"
    VALIDATION_ISSUES_COUNT = f"{NAMESPACE}.validation.issues.count"
    VALIDATION_WARNINGS_COUNT = f"{NAMESPACE}.validation.warnings.count"
    
    # Performance attributes
    CACHE_HIT = f"{NAMESPACE}.cache.hit"
    CACHE_TYPE = f"{NAMESPACE}.cache.type"
    CACHE_SIMILARITY = f"{NAMESPACE}.cache.similarity"
    EXAMPLES_USED_COUNT = f"{NAMESPACE}.examples.used.count"
    RETRY_ATTEMPT = f"{NAMESPACE}.retry.attempt"
    
    # Knowledge base attributes
    KB_OPERATORS_AVAILABLE = f"{NAMESPACE}.kb.operators.available"
    KB_FUNCTIONS_AVAILABLE = f"{NAMESPACE}.kb.functions.available"
    KB_EXAMPLES_COUNT = f"{NAMESPACE}.kb.examples.count"

def initialize_enhanced_instrumentation() -> None:
    """Initialize enhanced OpenTelemetry instrumentation with proper semantic conventions."""
    global tracer, meter
    
    config = get_config()
    
    # Create resource with proper attributes following semantic conventions
    resource = Resource.create({
        ResourceAttributes.SERVICE_NAME: config.service_name,
        ResourceAttributes.SERVICE_VERSION: "2.0.0",
        ResourceAttributes.SERVICE_NAMESPACE: "coralogix.ai.assistant",
        ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv("ENVIRONMENT", "development"),
        ResourceAttributes.HOST_NAME: os.getenv("HOSTNAME", "localhost"),
        "dataprime.assistant.type": "production",
        "dataprime.knowledge_base.version": "enhanced",
    })
    
    # Setup Coralogix export with resource using endpoint-based configuration
    setup_export_to_coralogix(
        service_name=config.service_name,
        coralogix_token=config.cx_token,
        coralogix_endpoint=getattr(config, 'cx_endpoint', None),
        application_name=config.application_name,
        subsystem_name=config.subsystem_name,
        capture_content=config.enable_content_capture
    )
    
    # Initialize OpenAI instrumentation with proper configuration
    OpenAIInstrumentor().instrument(
        capture_content=config.enable_content_capture,
        enrichment_attributes={
            "gen_ai.system": "openai",
            "gen_ai.operation.name": "dataprime_query_generation"
        }
    )
    
    # Get instrumentation instances
    tracer = trace.get_tracer(
        instrumenting_module_name="dataprime.assistant",
        instrumenting_library_version="2.0.0",
        schema_url="https://opentelemetry.io/schemas/1.21.0"
    )
    
    meter = metrics.get_meter(
        name="dataprime.assistant",
        version="2.0.0",
        schema_url="https://opentelemetry.io/schemas/1.21.0"
    )
    
    # Initialize metrics
    _initialize_metrics()
    
    print(f"✅ Enhanced instrumentation initialized for {config.service_name}")
    print(f"   📊 Metrics: Enabled")
    print(f"   🔗 Semantic Conventions: OpenTelemetry 1.21.0")
    print(f"   🏷️  Resource Attributes: {len(resource.attributes)} attributes")

def _initialize_metrics():
    """Initialize application metrics following OpenTelemetry conventions."""
    global meter
    
    if not meter:
        return
    
    # Counters
    global query_generation_counter, intent_classification_counter, validation_counter
    global cache_hit_counter, error_counter
    
    query_generation_counter = meter.create_counter(
        name="dataprime.query.generations",
        description="Number of DataPrime queries generated",
        unit="1"
    )
    
    intent_classification_counter = meter.create_counter(
        name="dataprime.intent.classifications",
        description="Number of intent classifications performed",
        unit="1"
    )
    
    validation_counter = meter.create_counter(
        name="dataprime.query.validations",
        description="Number of query validations performed",
        unit="1"
    )
    
    cache_hit_counter = meter.create_counter(
        name="dataprime.cache.hits",
        description="Number of cache hits",
        unit="1"
    )
    
    error_counter = meter.create_counter(
        name="dataprime.errors",
        description="Number of errors encountered",
        unit="1"
    )
    
    # Histograms
    global query_generation_duration, intent_confidence_histogram, validation_score_histogram
    
    query_generation_duration = meter.create_histogram(
        name="dataprime.query.generation.duration",
        description="Duration of query generation operations",
        unit="s"
    )
    
    intent_confidence_histogram = meter.create_histogram(
        name="dataprime.intent.confidence",
        description="Intent classification confidence scores",
        unit="1"
    )
    
    validation_score_histogram = meter.create_histogram(
        name="dataprime.validation.syntax_score",
        description="Query validation syntax scores",
        unit="1"
    )
    
    # Gauges
    global active_sessions_gauge
    
    active_sessions_gauge = meter.create_up_down_counter(
        name="dataprime.sessions.active",
        description="Number of active user sessions",
        unit="1"
    )

class DataPrimeTracer:
    """Enhanced tracer following OpenTelemetry semantic conventions."""
    
    @staticmethod
    def trace_query_generation(
        user_input: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        span_kind: SpanKind = SpanKind.INTERNAL
    ):
        """Create properly structured span for query generation."""
        if not tracer:
            return None
            
        # Follow semantic convention: operation_name format
        span = tracer.start_span(
            name="dataprime query_generation",
            kind=span_kind,
            attributes={
                # Standard attributes
                SpanAttributes.OPERATION: "query_generation",
                
                # DataPrime-specific attributes
                DataPrimeAttributes.USER_INPUT: user_input,
                DataPrimeAttributes.USER_INPUT_LENGTH: len(user_input),
                DataPrimeAttributes.USER_ID: user_id or "anonymous",
            }
        )
        
        # Add to baggage for cross-service correlation
        if user_id:
            baggage.set_baggage("user.id", user_id)
        if session_id:
            baggage.set_baggage("session.id", session_id)
            span.set_attribute(DataPrimeAttributes.USER_SESSION_ID, session_id)
        
        return span
    
    @staticmethod
    def trace_intent_classification(user_input: str, span_kind: SpanKind = SpanKind.INTERNAL):
        """Create span for intent classification following semantic conventions."""
        if not tracer:
            return None
            
        span = tracer.start_span(
            name="dataprime intent_classification",
            kind=span_kind,
            attributes={
                SpanAttributes.OPERATION: "intent_classification",
                DataPrimeAttributes.USER_INPUT: user_input,
                DataPrimeAttributes.USER_INPUT_LENGTH: len(user_input),
            }
        )
        
        return span
    
    @staticmethod  
    def trace_query_validation(query: str, span_kind: SpanKind = SpanKind.INTERNAL):
        """Create span for query validation."""
        if not tracer:
            return None
            
        span = tracer.start_span(
            name="dataprime query_validation",
            kind=span_kind,
            attributes={
                SpanAttributes.OPERATION: "query_validation",
                DataPrimeAttributes.QUERY_GENERATED: query,
                DataPrimeAttributes.QUERY_LENGTH: len(query),
                DataPrimeAttributes.QUERY_COMPLEXITY: query.count("|") + 1,
            }
        )
        
        return span

def enhanced_trace_function(
    operation_name: str,
    span_kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
    record_metrics: bool = True
) -> Callable:
    """Enhanced decorator with proper semantic conventions and metrics."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not tracer:
                return func(*args, **kwargs)
            
            # Create span with semantic naming
            span_name = f"dataprime {operation_name}"
            
            with tracer.start_as_current_span(
                span_name,
                kind=span_kind,
                attributes=attributes or {}
            ) as span:
                # Add standard attributes
                span.set_attribute("code.function", func.__name__)
                span.set_attribute("code.namespace", func.__module__)
                
                try:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Set success status
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("operation.duration", duration)
                    
                    # Record metrics if enabled
                    if record_metrics and operation_name == "query_generation":
                        query_generation_counter.add(1, {
                            "operation": operation_name,
                            "status": "success"
                        })
                        query_generation_duration.record(duration, {
                            "operation": operation_name
                        })
                    
                    return result
                    
                except Exception as e:
                    # Record error with proper attributes
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    
                    # Record error metrics
                    if record_metrics:
                        error_counter.add(1, {
                            "operation": operation_name,
                            "error_type": type(e).__name__
                        })
                    
                    # Record exception event
                    span.record_exception(e)
                    
                    raise
        
        return wrapper
    return decorator

def set_dataprime_attributes(
    span: trace.Span,
    user_input: Optional[str] = None,
    intent_result: Optional[Any] = None,
    generated_query: Optional[str] = None,
    validation_result: Optional[Any] = None,
    cache_info: Optional[Dict[str, Any]] = None,
    examples_count: Optional[int] = None
) -> None:
    """Set DataPrime-specific attributes following semantic conventions."""
    
    # User input attributes
    if user_input:
        span.set_attribute(DataPrimeAttributes.USER_INPUT, user_input)
        span.set_attribute(DataPrimeAttributes.USER_INPUT_LENGTH, len(user_input))
    
    # Intent classification attributes
    if intent_result:
        span.set_attribute(DataPrimeAttributes.INTENT_TYPE, intent_result.intent_type.value)
        span.set_attribute(DataPrimeAttributes.INTENT_CONFIDENCE, intent_result.confidence)
        
        if intent_result.keywords_found:
            span.set_attribute(DataPrimeAttributes.INTENT_KEYWORDS, ",".join(intent_result.keywords_found))
        
        if intent_result.suggested_timeframe:
            span.set_attribute(DataPrimeAttributes.INTENT_TIMEFRAME, intent_result.suggested_timeframe)
        
        if intent_result.entities:
            span.set_attribute(DataPrimeAttributes.INTENT_ENTITIES, str(intent_result.entities))
        
        # Record intent confidence metric
        if hasattr(intent_confidence_histogram, 'record'):
            intent_confidence_histogram.record(intent_result.confidence, {
                "intent_type": intent_result.intent_type.value
            })
    
    # Query generation attributes
    if generated_query:
        span.set_attribute(DataPrimeAttributes.QUERY_GENERATED, generated_query)
        span.set_attribute(DataPrimeAttributes.QUERY_LENGTH, len(generated_query))
        span.set_attribute(DataPrimeAttributes.QUERY_OPERATORS_COUNT, generated_query.count("|") + 1)
        
        # Analyze query patterns
        functions_count = len([f for f in ['count', 'sum', 'avg', 'max', 'min'] if f in generated_query.lower()])
        span.set_attribute(DataPrimeAttributes.QUERY_FUNCTIONS_COUNT, functions_count)
    
    # Validation attributes
    if validation_result:
        span.set_attribute(DataPrimeAttributes.VALIDATION_VALID, validation_result.is_valid)
        span.set_attribute(DataPrimeAttributes.VALIDATION_SYNTAX_SCORE, validation_result.syntax_score)
        span.set_attribute(DataPrimeAttributes.VALIDATION_COMPLEXITY_SCORE, validation_result.complexity_score)
        span.set_attribute(DataPrimeAttributes.VALIDATION_COST, validation_result.estimated_cost)
        span.set_attribute(DataPrimeAttributes.VALIDATION_ISSUES_COUNT, len(validation_result.issues))
        
        # Record validation metrics
        if hasattr(validation_counter, 'add'):
            validation_counter.add(1, {
                "is_valid": str(validation_result.is_valid),
                "cost": validation_result.estimated_cost
            })
            
        if hasattr(validation_score_histogram, 'record'):
            validation_score_histogram.record(validation_result.syntax_score, {
                "is_valid": str(validation_result.is_valid)
            })
    
    # Cache attributes
    if cache_info:
        span.set_attribute(DataPrimeAttributes.CACHE_HIT, cache_info.get('hit', False))
        if cache_info.get('type'):
            span.set_attribute(DataPrimeAttributes.CACHE_TYPE, cache_info['type'])
        if cache_info.get('similarity'):
            span.set_attribute(DataPrimeAttributes.CACHE_SIMILARITY, cache_info['similarity'])
        
        # Record cache metrics
        if cache_info.get('hit') and hasattr(cache_hit_counter, 'add'):
            cache_hit_counter.add(1, {
                "cache_type": cache_info.get('type', 'unknown')
            })
    
    # Examples attributes
    if examples_count is not None:
        span.set_attribute(DataPrimeAttributes.EXAMPLES_USED_COUNT, examples_count)

def add_span_event(
    event_name: str,
    attributes: Optional[Dict[str, Any]] = None,
    timestamp: Optional[float] = None
) -> None:
    """Add span event with proper attributes."""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(
            event_name,
            attributes=attributes or {},
            timestamp=int((timestamp or time.time()) * 1_000_000_000)  # Convert to nanoseconds
        )

def record_user_feedback(
    rating: int, 
    comment: Optional[str] = None,
    query_id: Optional[str] = None
) -> None:
    """Record user feedback with proper event structure."""
    add_span_event(
        "dataprime.user.feedback",
        {
            "feedback.rating": rating,
            "feedback.comment": comment or "",
            "feedback.query_id": query_id or "",
            "feedback.timestamp": time.time()
        }
    )

def get_enhanced_span_context() -> Dict[str, Any]:
    """Get enhanced span context with baggage information."""
    span = trace.get_current_span()
    context = {}
    
    if span and span.is_recording():
        span_context = span.get_span_context()
        context.update({
            "trace_id": f"{span_context.trace_id:032x}",
            "span_id": f"{span_context.span_id:016x}",
            "trace_flags": span_context.trace_flags,
            "is_remote": span_context.is_remote,
        })
    
    # Add baggage
    baggage_items = baggage.get_all()
    if baggage_items:
        context["baggage"] = dict(baggage_items)
    
    return context

# Migration helpers for backward compatibility
def add_dataprime_attributes(span, **kwargs):
    """Backward compatibility wrapper."""
    set_dataprime_attributes(span, **kwargs)

def trace_intent_classification(func):
    """Backward compatibility wrapper."""
    return enhanced_trace_function("intent_classification")(func)

def trace_query_generation(func):
    """Backward compatibility wrapper."""
    return enhanced_trace_function("query_generation")(func)

def trace_query_validation(func):
    """Backward compatibility wrapper."""
    return enhanced_trace_function("query_validation")(func) 