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
            source_url="https://example.com"
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
        ical_str = result.decode('utf-8')
        assert 'BEGIN:VCALENDAR' in ical_str
        assert 'END:VCALENDAR' in ical_str
        assert 'BEGIN:VEVENT' in ical_str
        assert 'END:VEVENT' in ical_str
        assert 'CrossFit: WOD' in ical_str
        assert 'Coach: Tomasz Nowosielski' in ical_str

    def test_generate_ical_content_multiple_classes(self, exporter, sample_class):
        """Test generate_ical_content with multiple classes."""
        # Arrange
        class2 = ClassItem(
            date=datetime(2025, 11, 24, 7, 0, 0),
            event_name="HYROX",
            coach="Jane Doe",
            duration_min=45,
            source_url="https://example.com"
        )

        # Act
        result = exporter.generate_ical_content([sample_class, class2])

        # Assert
        assert isinstance(result, bytes)
        ical_str = result.decode('utf-8')
        assert ical_str.count('BEGIN:VEVENT') == 2
        assert ical_str.count('END:VEVENT') == 2
        assert 'CrossFit: WOD' in ical_str
        assert 'CrossFit: HYROX' in ical_str

    def test_generate_ical_content_class_without_duration(self, exporter):
        """Test generate_ical_content with a class that has no duration."""
        # Arrange
        class_no_duration = ClassItem(
            date=datetime(2025, 11, 24, 6, 0, 0),
            event_name="Open Gym",
            coach="John Smith",
            duration_min=None,
            source_url="https://example.com"
        )

        # Act
        result = exporter.generate_ical_content([class_no_duration])

        # Assert
        assert isinstance(result, bytes)
        ical_str = result.decode('utf-8')
        assert 'CrossFit: Open Gym' in ical_str
        # Should have default 1-hour duration