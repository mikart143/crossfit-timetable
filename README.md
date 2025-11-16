# CrossFit Timetable API

A FastAPI-based web service for extracting CrossFit class timetables from the CrossFit 2 Rzeszów website.

## Features

- **REST API**: FastAPI-based web service with automatic OpenAPI documentation
- **Authentication**: Simple token-based authentication for API access
- **Parametrized Date Selection**: Fetch timetables for specific weeks by providing a Monday date
- **Date Validation**: Ensures dates are Mondays and not more than 2 weeks in the past
- **Multiple Output Formats**: JSON data and iCal calendar export
- **Pydantic Models**: Type-safe data models with validation
- **Comprehensive Testing**: Full unit test coverage

## Installation

This project uses [uv](https://github.com/astral-sh/uv) for dependency management.

```bash
# Clone the repository
git clone <repository-url>
cd crossfit-timetable

# Install dependencies
uv sync

# Install development dependencies (including pytest)
uv sync --group dev
```

## Configuration

The application uses environment variables for configuration with the `APP_` prefix.

### Environment Variables

- `APP_BASE_URL`: Base URL for the CrossFit website (default: "https://crossfit2-rzeszow.cms.efitness.com.pl")
- `APP_DEBUG`: Enable debug mode (default: false)
- `APP_AUTH_TOKEN`: Authentication token required for API access (default: "default-token-change-me")

### Setting Environment Variables

```bash
# Set authentication token
export APP_AUTH_TOKEN="your-secure-token-here"

# Start the server
uv run server
```

### API Endpoints

#### GET `/`
Returns basic API information. (No authentication required)

**Response:**
```json
{
  "message": "CrossFit Timetable API",
  "endpoints": {
    "/timetable": "Get timetable data as JSON",
    "/ical": "Download timetable as iCal file"
  }
}
```

#### GET `/timetable`
Returns the CrossFit timetable data as JSON. (Authentication required)

**Authentication Options:**
- Header: `Authorization: Bearer <your-token>`
- Query parameter: `?token=<your-token>`

**Query Parameters:**
- `start_date` (optional): Start date in YYYY-MM-DD format (must be a Monday)
- `token` (optional): API token (alternative to Authorization header)

**Response:**
```json
[
  {
    "date": "2025-11-13T06:00:00",
    "event_name": "WOD",
    "coach": "John Doe",
    "duration_min": 60,
    "source_url": "https://crossfit2-rzeszow.cms.efitness.com.pl/kalendarz-zajec?day=2025-11-11&view=Agenda"
  }
]
```

#### GET `/ical`
Returns the CrossFit timetable as an iCal file for calendar import. (Authentication required)

**Authentication Options:**
- Header: `Authorization: Bearer <your-token>`
- Query parameter: `?token=<your-token>`

**Query Parameters:**
- `start_date` (optional): Start date in YYYY-MM-DD format (must be a Monday)
- `token` (optional): API token (alternative to Authorization header)

**Response:** iCal (.ics) file download

### Examples

```bash
# Get current week's timetable as JSON (using Bearer token)
curl -H "Authorization: Bearer your-token-here" http://localhost:8000/timetable

# Get current week's timetable as JSON (using query parameter)
curl "http://localhost:8000/timetable?token=your-token-here"

# Get specific week's timetable (Bearer token)
curl -H "Authorization: Bearer your-token-here" "http://localhost:8000/timetable?start_date=2025-11-11"

# Get specific week's timetable (query parameter)
curl "http://localhost:8000/timetable?start_date=2025-11-11&token=your-token-here"

# Download iCal file (Bearer token)
curl -H "Authorization: Bearer your-token-here" -o crossfit.ics http://localhost:8000/ical

# Download iCal file (query parameter)
curl -o crossfit.ics "http://localhost:8000/ical?token=your-token-here"

# Download specific week's iCal (query parameter)
curl -o crossfit.ics "http://localhost:8000/ical?start_date=2025-11-11&token=your-token-here"
```

## API Documentation

When the server is running, visit `http://localhost:8000/docs` for interactive API documentation powered by Swagger UI, or `http://localhost:8000/redoc` for ReDoc documentation.

## Testing

The project includes comprehensive unit tests covering all functionality.

### Running Tests

```bash
# Using pytest directly
uv run pytest

# Run specific test file
uv run pytest tests/test_scraper.py

# Run with verbose output
uv run pytest -v
```

### Test Coverage

- Date validation logic
- Text parsing functions
- HTML table extraction
- Time slot parsing
- API endpoint responses
- Pydantic model validation

## Development

### Project Structure

```
crossfit-timetable/
├── src/
│   └── crossfit_timetable/
│       ├── __init__.py
│       ├── scraper.py          # Main scraper implementation
│       ├── ical_exporter.py    # iCal export functionality
│       └── main.py            # FastAPI application
├── tests/
│   ├── test_scraper.py         # Scraper unit tests
│   └── test_ical_exporter.py   # iCal export tests
├── pyproject.toml     # Project configuration
├── uv.lock           # Dependency lock file
└── README.md         # This file
```

### Dependencies

- **Runtime**: aiohttp, beautifulsoup4, lxml, pydantic, python-dateutil, fastapi, uvicorn, icalendar
- **Development**: pytest

## License

[Add your license here]
