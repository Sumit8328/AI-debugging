import os
import re
import logging
import asyncio
from typing import Type, TypeVar, Optional, Dict, Any, List
from pydantic import BaseModel, ValidationError

import openai
from openai import AsyncOpenAI
from openai import (
    AuthenticationError,
    RateLimitError,
    APITimeoutError,
    APIConnectionError,
    APIStatusError,
    APIError
)

from backend.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def mask_secret(text: str) -> str:
    """
    Redacts any potential API keys or sensitive credential patterns from log or error messages.
    Ensures OPENAI_API_KEY is never exposed in logs, exceptions, or WebSocket payloads.
    """
    if not text:
        return text
    # Mask OpenAI key formats (e.g. sk-proj-..., sk-..., etc.)
    return re.sub(r"sk-[a-zA-Z0-9_\-]{15,}", "sk-***REDACTED***", str(text))


class OpenAIClientError(Exception):
    """Base exception for all OpenAI client operations."""
    def __init__(self, message: str, source: str = "openai_client"):
        self.message = mask_secret(message)
        self.source = source
        super().__init__(self.message)


class OpenAIConfigurationError(OpenAIClientError):
    """Raised when OPENAI_API_KEY is missing or unconfigured."""
    pass


class OpenAIAuthenticationError(OpenAIClientError):
    """Raised when the OpenAI API key is rejected or invalid."""
    pass


class OpenAIRateLimitError(OpenAIClientError):
    """Raised when OpenAI API rate limits or quota are exceeded."""
    pass


class OpenAITimeoutError(OpenAIClientError):
    """Raised when the OpenAI API call times out."""
    pass


class OpenAIConnectionError(OpenAIClientError):
    """Raised when network connectivity to OpenAI fails."""
    pass


class OpenAIResponseValidationError(OpenAIClientError):
    """Raised when the model response fails Pydantic schema validation after retries."""
    pass


