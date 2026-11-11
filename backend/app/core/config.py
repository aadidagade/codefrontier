from pathlib import Path
from typing import List, Optional
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base backend directory: d:\hackathons\codefrontier\backend
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Production-oriented application settings loaded via Pydantic v2.
    Safely handles secrets, paths, and environment overrides.
    """

    model_config = SettingsConfigDict(
        env_file=(str(BACKEND_DIR / ".env"), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # Application Information
    APP_NAME: str = "Knowledge Handover Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/knowledge_handover",
        description="Async PostgreSQL connection URL (postgresql+asyncpg://...)",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_PRE_PING: bool = True

    # Security & JWT Tokens
    JWT_SECRET_KEY: str = Field(
        ...,
        description="Cryptographically secure secret key for JWT signing",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Google Gemini AI Configuration
    GEMINI_API_KEY: str = Field(
        ...,
        description="Official Google Gemini API Key from Google AI Studio",
    )
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    # Frontend Integration & CORS
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # File Storage & Uploads
    UPLOAD_DIR: str = "storage/uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    @property
    def upload_path(self) -> Path:
        """Returns verified absolute directory path for uploaded documents."""
        path = BACKEND_DIR / self.UPLOAD_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    def is_gemini_configured(self) -> bool:
        """Verifies if the Gemini API key is populated and not a placeholder."""
        val = self.GEMINI_API_KEY.strip()
        return bool(val and val != "YOUR_GEMINI_API_KEY" and not val.startswith("YOUR_"))

    def is_database_configured(self) -> bool:
        """Verifies if the database URL has a real password configured."""
        return "YOUR_PASSWORD" not in self.DATABASE_URL


# Global settings singleton instance
settings = Settings()
