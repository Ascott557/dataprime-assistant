"""OpenTelemetry GenAI Semantic Conventions Implementation.

This module implements the official OpenTelemetry semantic conventions for Generative AI systems,
including spans, events, metrics, and agent operations as defined in:
- https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-spans/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-events/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-metrics/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/gen-ai-agent-spans/
"""

import functools
import time
import json
from typing import Any, Callable, Dict, Optional, List, Union
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum

from opentelemetry import trace, metrics, baggage
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.util.types import AttributeValue
from llm_tracekit import setup_export_to_coralogix, OpenAIInstrumentor

from .config import get_config

# Global instrumentation state
_initialized = False
tracer = None
meter = None

# GenAI Operation Names (following semantic conventions)
class GenAIOperationName:
    CHAT = "chat"
    TEXT_COMPLETION = "text_completion"
    EMBEDDINGS = "embeddings"
    CREATE_AGENT = "create_agent"
    INVOKE_AGENT = "invoke_agent"
    EXECUTE_TOOL = "execute_tool"
    GENERATE_CONTENT = "generate_content"

# GenAI Systems (following semantic conventions)
class GenAISystem:
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure.ai.openai"
    AWS_BEDROCK = "aws.bedrock"
    CUSTOM = "_OTHER"

# GenAI Token Types
class GenAITokenType:
    INPUT = "input"
    OUTPUT = "output"

# GenAI Output Types
class GenAIOutputType:
    TEXT = "text"
    JSON = "json"
    IMAGE = "image"
    SPEECH = "speech"

# GenAI Attribute Names (following semantic conventions)
class GenAIAttributes:
    # Core operation attributes
    OPERATION_NAME = "gen_ai.operation.name"
    SYSTEM = "gen_ai.system"
    
    # Request attributes
    REQUEST_MODEL = "gen_ai.request.model"
    REQUEST_TEMPERATURE = "gen_ai.request.temperature"
    REQUEST_TOP_P = "gen_ai.request.top_p"
    REQUEST_TOP_K = "gen_ai.request.top_k"
    REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
    REQUEST_SEED = "gen_ai.request.seed"
    REQUEST_FREQUENCY_PENALTY = "gen_ai.request.frequency_penalty"
    REQUEST_PRESENCE_PENALTY = "gen_ai.request.presence_penalty"
    REQUEST_STOP_SEQUENCES = "gen_ai.request.stop_sequences"
    REQUEST_CHOICE_COUNT = "gen_ai.request.choice.count"
    REQUEST_ENCODING_FORMATS = "gen_ai.request.encoding_formats"
    
    # Response attributes
    RESPONSE_ID = "gen_ai.response.id"
    RESPONSE_MODEL = "gen_ai.response.model"
    RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
    
    # Usage attributes
    USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
    USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
    
    # Agent attributes
    AGENT_ID = "gen_ai.agent.id"
    AGENT_NAME = "gen_ai.agent.name"
    AGENT_DESCRIPTION = "gen_ai.agent.description"
    
    # Conversation attributes
    CONVERSATION_ID = "gen_ai.conversation.id"
    
    # Output type
    OUTPUT_TYPE = "gen_ai.output.type"
    
    # Tool attributes
    TOOL_NAME = "gen_ai.tool.name"
    TOOL_CALL_ID = "gen_ai.tool.call.id"
    TOOL_DESCRIPTION = "gen_ai.tool.description"
    
    # Token type for metrics
    TOKEN_TYPE = "gen_ai.token.type"
    
    # Data source attributes
    DATA_SOURCE_ID = "gen_ai.data_source.id"
    
    # OpenAI specific attributes
    OPENAI_REQUEST_SERVICE_TIER = "gen_ai.openai.request.service_tier"
    OPENAI_RESPONSE_SERVICE_TIER = "gen_ai.openai.response.service_tier"
    OPENAI_RESPONSE_SYSTEM_FINGERPRINT = "gen_ai.openai.response.system_fingerprint"

# GenAI Event Names (following semantic conventions)
class GenAIEventName:
    PROMPT = "gen_ai.content.prompt"
    COMPLETION = "gen_ai.content.completion"

