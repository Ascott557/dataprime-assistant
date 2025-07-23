# src/__init__.py
"""DataPrime Assistant - AI-powered DataPrime query generator."""

__version__ = "1.0.0"
__author__ = "Coralogix Developer Advocacy"

# data/__init__.py
"""DataPrime knowledge base and examples."""

# tests/__init__.py  
"""Test suite for DataPrime Assistant."""

# src/utils/__init__.py
"""Utility modules for DataPrime Assistant."""

from .utils.config import get_config
from .utils.instrumentation import initialize_instrumentation
from .utils.validation import DataPrimeValidator

__all__ = [
    "get_config",
    "initialize_instrumentation", 
    "DataPrimeValidator"
]