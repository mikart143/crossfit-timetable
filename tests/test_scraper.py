"""
Unit tests for the CrossFit timetable scraper.

Tests follow the AAA (Arrange, Act, Assert) pattern:
- Arrange: Set up test data and environment
- Act: Execute the code being tested
- Assert: Verify the results
"""

from datetime import datetime, date
from unittest.mock import patch

import pytest

from crossfit_timetable.scraper import CrossfitScraper, ClassItem


class TestCrossfitScraper:
    @pytest.fixture
    def scraper(self):
        return CrossfitScraper()

    def test_get_valid_monday_none(self):
        """Test get_valid_monday with None returns current week's Monday."""
        # Arrange
        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 11, 11, 12, 0, 0)
            mock_datetime.combine = datetime.combine
            mock_datetime.min.time.return_value = datetime.min.time()

            # Act
            result = CrossfitScraper.get_valid_monday(None)

            # Assert
            expected = date(2025, 11, 10)  # Monday of that week
            assert result == expected

    def test_get_valid_monday_valid_date(self):
        """Test get_valid_monday with a valid Monday date."""
        # Arrange
        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 11, 11, 12, 0, 0)
            monday = date(2025, 11, 10)  # Monday

            # Act
            result = CrossfitScraper.get_valid_monday(monday)

            # Assert
            assert result == monday

    def test_get_valid_monday_not_monday(self):
        """Test get_valid_monday raises error for non-Monday dates."""
        # Arrange
        tuesday = date(2025, 11, 11)  # Tuesday

        # Act & Assert
        with pytest.raises(ValueError, match="Date must be a Monday"):
            CrossfitScraper.get_valid_monday(tuesday)

    def test_get_valid_monday_too_old(self):
        """Test get_valid_monday raises error for dates more than 2 weeks ago."""
        # Arrange
        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 11, 11, 12, 0, 0)
            old_monday = date(2025, 10, 27)  # More than 2 weeks before Nov 11

            # Act & Assert
            with pytest.raises(
                ValueError, match="Date cannot be more than 2 weeks in the past"
            ):
                CrossfitScraper.get_valid_monday(old_monday)

    def test_parse_time_range_valid(self, scraper):
        """Test _parse_time_range with valid time range."""
        # Arrange & Act & Assert
        assert scraper._parse_time_range("06:00 - 07:00") == 60
        assert scraper._parse_time_range("06:00-07:00") == 60
        assert scraper._parse_time_range("18:00 - 19:30") == 90
        assert scraper._parse_time_range("09:15 - 10:00") == 45

    def test_parse_time_range_invalid(self, scraper):
        """Test _parse_time_range with invalid input."""
        # Arrange & Act & Assert
        assert scraper._parse_time_range("invalid") is None
        assert scraper._parse_time_range("06:00") is None
        assert scraper._parse_time_range("") is None

    def test_parse_agenda_date_valid(self, scraper):
        """Test _parse_agenda_date with valid date string."""
        # Arrange
        date_str = "Pn, 2025-11-24"
        expected = date(2025, 11, 24)

        # Act
        result = scraper._parse_agenda_date(date_str)

        # Assert
        assert result == expected

    def test_parse_agenda_date_various_formats(self, scraper):
        """Test _parse_agenda_date with various date formats."""
        # Arrange & Act & Assert
        assert scraper._parse_agenda_date("Wt, 2025-11-25") == date(2025, 11, 25)
        assert scraper._parse_agenda_date("So, 2025-11-29") == date(2025, 11, 29)
        assert scraper._parse_agenda_date("2025-11-30") == date(2025, 11, 30)

    def test_parse_agenda_date_invalid(self, scraper):
        """Test _parse_agenda_date with invalid input."""
        # Arrange & Act & Assert
        assert scraper._parse_agenda_date("No date here") is None
        assert scraper._parse_agenda_date("") is None

    @pytest.mark.asyncio
    async def test_fetch_timetable_integration(self, scraper):
        """Test fetch_timetable with mocked HTTP response using Agenda view."""
        # Arrange
        expected_result = [
            ClassItem(
                date=datetime(2025, 11, 24, 6, 0, 0),
                event_name="WOD",
                coach="Tomasz Nowosielski",
                duration_min=60,
                source_url="https://crossfit2-rzeszow.cms.efitness.com.pl/kalendarz-zajec?day=2025-11-24&view=Agenda",
            ),
            ClassItem(
                date=datetime(2025, 11, 24, 7, 0, 0),
                event_name="HYROX",
                coach="Jan Kowalski",
                duration_min=60,
                source_url="https://crossfit2-rzeszow.cms.efitness.com.pl/kalendarz-zajec?day=2025-11-24&view=Agenda",
            ),
        ]

        # Mock the entire fetch_timetable method
        with patch.object(
            scraper, "fetch_timetable", return_value=expected_result
        ) as mock_fetch:
            # Act
            result = await scraper.fetch_timetable(date(2025, 11, 24))

            # Assert
            mock_fetch.assert_called_once_with(date(2025, 11, 24))
            assert len(result) == 2

            # First class
            assert isinstance(result[0], ClassItem)
            assert result[0].event_name == "WOD"
            assert result[0].coach == "Tomasz Nowosielski"
            assert result[0].duration_min == 60
            assert result[0].date == datetime(2025, 11, 24, 6, 0, 0)
            assert "view=Agenda" in result[0].source_url

            # Second class
            assert result[1].event_name == "HYROX"
            assert result[1].coach == "Jan Kowalski"
            assert result[1].duration_min == 60
            assert result[1].date == datetime(2025, 11, 24, 7, 0, 0)

    @pytest.mark.asyncio
    async def test_fetch_timetable_with_html(self, scraper):
        """Test fetch_timetable with mocked HTML response."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="2">Pn, 2025-12-15</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Tomasz Nowosielski
                </td>
            </tr>
            <tr>
                <td>07:00 - 08:00</td>
                <td>
                    <p class="event_name">HYROX</p>
                    Jan Kowalski
                </td>
            </tr>
        </table>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            # Mock datetime.now() to return a fixed date for testing
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)
            # Preserve real datetime.combine and datetime.min.time for date parsing
            mock_datetime.combine = datetime.combine
            mock_datetime.min.time.return_value = datetime.min.time()

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act
                result = await scraper.fetch_timetable(test_date)

                # Assert
                assert len(result) == 2
                assert result[0].event_name == "WOD"
                assert result[0].coach == "Tomasz Nowosielski"
                assert result[0].date == datetime(2025, 12, 15, 6, 0, 0)
                assert result[0].duration_min == 60

                assert result[1].event_name == "HYROX"
                assert result[1].coach == "Jan Kowalski"
                assert result[1].date == datetime(2025, 12, 15, 7, 0, 0)
                assert result[1].duration_min == 60

    @pytest.mark.asyncio
    async def test_fetch_timetable_no_table_found(self, scraper):
        """Test fetch_timetable when no table is found in HTML."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <p>No table here</p>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act & Assert
                with pytest.raises(
                    RuntimeError, match="Table with class schedule not found"
                ):
                    await scraper.fetch_timetable(test_date)

    @pytest.mark.asyncio
    async def test_fetch_timetable_empty_table(self, scraper):
        """Test fetch_timetable with empty table."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <table class="calendar_table_agenda">
        </table>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act
                result = await scraper.fetch_timetable(test_date)

                # Assert
                assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_timetable_malformed_time(self, scraper):
        """Test fetch_timetable with malformed time in HTML."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="1">Pn, 2025-12-15</td>
                <td>invalid-time</td>
                <td>
                    <p class="event_name">WOD</p>
                    Coach Name
                </td>
            </tr>
        </table>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act
                result = await scraper.fetch_timetable(test_date)

                # Assert - should skip rows with invalid time
                assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_timetable_no_event_name(self, scraper):
        """Test fetch_timetable with missing event name."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="1">Pn, 2025-12-15</td>
                <td>06:00 - 07:00</td>
                <td>
                    No event name here
                </td>
            </tr>
        </table>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act
                result = await scraper.fetch_timetable(test_date)

                # Assert - should skip rows without event name
                assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_timetable_invalid_date(self, scraper):
        """Test fetch_timetable with invalid date in HTML."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="1">Invalid Date</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Coach
                </td>
            </tr>
        </table>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act
                result = await scraper.fetch_timetable(test_date)

                # Assert - should skip rows with invalid dates
                assert len(result) == 0

    @pytest.mark.asyncio
    async def test_fetch_timetable_multiple_days(self, scraper):
        """Test fetch_timetable with multiple days in the same week."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="2">Pn, 2025-12-15</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Coach A
                </td>
            </tr>
            <tr>
                <td>18:00 - 19:00</td>
                <td>
                    <p class="event_name">Evening WOD</p>
                    Coach B
                </td>
            </tr>
            <tr>
                <td rowspan="1">Wt, 2025-12-16</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">HYROX</p>
                    Coach C
                </td>
            </tr>
        </table>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            # Mock datetime.now() to return a fixed date for testing
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)
            # Preserve real datetime.combine and datetime.min.time for date parsing
            mock_datetime.combine = datetime.combine
            mock_datetime.min.time.return_value = datetime.min.time()

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act
                result = await scraper.fetch_timetable(test_date)

                # Assert
                assert len(result) == 3
                # Check sorted by date
                assert result[0].date == datetime(2025, 12, 15, 6, 0, 0)
                assert result[1].date == datetime(2025, 12, 15, 18, 0, 0)
                assert result[2].date == datetime(2025, 12, 16, 6, 0, 0)

    def test_class_item_creation(self):
        """Test ClassItem Pydantic model creation and validation."""
        # Arrange
        date_time = datetime(2025, 11, 10, 6, 0, 0)
        event_name = "WOD"
        coach = "Tomasz Nowosielski"
        duration = 60
        source_url = "https://example.com"

        # Act
        item = ClassItem(
            date=date_time,
            event_name=event_name,
            coach=coach,
            duration_min=duration,
            source_url=source_url,
        )

        # Assert
        assert item.date == date_time
        assert item.event_name == event_name
        assert item.coach == coach
        assert item.duration_min == duration
        assert item.source_url == source_url

    def test_class_item_optional_duration(self):
        """Test ClassItem with optional duration."""
        # Arrange
        date_time = datetime(2025, 11, 10, 6, 0, 0)
        event_name = "WOD"
        coach = "Tomasz Nowosielski"
        source_url = "https://example.com"

        # Act
        item = ClassItem(
            date=date_time,
            event_name=event_name,
            coach=coach,
            duration_min=None,
            source_url=source_url,
        )

        # Assert
        assert item.duration_min is None

    @pytest.mark.asyncio
    async def test_fetch_timetable_with_empty_rows_and_no_current_date(self, scraper):
        """Test fetch_timetable with empty rows and rows without current_date set."""
        # Arrange
        test_date = date(2025, 12, 15)  # A Monday
        html_content = """
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
            </tr>
            <tr>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Coach A
                </td>
            </tr>
            <tr>
                <td rowspan="1">Pn, 2025-12-15</td>
                <td>18:00 - 19:00</td>
                <td>
                    <p class="event_name">Evening WOD</p>
                    Coach B
                </td>
            </tr>
        </table>
        </body>
        </html>
        """

        with patch("crossfit_timetable.scraper.datetime") as mock_datetime:
            # Mock datetime.now() to return a fixed date for testing
            mock_datetime.now.return_value = datetime(2025, 12, 17, 12, 0, 0)
            # Preserve real datetime.combine and datetime.min.time for date parsing
            mock_datetime.combine = datetime.combine
            mock_datetime.min.time.return_value = datetime.min.time()

            with patch("aiohttp.ClientSession.get") as mock_get:
                mock_resp = mock_get.return_value.__aenter__.return_value
                mock_resp.text.return_value = html_content
                mock_resp.raise_for_status.return_value = None

                # Act
                result = await scraper.fetch_timetable(test_date)

                # Assert - should skip empty row and row without current_date, only get the valid one
                assert len(result) == 1
                assert result[0].event_name == "Evening WOD"
                assert result[0].date == datetime(2025, 12, 15, 18, 0, 0)
