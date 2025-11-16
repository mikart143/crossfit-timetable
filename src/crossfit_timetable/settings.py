from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with APP_ prefix."""

    model_config = SettingsConfigDict(
        env_prefix="APP_", 
        case_sensitive=False, 
        env_file=".env" if Path(".env").exists() else None
    )

    # Base URL for the CrossFit timetable scraper
    scraper_base_url: str

    # Debug mode flag
    debug: bool

    # Authentication token for API access
    auth_token: str

    # Enable Swagger UI
    enable_swagger: bool



# Create a global settings instance
settings = Settings()