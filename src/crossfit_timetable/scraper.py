import inspect
import logging
import re
from datetime import date, datetime, timedelta
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from pydantic import BaseModel

from crossfit_timetable.settings import settings

logger = logging.getLogger(__name__)


class ClassItem(BaseModel):
    date: datetime  # Full datetime with time
    event_name: str
    coach: str
    duration_min: Optional[int]
    source_url: str
    location: Optional[str] = None  # Location from website


class CrossfitScraper:
    """Scraper for CrossFit timetable data."""

    # Compiled regex patterns for performance
    DATE_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}")

    @staticmethod
    async def _raise_for_status(response: aiohttp.ClientResponse) -> None:
        """Call raise_for_status, compatible with both sync and async versions (for mocks)."""
        if inspect.iscoroutinefunction(response.raise_for_status):
            await response.raise_for_status()
        else:
            response.raise_for_status()

    @staticmethod
    def get_valid_monday(target_date: Optional[date] = None) -> date:
        """Get a valid Monday date, defaulting to this week's Monday, with constraints."""
        today = datetime.now().date()

        if target_date is None:
            # Use this week's Monday
            monday = today - timedelta(days=today.weekday())
            return monday
        else:
            # Validate
            if target_date.weekday() != 0:  # 0 is Monday
                raise ValueError("Date must be a Monday")
            two_weeks_ago = today - timedelta(days=14)
            if target_date < two_weeks_ago:
                raise ValueError("Date cannot be more than 2 weeks in the past")
            return target_date

    def _parse_time_range(self, time_range: str) -> Optional[int]:
        """Parse time range like '06:00 - 07:00' and return duration in minutes."""
        parts = time_range.strip().split("-")
        if len(parts) != 2:
            return None

        try:
            start_parts = parts[0].strip().split(":")
            end_parts = parts[1].strip().split(":")

            start_hour = int(start_parts[0])
            start_min = int(start_parts[1])
            end_hour = int(end_parts[0])
            end_min = int(end_parts[1])

            start_total = start_hour * 60 + start_min
            end_total = end_hour * 60 + end_min

            return end_total - start_total
        except (ValueError, IndexError):
            return None

    def _parse_agenda_date(self, date_str: str) -> Optional[date]:
        """Parse date string like 'Pn, 2025-11-24' to extract the date."""
        match = self.DATE_REGEX.search(date_str)
        if match:
            return parse_date(match.group(0)).date()
        return None

    async def fetch_location(
        self, base_url: str, session: Optional[aiohttp.ClientSession] = None
    ) -> Optional[str]:
        """Fetch the location/address from the website's address section."""
        try:
            # Reuse provided session when possible to reduce overhead
            if session is None:
                async with aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as own_session:
                    async with own_session.get(base_url) as resp:
                        await self._raise_for_status(resp)
                        html = await resp.text()
            else:
                async with session.get(base_url) as resp:
                    await self._raise_for_status(resp)
                    html = await resp.text()

            soup = BeautifulSoup(html, "lxml")

            # Find the address section
            address_section = soup.find("address")
            if not address_section:
                logger.warning("Address section not found on the page.")
                return None

            # Extract address lines from paragraphs
            paragraphs = address_section.find_all("p")
            address_lines = []

            for p in paragraphs:
                text = p.get_text(strip=True)
                # Skip empty lines and the "Kontakt" header
                if text and text != "Kontakt":
                    address_lines.append(text)

            if address_lines:
                # Format: street, postal_code city
                # Remove the gym name (first line if it contains "CrossFit")
                filtered_lines = [
                    line
                    for line in address_lines
                    if line and line != "CrossFit Rzeszów 2.0"
                ]
                if filtered_lines:
                    # Join address lines with proper formatting
                    address = ", ".join(filtered_lines)
                    # Add Poland if not already present
                    if "Poland" not in address:
                        address += ", Poland"
                    logger.info(f"Fetched location: {address}")
                    return address
        except Exception as e:
            logger.warning(f"Failed to fetch location from website: {e}")
            return None

    async def fetch_timetable(
        self,
        start_date: Optional[date] = None,
        *,
        session: Optional[aiohttp.ClientSession] = None,
        location: Optional[str] = None,
    ) -> List[ClassItem]:
        """Fetch and parse the CrossFit timetable from the website."""
        monday = self.get_valid_monday(start_date)
        base_url = settings.scraper_base_url
        url = f"{base_url}/kalendarz-zajec?day={monday}&view=Agenda"

        logger.info(f"Fetching timetable for week starting {monday}")
        logger.debug(f"Requesting URL: {url}")

        async def ensure_location(
            active_session: aiohttp.ClientSession,
        ) -> Optional[str]:
            if location is not None:
                return location
            return await self.fetch_location(base_url, session=active_session)

        # Fetch location from website (cached) and timetable HTML, reusing session if provided
        if session is None:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            ) as own_session:
                resolved_location = await ensure_location(own_session)
                async with own_session.get(url) as resp:
                    await self._raise_for_status(resp)
                    html = await resp.text()
        else:
            resolved_location = await ensure_location(session)
            async with session.get(url) as resp:
                await self._raise_for_status(resp)
                html = await resp.text()

        soup = BeautifulSoup(html, "lxml")

        # Find the agenda table
        table = soup.find("table", class_="calendar_table_agenda")
        if not table:
            logger.error("Table with class schedule not found on the page.")
            raise RuntimeError("Table with class schedule not found on the page.")

        records: List[ClassItem] = []
        current_date = None

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if not cells:
                continue

            # Check if this row has a date cell (indicated by rowspan attribute)
            date_cell = cells[0]
            if date_cell.has_attr("rowspan"):
                # This is a new date
                date_str = date_cell.get_text(strip=True)
                current_date = self._parse_agenda_date(date_str)
                if not current_date:
                    continue

                # Parse the time and content from this row
                time_cell = cells[1]
                content_cell = cells[2]
            else:
                # This row continues the same date
                time_cell = cells[0]
                content_cell = cells[1]

            if not current_date:
                continue

            # Parse time range
            time_range = time_cell.get_text(strip=True)
            duration_min = self._parse_time_range(time_range)

            # Extract start time
            time_parts = time_range.split("-")[0].strip().split(":")
            try:
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                full_datetime = datetime.combine(
                    current_date, datetime.min.time()
                ).replace(hour=hour, minute=minute)
            except (ValueError, IndexError):
                continue

            # Parse event name and coach
            event_name_elem = content_cell.find("p", class_="event_name")
            if not event_name_elem:
                continue

            event_name = event_name_elem.get_text(strip=True)

            # Coach is the text after the event name
            coach = ""
            for text in content_cell.stripped_strings:
                if text != event_name:
                    coach = text
                    break

            # Extract source URL from the schedule-agenda-link
            schedule_link = content_cell.find("a", class_="schedule-agenda-link")
            source_url = url
            if schedule_link and schedule_link.has_attr("href"):
                relative_href = schedule_link.get("href")
                source_url = f"{base_url}{relative_href}"

            item = ClassItem(
                date=full_datetime,
                event_name=event_name,
                coach=coach,
                duration_min=duration_min,
                source_url=source_url,
                location=resolved_location,
            )
            records.append(item)

        # Sort by datetime, then by event name and coach for consistency
        records.sort(key=lambda x: (x.date, x.event_name, x.coach))

        logger.info(f"Successfully parsed {len(records)} classes from the timetable")

        return records
