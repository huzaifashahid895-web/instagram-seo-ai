# backend/app/config.py — Environment-driven settings via pydantic-settings
# Cost classification: FREE + OPEN SOURCE

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All app configuration, read from environment or .env file.

    Defaults are dev-friendly. Production overrides via .env or environment.
    """

    # Database
    DATABASE_URL: str = "sqlite:///./aism.db"

    # Chroma vector DB
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8000
    CHROMA_PERSIST_DIR: str = "../chroma_data"

    # Local file storage
    STORAGE_ROOT: str = "../storage"

    # Deterministic media analysis executables
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    # Logging
    LOG_LEVEL: str = "INFO"

    # CORS (comma-separated origins)
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:5174",  # Vite dev server (alternate port)
        "http://localhost:3000",  # Alternate dev port
    ]

    # Security / Auth (placeholder for Step 4)
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Instagram OAuth (placeholder for Step 4)
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    INSTAGRAM_REDIRECT_URI: str = "http://localhost:8000/social-accounts/callback"
    
    # Instagram Webhooks
    INSTAGRAM_WEBHOOK_VERIFY_TOKEN: str = ""

    # Encryption key for social account tokens at rest (Step 4)
    ENCRYPTION_KEY: str = ""

    # AI Models Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b"
    
    EMBEDDINGS_MODEL: str = "BAAI/bge-small-en-v1.5"
    
    WHISPER_MODEL: str = "base"
    WHISPER_DEVICE: str = "cpu"

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
