# CrossFit Timetable API (Rust)

Rust reimplementation of the CrossFit timetable service. It scrapes the CrossFit 2 Rzeszów agenda view, exposes it over HTTP via Axum, and can export results to JSON or iCal.

## Features
- **Axum-based REST API** with health and info endpoints
- **Token authentication** via `Authorization: Bearer <token>` header or `?token=<token>` query parameter
- **Week selection** (`weeks=1-6`, default=1) starting from the current week (Mondays only)
- **HTML scraping** with `reqwest` + `scraper` for agenda data and location extraction
- **iCal export** built with `icalendar` crate (timezone: Europe/Warsaw)
- **OpenAPI/Swagger UI** documentation (enabled by default at `/docs`)
- **Comprehensive test suite** covering parsing, authentication, and iCal generation

## Prerequisites
- Rust toolchain (https://rustup.rs)

## Running

### Quick Start
```bash
# Install dependencies and run with defaults
cargo run
```

### With Custom Configuration
```bash
# Custom authentication token, base URL, and port
APP_AUTH_TOKEN=my-secret-token \
APP_SCRAPER_BASE_URL=https://example.com/api \
APP_PORT=3000 \
cargo run
```

### Running Tests
```bash
# Run all tests
cargo test

# Run with output
cargo test -- --nocapture
```

## Configuration (environment variables)
- `APP_SCRAPER_BASE_URL` — Base URL for the CrossFit 2 agenda (default: `https://crossfit2-rzeszow.cms.efitness.com.pl`)
- `APP_AUTH_TOKEN` — Token for API authentication (default: `default-token-change-me`)
- `APP_PORT` — HTTP server port (default: `8080`)
- `APP_DEBUG` — Enable debug logging (default: `false`)
- `APP_ENABLE_SWAGGER` — Enable OpenAPI/Swagger UI at `/docs` (default: `true`)
- `APP_LOCATION` — Optional location string (if not set, fetched from the scraper for JSON endpoint; used for iCal if provided)

## API

All authenticated routes accept either `Authorization: Bearer <token>` header or `?token=<token>` query parameter.

### Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | No | API info and available endpoints |
| `GET` | `/healthz/live` | No | Liveness probe (always returns 200) |
| `GET` | `/healthz/ready` | No | Readiness probe (always returns 200) |
| `GET` | `/timetable?weeks=N` | **Yes** | JSON list of classes for next N weeks (1-6) |
| `GET` | `/timetable.ical?weeks=N` | **Yes** | iCal file for next N weeks (1-6) |
| `GET` | `/docs` | No | OpenAPI/Swagger interactive documentation |
| `GET` | `/openapi.json` | No | OpenAPI spec (JSON) |

### Query Parameters
- `weeks` (integer, 1-6, default=1) — Number of weeks of classes to fetch starting from the current Monday
- `token` (string, optional) — Authentication token (alternative to Bearer header)

### Response Formats

**JSON Response** (`/timetable`):
```json
[
  {
    "date": "2025-01-27T06:00:00",
    "event_name": "WOD",
    "coach": "Coach Name",
    "duration_min": 60,
    "source_url": "https://crossfit2-rzeszow.cms.efitness.com.pl/...",
    "location": "CrossFit 2 Rzeszów"
  }
]
```

**iCal Response** (`/timetable.ical`):
- Content-Type: `text/calendar`
- Content-Disposition: `attachment; filename=crossfit_timetable.ics`
- Events default to 1 hour duration if not specified
- Timezone: Europe/Warsaw

## Notes
- Date validation: Only Mondays are supported; no data older than 2 weeks (14 days) in the past is fetched
- iCal events default to 1 hour duration if unavailable from the source
- Timezone for iCal generation: Europe/Warsaw
- The location is fetched from the scraper on each JSON request; for iCal, uses `APP_LOCATION` if set, otherwise fetches from scraper
- All times are in the scheduler's configured timezone

## License
MIT
