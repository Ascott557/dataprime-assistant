"""Configuration management for DataPrime Assistant."""

import os
from typing import Optional
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config(BaseSettings):
    """Application configuration with validation."""
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    model_name: str = Field("gpt-4o-mini", env="MODEL_NAME")
    max_tokens: int = Field(1000, env="MAX_TOKENS")
    temperature: float = Field(0.1, env="TEMPERATURE")
    
    # Coralogix Configuration
    cx_token: str = Field(..., env="CX_TOKEN")
    cx_domain: str = Field("coralogix.com", env="CX_DOMAIN")
    service_name: str = Field("dataprime-assistant", env="SERVICE_NAME")
    application_name: str = Field("ai-demo-app", env="APPLICATION_NAME")
    subsystem_name: str = Field("query-generator", env="SUBSYSTEM_NAME")
    enable_content_capture: bool = Field(True, env="ENABLE_CONTENT_CAPTURE")
    
    # Application Configuration
    log_level: str = Field("INFO", env="LOG_LEVEL")
    debug_mode: bool = Field(False, env="DEBUG_MODE")
    enable_cache: bool = Field(True, env="ENABLE_CACHE")
    
    # Enhanced Telemetry Configuration
    enhanced_telemetry: bool = Field(True, env="ENHANCED_TELEMETRY")
    enable_metrics: bool = Field(True, env="ENABLE_METRICS")
    telemetry_sampling_rate: float = Field(1.0, env="TELEMETRY_SAMPLING_RATE")
    
    # Additional Configuration (optional)
    cx_endpoint: Optional[str] = Field(None, env="CX_ENDPOINT")
    enable_conversation_context: bool = Field(True, env="ENABLE_CONVERSATION_CONTEXT")
    enable_performance_monitoring: bool = Field(True, env="ENABLE_PERFORMANCE_MONITORING")
    
    @validator("temperature")
    def validate_temperature(cls, v):
        if not 0 <= v <= 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v
    
    @validator("max_tokens")
    def validate_max_tokens(cls, v):
        if v <= 0:
            raise ValueError("Max tokens must be positive")
        return v
    
    @validator("cx_domain")
    def validate_cx_domain(cls, v):
        valid_domains = [
            "coralogix.com", 
            "eu2.coralogix.com", 
            "app.coralogix.in",
            "coralogixsg.com", 
            "coralogix.co.uk"
        ]
        if v not in valid_domains:
            raise ValueError(f"Coralogix domain must be one of: {', '.join(valid_domains)}")
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global configuration instance
config = Config()

def get_config() -> Config:
    """Get the global configuration instance."""
    return config