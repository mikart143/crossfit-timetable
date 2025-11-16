import logging
from datetime import date, timedelta
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from crossfit_timetable.scraper import CrossfitScraper, ClassItem
from crossfit_timetable.ical_exporter import ICalExporter
from crossfit_timetable.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CrossFit Timetable API",
    description="API for CrossFit 2 Rzeszów timetable data",
    version="1.0.0",
    openapi_url="/openapi.json" if settings.enable_swagger else None,
    docs_url="/docs" if settings.enable_swagger else None
)

scraper = CrossfitScraper()
exporter = ICalExporter()

# Security scheme
security = HTTPBearer(auto_error=False)  # Make it optional


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    token: Optional[str] = Query(None, description="API token (alternative to Authorization header)")
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
            "/ical": "Download timetable as iCal file"
        }
    }


@app.get("/timetable", response_model=List[ClassItem])
async def get_timetable(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD, must be a Monday)"),
    token: str = Depends(verify_token)
):
    """Get the CrossFit timetable data as JSON."""
    try:
        target_date = None
        if start_date:
            try:
                target_date = date.fromisoformat(start_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        classes = await scraper.fetch_timetable(target_date)
        return classes
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching timetable: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch timetable")


@app.get("/ical", response_class=PlainTextResponse)
async def get_ical(
    weeks: int = Query(1, ge=1, le=6, description="Number of weeks to include (1-6)"),
    token: str = Depends(verify_token)
):
    """Get the CrossFit timetable as an iCal file."""
    try:
        today = date.today()
        current_monday = today - timedelta(days=today.weekday())
        all_classes = []
        for i in range(weeks):
            target_monday = current_monday + timedelta(weeks=i)
            classes = await scraper.fetch_timetable(target_monday)
            all_classes.extend(classes)

        if not all_classes:
            raise HTTPException(status_code=404, detail="No classes found")

        # Generate iCal content
        ical_content = exporter.generate_ical_content(all_classes).decode('utf-8')

        return PlainTextResponse(
            content=ical_content,
            media_type="text/calendar",
            headers={
                "Content-Disposition": "attachment; filename=crossfit_timetable.ics"
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating iCal: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate iCal file")