@dataclass
class GenAIRequestConfig:
    """Configuration for GenAI requests following semantic conventions."""
    model: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[float] = None
    max_tokens: Optional[int] = None
    seed: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    choice_count: Optional[int] = None
    encoding_formats: Optional[List[str]] = None
    service_tier: Optional[str] = None

@dataclass
class GenAIResponse:
    """GenAI response data following semantic conventions."""
    id: Optional[str] = None
    model: Optional[str] = None
    finish_reasons: Optional[List[str]] = None
    system_fingerprint: Optional[str] = None
    service_tier: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None

@dataclass
class GenAIPromptEvent:
    """GenAI prompt event data."""
    prompt: str
    role: str = "user"

@dataclass
class GenAICompletionEvent:
    """GenAI completion event data."""
    completion: str
    role: str = "assistant"

def initialize_genai_instrumentation() -> None:
    """Initialize OpenTelemetry GenAI instrumentation following semantic conventions."""
    global tracer, meter, _initialized
    
    if _initialized:
        print(f"⚠️  GenAI instrumentation already initialized - skipping")
        return
    
    config = get_config()
    
    try:
        # Setup Coralogix export using endpoint-based configuration
        setup_export_to_coralogix(
            service_name=config.service_name,
            coralogix_token=config.cx_token,
            coralogix_endpoint=getattr(config, 'cx_endpoint', None),
            application_name=config.application_name,
            subsystem_name=config.subsystem_name,
            capture_content=config.enable_content_capture
        )
    except Exception as e:
        if "not allowed" in str(e) or "already" in str(e):
            print(f"⚠️  Tracer provider already initialized - continuing with existing setup")
        else:
            raise
    
    # Initialize OpenAI instrumentation with GenAI conventions
    try:
        OpenAIInstrumentor().instrument(
            capture_content=config.enable_content_capture,
            enrichment_attributes={
                GenAIAttributes.SYSTEM: GenAISystem.OPENAI,
            }
        )
    except Exception as e:
        if "already" in str(e).lower() or "instrument" in str(e).lower():
            print(f"⚠️  OpenAI instrumentation already active - continuing with existing setup")
        else:
            raise
    
    # Get instrumentation instances
    tracer = trace.get_tracer(
        instrumenting_module_name="dataprime.genai.assistant",
        instrumenting_library_version="2.0.0",
        schema_url="https://opentelemetry.io/schemas/1.21.0"
    )
    
    meter = metrics.get_meter(
        name="dataprime.genai.assistant",
        version="2.0.0",
        schema_url="https://opentelemetry.io/schemas/1.21.0"
    )
    
    # Initialize GenAI metrics following semantic conventions
    _initialize_genai_metrics()
    
    # Mark as initialized
    _initialized = True
    
    print(f"✅ GenAI instrumentation initialized for {config.service_name}")
    print(f"   📊 GenAI Metrics: Enabled") 
    print(f"   🔗 GenAI Semantic Conventions: OpenTelemetry 1.36.0")

def _initialize_genai_metrics():
    """Initialize GenAI metrics following OpenTelemetry conventions."""
    global meter, token_usage_histogram, operation_duration_histogram
    
    if not meter:
        return
    
    # GenAI client token usage histogram 
    # Following buckets from spec: [1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864]
    token_usage_histogram = meter.create_histogram(
        name="gen_ai.client.token.usage",
        description="Distribution of token usage per GenAI operation",
        unit="token",
        explicit_bucket_boundaries_advisory=[1, 4, 16, 64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304, 16777216, 67108864]
    )
    
    # GenAI client operation duration histogram
    # Following buckets from spec: [0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92]
    operation_duration_histogram = meter.create_histogram(
        name="gen_ai.client.operation.duration",
        description="GenAI operation duration",
        unit="s",
        explicit_bucket_boundaries_advisory=[0.01, 0.02, 0.04, 0.08, 0.16, 0.32, 0.64, 1.28, 2.56, 5.12, 10.24, 20.48, 40.96, 81.92]
    )

