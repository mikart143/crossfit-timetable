import logging
from datetime import datetime, timedelta
from typing import List
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event, Timezone, TimezoneStandard, vText

from .scraper import ClassItem

logger = logging.getLogger(__name__)

# Geographic coordinates for CrossFit 2.0 Rzeszów
# Source: Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland
CROSSFIT_RZESZOW_LAT = 50.0386
CROSSFIT_RZESZOW_LON = 22.0026
CROSSFIT_RZESZOW_TITLE = "CrossFit 2.0 Rzeszów"


class ICalExporter:
    """Exports CrossFit class information to iCal format."""

    def __init__(self):
        """Initialize the iCal exporter."""
        pass

    def _create_structured_location(self, location: str) -> str:
        """
        Create X-APPLE-STRUCTURED-LOCATION property value.

        This is an Apple-specific extension that enables enhanced location features
        in Apple Calendar, including map integration and travel time alerts.

        Format: geo:latitude,longitude with parameters:
        - VALUE=URI: Indicates the value is a URI
        - X-ADDRESS: Physical address with \\n as line separator
        - X-TITLE: Location title/name
        - X-APPLE-RADIUS: Optional radius in meters (defaults to ~50m)

        Args:
            location: Human-readable address string

        Returns:
            Formatted geo URI string for X-APPLE-STRUCTURED-LOCATION
        """
        # Format address for X-APPLE-STRUCTURED-LOCATION
        # Apple Calendar expects \\n (literal backslash-n) for line breaks in X-ADDRESS
        address_formatted = location.replace(", ", "\\n")

        # Build the geo URI with coordinates
        geo_uri = f"geo:{CROSSFIT_RZESZOW_LAT},{CROSSFIT_RZESZOW_LON}"

        return geo_uri

    def generate_ical_content(self, classes: List[ClassItem]) -> bytes:
        """
        Generate iCal content as bytes.

        Args:
            classes: List of ClassItem objects to export.

        Returns:
            iCal content as bytes.
        """
        if not classes:
            logger.warning("No classes to export to iCal.")
            return b""

        cal = Calendar()
        cal.add("prodid", "-//CrossFit Timetable//crossfit-timetable//")
        cal.add("version", "2.0")

        # Add timezone information for Google Calendar compatibility
        tz = Timezone()
        tz.add("tzid", "Europe/Warsaw")
        tz_standard = TimezoneStandard()
        tz_standard.add("tzname", "CET")
        tz_standard.add("dtstart", datetime(1970, 10, 26, 3, 0, 0))
        tz_standard.add("rrule", {"freq": "yearly", "bymonth": 10, "byday": "-1su"})
        tz_standard.add("tzoffsetfrom", timedelta(hours=2))
        tz_standard.add("tzoffsetto", timedelta(hours=1))
        tz.add_component(tz_standard)
        tz_daylight = TimezoneStandard()
        tz_daylight.add("tzname", "CEST")
        tz_daylight.add("dtstart", datetime(1970, 3, 29, 2, 0, 0))
        tz_daylight.add("rrule", {"freq": "yearly", "bymonth": 3, "byday": "-1su"})
        tz_daylight.add("tzoffsetfrom", timedelta(hours=1))
        tz_daylight.add("tzoffsetto", timedelta(hours=2))
        tz.add_component(tz_daylight)
        cal.add_component(tz)

        warsaw_tz = ZoneInfo("Europe/Warsaw")

        for class_item in classes:
            event = Event()

            # Make datetime timezone-aware
            start_time = class_item.date.replace(tzinfo=warsaw_tz)

            # Calculate end time
            if class_item.duration_min:
                end_time = start_time + timedelta(minutes=class_item.duration_min)
            else:
                # Default to 1 hour if duration not specified
                end_time = start_time + timedelta(hours=1)

            event.add("summary", f"CrossFit: {class_item.event_name}")
            event.add("dtstart", start_time)
            event.add("dtend", end_time)
            # Use location from scraper if available, otherwise use fallback
            location = class_item.location or "CrossFit 2.0 Rzeszów"
            event.add("location", location)
            event.add(
                "description",
                f"CrossFit Class\nCoach: {class_item.coach}\nSource: {class_item.source_url}",
            )
            # Add unique UID for Google Calendar
            event.add(
                "uid",
                f"{class_item.date.isoformat()}-{class_item.event_name.replace(' ', '-')}-{class_item.coach.replace(' ', '-')}-crossfit-timetable",
            )

            # Add X-APPLE-STRUCTURED-LOCATION for enhanced Apple Calendar support
            # This is an Apple-specific extension (not part of RFC 5545)
            # Enables map integration, travel time alerts, and location-based features
            # Format address for X-ADDRESS parameter (use \\n for line breaks)
            address_formatted = location.replace(", ", "\\n")
            geo_uri = self._create_structured_location(location)

            # Add the property with all required parameters
            # Note: icalendar library handles this as a custom property
            event.add(
                "X-APPLE-STRUCTURED-LOCATION",
                geo_uri,
                parameters={
                    "VALUE": "URI",
                    "X-ADDRESS": address_formatted,
                    "X-TITLE": CROSSFIT_RZESZOW_TITLE,
                    "X-APPLE-RADIUS": "49.91",  # ~50 meters radius
                },
            )

            cal.add_component(event)

        return cal.to_ical()
