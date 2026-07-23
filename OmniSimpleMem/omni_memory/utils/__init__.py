"""
Utility functions for Omni-Memory.
"""

from omni_memory.utils.embedding import EmbeddingService
from omni_memory.utils.logging_config import setup_logging
from omni_memory.utils.usage import (
    get_usage_tracker,
    reset_usage_tracker,
    wrap_openai_client,
)

__all__ = [
    "EmbeddingService",
    "setup_logging",
    "get_usage_tracker",
    "reset_usage_tracker",
    "wrap_openai_client",
]