class GenAISpanManager:
    """Manager for creating GenAI spans following semantic conventions."""
    
    @staticmethod
    @contextmanager
    def create_inference_span(
        operation_name: str,
        request_config: GenAIRequestConfig,
        system: str = GenAISystem.OPENAI,
        conversation_id: Optional[str] = None,
        output_type: Optional[str] = None,
        span_kind: SpanKind = SpanKind.CLIENT
    ):
        """Create a GenAI inference span following semantic conventions."""
        if not tracer:
            yield None
            return
            
        # Span name: {operation_name} {model}
        span_name = f"{operation_name} {request_config.model}"
        
        # Build attributes according to semantic conventions
        attributes = {
            GenAIAttributes.OPERATION_NAME: operation_name,
            GenAIAttributes.SYSTEM: system,
            GenAIAttributes.REQUEST_MODEL: request_config.model,
        }
        
        # Add optional request attributes
        if request_config.temperature is not None:
            attributes[GenAIAttributes.REQUEST_TEMPERATURE] = request_config.temperature
        if request_config.top_p is not None:
            attributes[GenAIAttributes.REQUEST_TOP_P] = request_config.top_p
        if request_config.top_k is not None:
            attributes[GenAIAttributes.REQUEST_TOP_K] = request_config.top_k
        if request_config.max_tokens is not None:
            attributes[GenAIAttributes.REQUEST_MAX_TOKENS] = request_config.max_tokens
        if request_config.seed is not None:
            attributes[GenAIAttributes.REQUEST_SEED] = request_config.seed
        if request_config.frequency_penalty is not None:
            attributes[GenAIAttributes.REQUEST_FREQUENCY_PENALTY] = request_config.frequency_penalty
        if request_config.presence_penalty is not None:
            attributes[GenAIAttributes.REQUEST_PRESENCE_PENALTY] = request_config.presence_penalty
        if request_config.stop_sequences:
            attributes[GenAIAttributes.REQUEST_STOP_SEQUENCES] = request_config.stop_sequences
        if request_config.choice_count and request_config.choice_count != 1:
            attributes[GenAIAttributes.REQUEST_CHOICE_COUNT] = request_config.choice_count
        if request_config.encoding_formats:
            attributes[GenAIAttributes.REQUEST_ENCODING_FORMATS] = request_config.encoding_formats
        if request_config.service_tier and request_config.service_tier != 'auto':
            attributes[GenAIAttributes.OPENAI_REQUEST_SERVICE_TIER] = request_config.service_tier
            
        # Add optional attributes
        if conversation_id:
            attributes[GenAIAttributes.CONVERSATION_ID] = conversation_id
        if output_type:
            attributes[GenAIAttributes.OUTPUT_TYPE] = output_type
            
        with tracer.start_as_current_span(
            span_name,
            kind=span_kind,
            attributes=attributes
        ) as span:
            yield span
    
    @staticmethod
    @contextmanager  
    def create_agent_span(
        operation_name: str,
        agent_name: Optional[str] = None,
        agent_id: Optional[str] = None,
        agent_description: Optional[str] = None,
        model: Optional[str] = None,
        conversation_id: Optional[str] = None,
        system: str = GenAISystem.CUSTOM,
        span_kind: SpanKind = SpanKind.CLIENT
    ):
        """Create a GenAI agent span following semantic conventions."""
        if not tracer:
            yield None
            return
            
        # Span name: {operation_name} {agent_name} or just {operation_name}
        span_name = f"{operation_name} {agent_name}" if agent_name else operation_name
        
        attributes = {
            GenAIAttributes.OPERATION_NAME: operation_name,
            GenAIAttributes.SYSTEM: system,
        }
        
        # Add agent attributes
        if agent_id:
            attributes[GenAIAttributes.AGENT_ID] = agent_id
        if agent_name:
            attributes[GenAIAttributes.AGENT_NAME] = agent_name
        if agent_description:
            attributes[GenAIAttributes.AGENT_DESCRIPTION] = agent_description
        if model:
            attributes[GenAIAttributes.REQUEST_MODEL] = model
        if conversation_id:
            attributes[GenAIAttributes.CONVERSATION_ID] = conversation_id
            
        with tracer.start_as_current_span(
            span_name,
            kind=span_kind,
            attributes=attributes
        ) as span:
            yield span
    
    @staticmethod
    @contextmanager
    def create_tool_execution_span(
        tool_name: str,
        tool_call_id: Optional[str] = None,
        tool_description: Optional[str] = None,
        span_kind: SpanKind = SpanKind.INTERNAL
    ):
        """Create a tool execution span following semantic conventions."""
        if not tracer:
            yield None
            return
            
        span_name = f"execute_tool {tool_name}"
        
        attributes = {
            GenAIAttributes.OPERATION_NAME: GenAIOperationName.EXECUTE_TOOL,
            GenAIAttributes.TOOL_NAME: tool_name,
        }
        
        if tool_call_id:
            attributes[GenAIAttributes.TOOL_CALL_ID] = tool_call_id
        if tool_description:
            attributes[GenAIAttributes.TOOL_DESCRIPTION] = tool_description
            
        with tracer.start_as_current_span(
            span_name,
            kind=span_kind,
            attributes=attributes
        ) as span:
            yield span

