from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with APP_ prefix."""

    model_config = SettingsConfigDict(
        env_prefix="APP_",
        case_sensitive=False,
        env_file=".env" if Path(".env").exists() else None,
    )

    # Base URL for the CrossFit timetable scraper
    scraper_base_url: str = "https://crossfit2-rzeszow.cms.efitness.com.pl"

    # CrossFit gym location (hardcoded)
    gym_location: str = "Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland"

    # Geographic coordinates for CrossFit 2.0 Rzeszów
    gym_latitude: float = 50.0386
    gym_longitude: float = 22.0026

    # CrossFit gym title for calendar entries
    gym_title: str = "CrossFit 2.0 Rzeszów"

    # Debug mode flag
    debug: bool = False

    # Authentication token for API access
    auth_token: str = "default-token-change-me"

    # Enable Swagger UI
    enable_swagger: bool = True


# Create a global settings instance
settings = Settings()