class OpenAIClient:
    """
    Reusable singleton client for OpenAI Responses API / Structured Outputs.
    
    Architecture:
    FastAPI -> Orchestrator -> Agent -> OpenAI Client -> Responses API

    - Reads OPENAI_API_KEY and MODEL_NAME from environment / config.py
    - Exposes clean methods for structured output generation
    - Never exposes secret values in logs or exceptions
    - Retries once on validation failure with schema correction
    - Gracefully handles API errors (missing key, auth, rate limit, timeout, connection)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ):
        # Read from environment or config.py
        env_key = os.getenv("OPENAI_API_KEY")
        self.api_key = (api_key or env_key or settings.OPENAI_API_KEY or "").strip() or None
        
        env_model = os.getenv("MODEL_NAME")
        self.model_name = model_name or env_model or settings.MODEL_NAME or "gpt-5.6-luna"
        self.timeout = timeout_seconds or settings.AI_TIMEOUT_SECONDS or 45

        self._client: Optional[AsyncOpenAI] = None
        if self.api_key:
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                timeout=float(self.timeout)
            )
            # Log initialization safely without exposing key
            logger.info(f"OpenAIClient initialized with model={self.model_name} (API key configured)")
        else:
            logger.info(f"OpenAIClient initialized with model={self.model_name} (OPENAI_API_KEY is not set)")

    def is_configured(self) -> bool:
        """Returns True if a non-empty API key is present."""
        return bool(self.api_key and len(self.api_key) > 0)

    @property
    def client(self) -> AsyncOpenAI:
        """Returns the active AsyncOpenAI client or raises OpenAIConfigurationError."""
        if not self.is_configured() or self._client is None:
            raise OpenAIConfigurationError("OpenAI API configuration is missing. Set OPENAI_API_KEY in environment or .env file.")
        return self._client

    async def create_response(
        self,
        instructions: str,
        input_text: str,
        response_format: Type[T],
        max_retries: int = 1
    ) -> T:
        """
        Creates a structured output call using the OpenAI Responses API.
        Validates the output against the specified Pydantic schema `response_format`.

        If validation fails:
        1. Logs the validation error safely (redacting any secrets).
        2. Retries once with a schema-correcting instruction.
        3. If still invalid, raises OpenAIResponseValidationError.

        Handles network, auth, rate-limit, and timeout errors cleanly.
        """
        if not self.is_configured():
            raise OpenAIConfigurationError("OpenAI API configuration is missing.")

        current_instructions = instructions
        current_input = input_text
        attempts = 0
        last_validation_error: Optional[Exception] = None

        while attempts <= max_retries:
            attempts += 1
            try:
                # 1. Attempt primary Responses API method
                parsed_result = await self._execute_responses_call(
                    instructions=current_instructions,
                    input_text=current_input,
                    response_format=response_format
                )

                if parsed_result is not None:
                    # Validate directly with Pydantic
                    if isinstance(parsed_result, response_format):
                        return parsed_result
                    elif isinstance(parsed_result, dict):
                        return response_format.model_validate(parsed_result)
                    elif hasattr(parsed_result, "model_dump"):
                        return response_format.model_validate(parsed_result.model_dump())
                    else:
                        return response_format.model_validate(parsed_result)

                raise ValidationError.from_exception_data(
                    title=response_format.__name__,
                    line_errors=[{"type": "value_error", "loc": ("root",), "msg": "Model returned empty parsed response", "input": {}}]
                )

            except (ValidationError, TypeError, ValueError) as val_err:
                last_validation_error = val_err
                safe_err_msg = mask_secret(str(val_err))
                logger.warning(
                    f"OpenAI structured output validation error on attempt {attempts}/{max_retries + 1}: {safe_err_msg}"
                )

                if attempts <= max_retries:
                    # Retry once with corrected request emphasizing schema compliance
                    current_instructions = (
                        f"{instructions}\n\n"
                        f"CRITICAL REQUIREMENT: Your previous response failed Pydantic validation: {safe_err_msg}. "
                        f"You must strictly adhere to the required schema fields and types for {response_format.__name__}."
                    )
                    await asyncio.sleep(0.5)
                    continue
                else:
                    raise OpenAIResponseValidationError(
                        f"Structured output failed schema validation after {attempts} attempts: {safe_err_msg}"
                    )

            except AuthenticationError as auth_err:
                raise OpenAIAuthenticationError(f"OpenAI authentication failed: {mask_secret(str(auth_err))}")
            except RateLimitError as rate_err:
                raise OpenAIRateLimitError(f"OpenAI rate limit or quota exceeded: {mask_secret(str(rate_err))}")
            except APITimeoutError as time_err:
                raise OpenAITimeoutError(f"OpenAI API request timed out after {self.timeout}s: {mask_secret(str(time_err))}")
            except APIConnectionError as conn_err:
                raise OpenAIConnectionError(f"OpenAI connection error: {mask_secret(str(conn_err))}")
            except APIStatusError as status_err:
                raise OpenAIClientError(f"OpenAI API status error ({status_err.status_code}): {mask_secret(str(status_err))}")
            except APIError as api_err:
                raise OpenAIClientError(f"OpenAI API error: {mask_secret(str(api_err))}")
            except OpenAIClientError:
                raise
            except Exception as ex:
                raise OpenAIClientError(f"Unexpected error communicating with OpenAI: {mask_secret(str(ex))}")

        if last_validation_error:
            raise OpenAIResponseValidationError(
                f"Structured output failed validation: {mask_secret(str(last_validation_error))}"
            )
        raise OpenAIClientError("Failed to obtain valid response from OpenAI Responses API.")

    async def _execute_responses_call(
        self,
        instructions: str,
        input_text: str,
        response_format: Type[T]
    ) -> Optional[T]:
        """
        Executes the call through the Responses API endpoint (`client.responses.parse`),
        with seamless fallback to Structured Outputs chat completions (`client.beta.chat.completions.parse`).
        """
        # Try Responses API endpoint first
        try:
            if hasattr(self.client, "responses") and hasattr(self.client.responses, "parse"):
                logger.debug(f"Calling client.responses.parse with model={self.model_name}")
                response = await self.client.responses.parse(
                    model=self.model_name,
                    instructions=instructions,
                    input=input_text,
                    text_format=response_format,
                    timeout=self.timeout
                )
                if response and hasattr(response, "output_parsed") and response.output_parsed is not None:
                    return response.output_parsed
        except (AttributeError, TypeError, APIStatusError) as e:
            logger.debug(f"Responses API parse returned {e}; falling back to beta.chat.completions.parse")
        except Exception:
            # Re-raise authentication or rate limit errors directly
            raise

        # Structured Outputs chat completions fallback
        logger.debug(f"Calling client.beta.chat.completions.parse with model={self.model_name}")
        messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": input_text}
        ]
        completion = await self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            response_format=response_format,
            timeout=self.timeout
        )

        if completion.choices and len(completion.choices) > 0:
            message = completion.choices[0].message
            if hasattr(message, "parsed") and message.parsed is not None:
                return message.parsed
            if hasattr(message, "refusal") and message.refusal:
                raise OpenAIClientError(f"Model refused request: {message.refusal}")

        return None


# Global reusable singleton instance
_openai_client_instance: Optional[OpenAIClient] = None


def get_openai_client() -> OpenAIClient:
    """Returns the application-wide reusable OpenAIClient singleton."""
    global _openai_client_instance
    if _openai_client_instance is None:
        _openai_client_instance = OpenAIClient()
    return _openai_client_instance


def reset_openai_client():
    """Resets the singleton instance (useful for testing or reloading config)."""
    global _openai_client_instance
    _openai_client_instance = None