def set_genai_response_attributes(span: trace.Span, response: GenAIResponse) -> None:
    """Set GenAI response attributes on span following semantic conventions."""
    if not span or not span.is_recording():
        return
        
    if response.id:
        span.set_attribute(GenAIAttributes.RESPONSE_ID, response.id)
    if response.model:
        span.set_attribute(GenAIAttributes.RESPONSE_MODEL, response.model)
    if response.finish_reasons:
        span.set_attribute(GenAIAttributes.RESPONSE_FINISH_REASONS, response.finish_reasons)
    if response.system_fingerprint:
        span.set_attribute(GenAIAttributes.OPENAI_RESPONSE_SYSTEM_FINGERPRINT, response.system_fingerprint)
    if response.service_tier:
        span.set_attribute(GenAIAttributes.OPENAI_RESPONSE_SERVICE_TIER, response.service_tier)
    if response.input_tokens:
        span.set_attribute(GenAIAttributes.USAGE_INPUT_TOKENS, response.input_tokens)
    if response.output_tokens:
        span.set_attribute(GenAIAttributes.USAGE_OUTPUT_TOKENS, response.output_tokens)

def add_genai_prompt_event(span: trace.Span, prompt_event: GenAIPromptEvent) -> None:
    """Add GenAI prompt event to span following semantic conventions."""
    if not span or not span.is_recording():
        return
        
    span.add_event(
        GenAIEventName.PROMPT,
        {
            "gen_ai.prompt": prompt_event.prompt,
            "gen_ai.prompt.role": prompt_event.role,
            "gen_ai.prompt.length": len(prompt_event.prompt)
        }
    )

def add_genai_completion_event(span: trace.Span, completion_event: GenAICompletionEvent) -> None:
    """Add GenAI completion event to span following semantic conventions."""
    if not span or not span.is_recording():
        return
        
    span.add_event(
        GenAIEventName.COMPLETION,
        {
            "gen_ai.completion": completion_event.completion,
            "gen_ai.completion.role": completion_event.role,
            "gen_ai.completion.length": len(completion_event.completion)
        }
    )

def record_genai_token_usage(
    operation_name: str,
    system: str,
    model: str,
    token_type: str,
    count: int,
    server_address: Optional[str] = None,
    server_port: Optional[int] = None,
    response_model: Optional[str] = None
) -> None:
    """Record GenAI token usage metric following semantic conventions."""
    if not token_usage_histogram:
        return
        
    attributes = {
        GenAIAttributes.OPERATION_NAME: operation_name,
        GenAIAttributes.SYSTEM: system,
        GenAIAttributes.REQUEST_MODEL: model,
        GenAIAttributes.TOKEN_TYPE: token_type,
    }
    
    if response_model:
        attributes[GenAIAttributes.RESPONSE_MODEL] = response_model
    if server_address:
        attributes[SpanAttributes.SERVER_ADDRESS] = server_address
    if server_port:
        attributes[SpanAttributes.SERVER_PORT] = server_port
        
    token_usage_histogram.record(count, attributes)

