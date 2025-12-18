"""
Unit tests for the FastAPI application.

Tests follow the AAA (Arrange, Act, Assert) pattern:
- Arrange: Set up test data and environment
- Act: Execute the code being tested
- Assert: Verify the results
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from crossfit_timetable.main import app
from crossfit_timetable.scraper import ClassItem


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_classes():
    """Create sample class data for testing."""
    return [
        ClassItem(
            date=datetime(2025, 11, 24, 6, 0, 0),
            event_name="WOD",
            coach="Tomasz Nowosielski",
            duration_min=60,
            source_url="https://example.com",
        ),
        ClassItem(
            date=datetime(2025, 11, 24, 7, 0, 0),
            event_name="HYROX",
            coach="Jan Kowalski",
            duration_min=60,
            source_url="https://example.com",
        ),
    ]


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_endpoint(self, client):
        """Test the root endpoint returns correct information."""
        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "CrossFit Timetable API"
        assert "/timetable" in data["endpoints"]
        assert "/timetable.ical" in data["endpoints"]


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_healthz_ready(self, client):
        """Test the ready health check endpoint."""
        # Act
        response = client.get("/healthz/ready")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_healthz_live(self, client):
        """Test the liveness health check endpoint."""
        # Act
        response = client.get("/healthz/live")

        # Assert
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAuthentication:
    """Tests for authentication."""

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_verify_token_with_bearer_token(self, client, sample_classes):
        """Test authentication with Bearer token in header."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_classes

            # Act
            response = client.get(
                "/timetable", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_verify_token_with_query_parameter(self, client, sample_classes):
        """Test authentication with token in query parameter."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_classes

            # Act
            response = client.get("/timetable?token=test-token")

            # Assert
            assert response.status_code == 200

    def test_verify_token_invalid(self, client):
        """Test authentication with invalid token."""
        # Act
        response = client.get(
            "/timetable", headers={"Authorization": "Bearer invalid-token"}
        )

        # Assert
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication token"

    def test_verify_token_missing(self, client):
        """Test authentication without token."""
        # Act
        response = client.get("/timetable")

        # Assert
        assert response.status_code == 401


class TestTimetableEndpoint:
    """Tests for the /timetable endpoint."""

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_timetable_success(self, client, sample_classes):
        """Test getting timetable with valid request."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_classes

            # Act
            response = client.get(
                "/timetable", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["event_name"] == "WOD"
            assert data[1]["event_name"] == "HYROX"
            mock_fetch.assert_called_once()

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_timetable_with_weeks_parameter(self, client, sample_classes):
        """Test getting timetable with weeks parameter."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_classes

            # Act
            response = client.get(
                "/timetable?weeks=2", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            assert mock_fetch.call_count == 2

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_timetable_no_classes_found(self, client):
        """Test getting timetable when no classes are found."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act
            response = client.get(
                "/timetable", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 404
            assert "No classes found" in response.json()["detail"]

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_timetable_value_error(self, client):
        """Test getting timetable with validation error."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = ValueError("Invalid date")

            # Act
            response = client.get(
                "/timetable", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 400
            assert "Invalid date" in response.json()["detail"]

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_timetable_generic_error(self, client):
        """Test getting timetable with unexpected error."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Unexpected error")

            # Act
            response = client.get(
                "/timetable", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 500
            assert "Failed to fetch timetable" in response.json()["detail"]


class TestICalEndpoint:
    """Tests for the /ical endpoint."""

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_ical_success(self, client, sample_classes):
        """Test getting iCal file with valid request."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_classes

            # Act
            response = client.get(
                "/timetable.ical", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/calendar; charset=utf-8"
            assert (
                "attachment; filename=crossfit_timetable.ics"
                in response.headers["content-disposition"]
            )
            assert b"BEGIN:VCALENDAR" in response.content
            assert b"CrossFit: WOD" in response.content

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_ical_with_weeks_parameter(self, client, sample_classes):
        """Test getting iCal file with weeks parameter."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = sample_classes

            # Act
            response = client.get(
                "/timetable.ical?weeks=2",
                headers={"Authorization": "Bearer test-token"},
            )

            # Assert
            assert response.status_code == 200
            # Should be called twice for 2 weeks
            assert mock_fetch.call_count == 2

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_ical_no_classes_found(self, client):
        """Test getting iCal when no classes are found."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = []

            # Act
            response = client.get(
                "/timetable.ical", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 404
            assert "No classes found" in response.json()["detail"]

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_ical_value_error(self, client):
        """Test getting iCal with validation error."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = ValueError("Invalid date")

            # Act
            response = client.get(
                "/timetable.ical", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 400
            assert "Invalid date" in response.json()["detail"]

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_ical_generic_error(self, client):
        """Test getting iCal with unexpected error."""
        # Arrange
        with patch(
            "crossfit_timetable.main.scraper.fetch_timetable", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Unexpected error")

            # Act
            response = client.get(
                "/timetable.ical", headers={"Authorization": "Bearer test-token"}
            )

            # Assert
            assert response.status_code == 500
            assert "Failed to generate iCal file" in response.json()["detail"]

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_ical_weeks_validation_min(self, client):
        """Test iCal endpoint with weeks below minimum."""
        # Act
        response = client.get(
            "/timetable.ical?weeks=0",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert - FastAPI should reject this with 422 Unprocessable Entity
        assert response.status_code == 422

    @patch("crossfit_timetable.main.settings.auth_token", "test-token")
    def test_get_ical_weeks_validation_max(self, client):
        """Test iCal endpoint with weeks above maximum."""
        # Act
        response = client.get(
            "/timetable.ical?weeks=7",
            headers={"Authorization": "Bearer test-token"},
        )

        # Assert - FastAPI should reject this with 422 Unprocessable Entity
        assert response.status_code == 422
