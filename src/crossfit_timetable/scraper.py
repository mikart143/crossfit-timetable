import logging
import re
from datetime import datetime, timedelta, date
from typing import List, Optional

import aiohttp
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ClassItem(BaseModel):
    date: datetime  # Full datetime with time
    event_name: str
    coach: str
    duration_min: Optional[int]
    source_url: str

class CrossfitScraper:
    """Scraper for CrossFit timetable data."""
    
    # Compiled regex patterns for performance
    DATE_REGEX = re.compile(r"\d{4}-\d{2}-\d{2}")
    
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
        parts = time_range.strip().split('-')
        if len(parts) != 2:
            return None
        
        try:
            start_parts = parts[0].strip().split(':')
            end_parts = parts[1].strip().split(':')
            
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

    async def fetch_timetable(self, start_date: Optional[date] = None) -> List[ClassItem]:
        """Fetch and parse the CrossFit timetable from the website."""
        monday = self.get_valid_monday(start_date)
        url = f"https://crossfit2-rzeszow.cms.efitness.com.pl/kalendarz-zajec?day={monday}&view=Agenda"
        
        logger.info(f"Fetching timetable for week starting {monday}")
        logger.debug(f"Requesting URL: {url}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                resp.raise_for_status()
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
            time_parts = time_range.split('-')[0].strip().split(':')
            try:
                hour = int(time_parts[0])
                minute = int(time_parts[1])
                full_datetime = datetime.combine(current_date, datetime.min.time()).replace(hour=hour, minute=minute)
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
            
            item = ClassItem(
                date=full_datetime,
                event_name=event_name,
                coach=coach,
                duration_min=duration_min,
                source_url=url
            )
            records.append(item)
    
        # Sort by datetime, then by event name and coach for consistency
        records.sort(key=lambda x: (x.date, x.event_name, x.coach))
        
        logger.info(f"Successfully parsed {len(records)} classes from the timetable")
    
        return records