"""
Unit tests for the iCal exporter.

Tests follow the AAA (Arrange, Act, Assert) pattern:
- Arrange: Set up test data and environment
- Act: Execute the code being tested
- Assert: Verify the results
"""

import pytest
from datetime import datetime

from crossfit_timetable.ical_exporter import ICalExporter
from crossfit_timetable.scraper import ClassItem


class TestICalExporter:
    @pytest.fixture
    def exporter(self):
        return ICalExporter()

    @pytest.fixture
    def sample_class(self):
        return ClassItem(
            date=datetime(2025, 11, 24, 6, 0, 0),
            event_name="WOD",
            coach="Tomasz Nowosielski",
            duration_min=60,
            source_url="https://example.com",
        )

    def test_init(self):
        """Test ICalExporter initialization."""
        exporter = ICalExporter()
        assert exporter is not None

    def test_generate_ical_content_no_classes(self, exporter):
        """Test generate_ical_content with empty class list."""
        # Act
        result = exporter.generate_ical_content([])

        # Assert
        assert result == b""

    def test_generate_ical_content_single_class(self, exporter, sample_class):
        """Test generate_ical_content with a single class."""
        # Act
        result = exporter.generate_ical_content([sample_class])

        # Assert
        assert isinstance(result, bytes)
        assert len(result) > 0
        ical_str = result.decode("utf-8")
        assert "BEGIN:VCALENDAR" in ical_str
        assert "END:VCALENDAR" in ical_str
        assert "BEGIN:VEVENT" in ical_str
        assert "END:VEVENT" in ical_str
        assert "CrossFit: WOD" in ical_str
        assert "Coach: Tomasz Nowosielski" in ical_str

    def test_generate_ical_content_multiple_classes(self, exporter, sample_class):
        """Test generate_ical_content with multiple classes."""
        # Arrange
        class2 = ClassItem(
            date=datetime(2025, 11, 24, 7, 0, 0),
            event_name="HYROX",
            coach="Jane Doe",
            duration_min=45,
            source_url="https://example.com",
        )

        # Act
        result = exporter.generate_ical_content([sample_class, class2])

        # Assert
        assert isinstance(result, bytes)
        ical_str = result.decode("utf-8")
        assert ical_str.count("BEGIN:VEVENT") == 2
        assert ical_str.count("END:VEVENT") == 2
        assert "CrossFit: WOD" in ical_str
        assert "CrossFit: HYROX" in ical_str

    def test_generate_ical_content_class_without_duration(self, exporter):
        """Test generate_ical_content with a class that has no duration."""
        # Arrange
        class_no_duration = ClassItem(
            date=datetime(2025, 11, 24, 6, 0, 0),
            event_name="Open Gym",
            coach="John Smith",
            duration_min=None,
            source_url="https://example.com",
        )

        # Act
        result = exporter.generate_ical_content([class_no_duration])

        # Assert
        assert isinstance(result, bytes)
        ical_str = result.decode("utf-8")
        assert "CrossFit: Open Gym" in ical_str
        # Should have default 1-hour duration

    def test_generate_ical_with_x_apple_structured_location(self, exporter):
        """Test that X-APPLE-STRUCTURED-LOCATION property is added to events."""
        # Arrange
        sample_class = ClassItem(
            date=datetime(2025, 11, 24, 6, 0, 0),
            event_name="WOD",
            coach="Tomasz Nowosielski",
            duration_min=60,
            source_url="https://example.com",
            location="Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland",
        )

        # Act
        result = exporter.generate_ical_content([sample_class])

        # Assert
        assert isinstance(result, bytes)
        ical_str = result.decode("utf-8")

        # Check that X-APPLE-STRUCTURED-LOCATION is present
        assert "X-APPLE-STRUCTURED-LOCATION" in ical_str

        # Check that it contains geo URI with coordinates
        # Note: icalendar library escapes commas as \, in text values
        assert ("geo:50.0386,22.0026" in ical_str or "geo:50.0386\\,22.0026" in ical_str)

        # Check that it has the VALUE=URI parameter
        assert "VALUE=URI" in ical_str

        # Check that X-ADDRESS parameter is present with address
        assert "X-ADDRESS" in ical_str

        # Check that X-TITLE parameter is present
        # Remove whitespace and line breaks for comparison due to RFC 5545 line folding
        ical_str_normalized = ical_str.replace("\r\n ", "").replace("\n ", "")
        assert ("X-TITLE=\"CrossFit 2.0 Rzeszów\"" in ical_str_normalized or 
                "X-TITLE=CrossFit 2.0 Rzeszów" in ical_str_normalized)

        # Check that X-APPLE-RADIUS is present
        assert "X-APPLE-RADIUS=49.91" in ical_str

    def test_generate_ical_with_x_apple_structured_location_no_location(
        self, exporter
    ):
        """Test X-APPLE-STRUCTURED-LOCATION with fallback location."""
        # Arrange - class without explicit location
        sample_class = ClassItem(
            date=datetime(2025, 11, 24, 6, 0, 0),
            event_name="WOD",
            coach="Tomasz Nowosielski",
            duration_min=60,
            source_url="https://example.com",
            location=None,  # No location provided
        )

        # Act
        result = exporter.generate_ical_content([sample_class])

        # Assert
        assert isinstance(result, bytes)
        ical_str = result.decode("utf-8")

        # Should still have X-APPLE-STRUCTURED-LOCATION with fallback
        assert "X-APPLE-STRUCTURED-LOCATION" in ical_str
        # Note: icalendar library escapes commas as \, in text values
        assert ("geo:50.0386,22.0026" in ical_str or "geo:50.0386\\,22.0026" in ical_str)

        # Should use fallback location
        assert "CrossFit 2.0 Rzeszów" in ical_str

    def test_x_apple_structured_location_format(self, exporter):
        """Test that X-APPLE-STRUCTURED-LOCATION follows Apple's format."""
        # Arrange
        sample_class = ClassItem(
            date=datetime(2025, 11, 24, 6, 0, 0),
            event_name="WOD",
            coach="Tomasz Nowosielski",
            duration_min=60,
            source_url="https://example.com",
            location="Street Name 15, 35-105 City, Country",
        )

        # Act
        result = exporter.generate_ical_content([sample_class])

        # Assert
        ical_str = result.decode("utf-8")

        # The format should be:
        # X-APPLE-STRUCTURED-LOCATION;VALUE=URI;X-ADDRESS=...;X-APPLE-RADIUS=...;X-TITLE=...:geo:lat,lon
        # Check that geo: comes at the end (the actual value)
        # Note: icalendar library escapes commas as \, in text values
        # Remove whitespace and line breaks for comparison due to RFC 5545 line folding
        ical_str_normalized = ical_str.replace("\r\n ", "").replace("\n ", "")
        assert (":geo:50.0386,22.0026" in ical_str_normalized or ":geo:50.0386\\,22.0026" in ical_str_normalized)

        # Standard LOCATION property should still be present
        assert "LOCATION:" in ical_str