def record_genai_operation_duration(
    operation_name: str,
    system: str,
    model: str,
    duration: float,
    error_type: Optional[str] = None,
    server_address: Optional[str] = None,
    server_port: Optional[int] = None,
    response_model: Optional[str] = None
) -> None:
    """Record GenAI operation duration metric following semantic conventions."""
    if not operation_duration_histogram:
        return
        
    attributes = {
        GenAIAttributes.OPERATION_NAME: operation_name,
        GenAIAttributes.SYSTEM: system,
        GenAIAttributes.REQUEST_MODEL: model,
    }
    
    if error_type:
        attributes[SpanAttributes.ERROR_TYPE] = error_type
    if response_model:
        attributes[GenAIAttributes.RESPONSE_MODEL] = response_model
    if server_address:
        attributes[SpanAttributes.SERVER_ADDRESS] = server_address
    if server_port:
        attributes[SpanAttributes.SERVER_PORT] = server_port
        
    operation_duration_histogram.record(duration, attributes)

def genai_inference_decorator(
    operation_name: str,
    system: str = GenAISystem.OPENAI,
    model_extractor: Optional[Callable[[Any], str]] = None,
    request_config_extractor: Optional[Callable[[Any], GenAIRequestConfig]] = None,
    response_extractor: Optional[Callable[[Any], GenAIResponse]] = None,
    conversation_id_extractor: Optional[Callable[[Any], str]] = None,
    output_type: Optional[str] = None
):
    """Decorator for GenAI inference operations following semantic conventions."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not tracer:
                return func(*args, **kwargs)
                
            # Extract configuration
            model = model_extractor(*args) if model_extractor else "unknown"
            request_config = request_config_extractor(*args) if request_config_extractor else GenAIRequestConfig(model=model)
            conversation_id = conversation_id_extractor(*args) if conversation_id_extractor else None
            
            with GenAISpanManager.create_inference_span(
                operation_name=operation_name,
                request_config=request_config,
                system=system,
                conversation_id=conversation_id,
                output_type=output_type
            ) as span:
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Extract and set response attributes
                    if response_extractor:
                        response = response_extractor(result)
                        set_genai_response_attributes(span, response)
                        
                        # Record metrics
                        if response.input_tokens:
                            record_genai_token_usage(
                                operation_name, system, request_config.model, 
                                GenAITokenType.INPUT, response.input_tokens,
                                response_model=response.model
                            )
                        if response.output_tokens:
                            record_genai_token_usage(
                                operation_name, system, request_config.model,
                                GenAITokenType.OUTPUT, response.output_tokens, 
                                response_model=response.model
                            )
                    
                    # Record operation duration
                    record_genai_operation_duration(
                        operation_name, system, request_config.model, duration,
                        response_model=response.model if response_extractor else None
                    )
                    
                    # Set success status
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    error_type = type(e).__name__
                    
                    # Set error status and attributes
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute(SpanAttributes.ERROR_TYPE, error_type)
                    span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
                    
                    # Record error metrics
                    record_genai_operation_duration(
                        operation_name, system, request_config.model, duration, 
                        error_type=error_type
                    )
                    
                    # Record exception event
                    span.record_exception(e)
                    raise
                    
        return wrapper
    return decorator

def genai_agent_decorator(
    operation_name: str,
    agent_name: Optional[str] = None,
    agent_description: Optional[str] = None,
    system: str = GenAISystem.CUSTOM
):
    """Decorator for GenAI agent operations following semantic conventions."""
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            if not tracer:
                return func(*args, **kwargs)
                
            with GenAISpanManager.create_agent_span(
                operation_name=operation_name,
                agent_name=agent_name,
                agent_description=agent_description,
                system=system
            ) as span:
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    # Set success status and duration
                    span.set_status(Status(StatusCode.OK))
                    span.set_attribute("operation.duration", duration)
                    
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    error_type = type(e).__name__
                    
                    # Set error status and attributes
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute(SpanAttributes.ERROR_TYPE, error_type)
                    span.set_attribute(SpanAttributes.ERROR_MESSAGE, str(e))
                    span.set_attribute("operation.duration", duration)
                    
                    # Record exception event
                    span.record_exception(e)
                    raise
                    
        return wrapper
    return decorator

# Backward compatibility aliases
initialize_enhanced_instrumentation = initialize_genai_instrumentation
DataPrimeTracer = GenAISpanManager 