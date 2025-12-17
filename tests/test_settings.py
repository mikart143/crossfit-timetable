"""
Unit tests for the settings module.

Tests follow the AAA (Arrange, Act, Assert) pattern:
- Arrange: Set up test data and environment
- Act: Execute the code being tested
- Assert: Verify the results
"""

import os
from unittest.mock import patch
import pytest
from pydantic import ValidationError

from crossfit_timetable.settings import Settings


class TestSettings:
    """Tests for Settings configuration."""

    def test_settings_with_environment_variables(self):
        """Test Settings initialization with environment variables."""
        # Arrange
        env_vars = {
            "APP_SCRAPER_BASE_URL": "https://example.com",
            "APP_DEBUG": "true",
            "APP_AUTH_TOKEN": "test-token-123",
            "APP_ENABLE_SWAGGER": "true",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        assert settings.scraper_base_url == "https://example.com"
        assert settings.debug is True
        assert settings.auth_token == "test-token-123"
        assert settings.enable_swagger is True

    def test_settings_case_insensitive(self):
        """Test Settings with case-insensitive environment variables."""
        # Arrange
        env_vars = {
            "APP_SCRAPER_BASE_URL": "https://example.com",
            "app_debug": "false",  # lowercase
            "App_Auth_Token": "test-token",  # mixed case
            "APP_ENABLE_SWAGGER": "false",
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        assert settings.scraper_base_url == "https://example.com"
        assert settings.debug is False
        assert settings.auth_token == "test-token"
        assert settings.enable_swagger is False

    def test_settings_with_defaults(self):
        """Test Settings uses default values when env vars are not provided."""
        # Arrange
        env_vars = {}  # No env vars

        # Act
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()

        # Assert - should use default values
        assert settings.scraper_base_url == "https://crossfit2-rzeszow.cms.efitness.com.pl"
        assert settings.debug is False
        assert settings.auth_token == "default-token-change-me"
        assert settings.enable_swagger is True

    def test_settings_boolean_parsing(self):
        """Test Settings correctly parses boolean values."""
        # Arrange
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
        ]

        for bool_string, expected in test_cases:
            env_vars = {
                "APP_SCRAPER_BASE_URL": "https://example.com",
                "APP_DEBUG": bool_string,
                "APP_AUTH_TOKEN": "test-token",
                "APP_ENABLE_SWAGGER": bool_string,
            }

            # Act
            with patch.dict(os.environ, env_vars, clear=False):
                settings = Settings()

            # Assert
            assert settings.debug is expected
            assert settings.enable_swagger is expected

    def test_settings_env_prefix(self):
        """Test Settings only reads variables with APP_ prefix."""
        # Arrange
        env_vars = {
            "APP_SCRAPER_BASE_URL": "https://example.com",
            "APP_DEBUG": "true",
            "APP_AUTH_TOKEN": "test-token",
            "APP_ENABLE_SWAGGER": "true",
            "SCRAPER_BASE_URL": "https://ignored.com",  # Without APP_ prefix
            "DEBUG": "false",  # Without APP_ prefix
        }

        # Act
        with patch.dict(os.environ, env_vars, clear=False):
            settings = Settings()

        # Assert
        # Should use APP_ prefixed values, not the non-prefixed ones
        assert settings.scraper_base_url == "https://example.com"
        assert settings.debug is True
