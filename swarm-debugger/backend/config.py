import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration for SWARM DEBUGGER.
    All sensitive credentials and environment overrides are loaded via environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Settings
    PROJECT_NAME: str = "SWARM DEBUGGER"
    VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # AI Configuration (OpenAI Responses API integration stub)
    # Never hardcode keys; configure via OPENAI_API_KEY environment variable.
    OPENAI_API_KEY: Optional[str] = None
    MODEL_NAME: str = "gpt-5.6-luna"
    AI_TIMEOUT_SECONDS: int = 45

    # Sandbox / Execution Configuration
    DOCKER_IMAGE: str = "swarm-sandbox:latest"
    SANDBOX_TIMEOUT_SECONDS: int = 30
    SANDBOX_MEMORY_LIMIT: str = "512m"
    SANDBOX_CPU_LIMIT: float = 1.0

    # Multi-Agent Debate Configuration
    DEFAULT_MAX_ROUNDS: int = 3

    # Database
    DATABASE_URL: str = "sqlite:///./swarm_debugger.db"


settings = Settings()
