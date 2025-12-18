import asyncio
import logging
from datetime import date, timedelta
from importlib.metadata import version
from typing import List, Optional

import aiohttp
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from crossfit_timetable.ical_exporter import ICalExporter
from crossfit_timetable.scraper import ClassItem, CrossfitScraper
from crossfit_timetable.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
logging.getLogger("uvicorn.access").setLevel(
    logging.DEBUG if settings.debug else logging.INFO
)

app = FastAPI(
    title="CrossFit Timetable API",
    description="API for CrossFit 2.0 Rzeszów timetable data",
    version=version("crossfit-timetable"),
    openapi_url="/openapi.json" if settings.enable_swagger else None,
    docs_url="/docs" if settings.enable_swagger else None,
)

scraper = CrossfitScraper()
exporter = ICalExporter()

# Security scheme
security = HTTPBearer(auto_error=False)  # Make it optional


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = Query(
        None, description="API token (alternative to Authorization header)"
    ),
):
    """Verify the provided token against the configured auth token.
    Accepts token via Bearer token in Authorization header or as query parameter.
    """
    provided_token = None

    # Check Bearer token first
    if credentials and credentials.credentials:
        provided_token = credentials.credentials
    # Check query parameter as fallback
    elif token:
        provided_token = token

    if not provided_token or provided_token != settings.auth_token:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

    return provided_token


@app.get("/healthz/ready")
async def healthz_ready():
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/healthz/live")
async def healthz_live():
    """Liveness check endpoint."""

    return {"status": "ok"}


@app.get("/")
async def root():
    """Get basic information about the API."""
    return {
        "message": "CrossFit Timetable API",
        "endpoints": {
            "/timetable": "Get timetable data as JSON",
            "/timetable.ical": "Download timetable as iCal file",
        },
    }


@app.get("/timetable", response_model=List[ClassItem])
async def get_timetable(
    weeks: int = Query(1, ge=1, le=6, description="Number of weeks to include (1-6)"),
    token: str = Depends(verify_token),
):
    """Get the CrossFit timetable data as JSON."""
    try:
        today = date.today()
        current_monday = today - timedelta(days=today.weekday())
        mondays = [current_monday + timedelta(weeks=i) for i in range(weeks)]

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            location = await scraper.fetch_location(
                settings.scraper_base_url, session=session
            )
            week_tasks = [
                scraper.fetch_timetable(monday, session=session, location=location)
                for monday in mondays
            ]
            week_results = await asyncio.gather(*week_tasks)

        all_classes = [cls for week in week_results for cls in week]

        if not all_classes:
            raise HTTPException(status_code=404, detail="No classes found")

        return all_classes
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching timetable: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch timetable")


@app.get("/timetable.ical", response_class=PlainTextResponse)
async def get_ical(
    weeks: int = Query(1, ge=1, le=6, description="Number of weeks to include (1-6)"),
    token: str = Depends(verify_token),
):
    """Get the CrossFit timetable as an iCal file."""
    try:
        today = date.today()
        current_monday = today - timedelta(days=today.weekday())
        mondays = [current_monday + timedelta(weeks=i) for i in range(weeks)]

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            location = await scraper.fetch_location(
                settings.scraper_base_url, session=session
            )
            week_tasks = [
                scraper.fetch_timetable(monday, session=session, location=location)
                for monday in mondays
            ]
            week_results = await asyncio.gather(*week_tasks)

        all_classes = [cls for week in week_results for cls in week]

        if not all_classes:
            raise HTTPException(status_code=404, detail="No classes found")

        # Generate iCal content
        ical_content = exporter.generate_ical_content(all_classes).decode("utf-8")

        return PlainTextResponse(
            content=ical_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": "attachment; filename=crossfit_timetable.ics"
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating iCal: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate iCal file")
