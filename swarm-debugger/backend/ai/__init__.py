"""
OpenAI Integration package for SWARM DEBUGGER.
Reusable client for OpenAI Responses API / Structured Outputs.
"""
from backend.ai.client import OpenAIClient, get_openai_client, OpenAIClientError, OpenAIConfigurationError

__all__ = ["OpenAIClient", "get_openai_client", "OpenAIClientError", "OpenAIConfigurationError"]
