use axum::{
    body::Body,
    http::{Request, StatusCode, header},
};
use crossfit_timetable::ical::ICalExporter;
use crossfit_timetable::scraper::CrossfitScraper;
use crossfit_timetable::settings::Settings;
use crossfit_timetable::{AppState, build_router};
use httpmock::prelude::*;
use std::sync::Arc;
use tower::Service;
use url::Url;

/// Helper function to create test app state with mocked server
fn create_test_state(mock_server_url: Url) -> AppState {
    let settings = Settings {
        scraper_base_url: mock_server_url.clone(),
        debug: true,
        auth_token: "test-token-123".to_string(),
        enable_swagger: true,
        port: 8080,
        location: Some("Test Location".to_string()),
        gym_latitude: 50.0386,
        gym_longitude: 22.0026,
        gym_title: "CrossFit 2.0 Rzeszów".to_string(),
        gym_location: "Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland".to_string(),
    };

    AppState {
        settings,
        scraper: Arc::new(CrossfitScraper::new(mock_server_url)),
        exporter: Arc::new(ICalExporter::new()),
    }
}

/// Helper to extract response body as string
async fn response_body_string(body: Body) -> String {
    let bytes = axum::body::to_bytes(body, usize::MAX).await.unwrap();
    String::from_utf8(bytes.to_vec()).unwrap()
}

#[tokio::test]
async fn test_root_endpoint() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act
    let response = app
        .call(Request::builder().uri("/").body(Body::empty()).unwrap())
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::OK);

    let body = response_body_string(response.into_body()).await;
    assert!(body.contains("CrossFit Timetable API"));
    assert!(body.contains("/timetable"));
    assert!(body.contains("/timetable.ical"));
}

#[tokio::test]
async fn test_healthz_ready() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/healthz/ready")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::OK);

    let body = response_body_string(response.into_body()).await;
    assert!(body.contains(r#""status":"ok"#));
}

#[tokio::test]
async fn test_healthz_live() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/healthz/live")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::OK);

    let body = response_body_string(response.into_body()).await;
    assert!(body.contains(r#""status":"ok"#));
}

#[tokio::test]
async fn test_timetable_no_auth_token() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert - should fail without token
    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_timetable_invalid_auth_token() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable?token=invalid-token")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_timetable_valid_auth_bearer() {
    // Arrange
    let mock_server = MockServer::start();
    let state = create_test_state(Url::parse(&mock_server.base_url()).unwrap());

    // Mock the scraper response with empty classes (will result in 404)
    mock_server.mock(|when, then| {
        when.method(GET).path_matches("kalendarz");
        then.status(200)
            .body(r#"<html><body><table class="calendar_table_agenda"></table></body></html>"#);
    });

    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable")
                .header(header::AUTHORIZATION, "Bearer test-token-123")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert - should fail with 404 since no classes found
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_timetable_valid_auth_query() {
    // Arrange
    let mock_server = MockServer::start();
    let state = create_test_state(Url::parse(&mock_server.base_url()).unwrap());

    // Mock the scraper response
    mock_server.mock(|when, then| {
        when.method(GET).path_matches("kalendarz");
        then.status(200)
            .body(r#"<html><body><table class="calendar_table_agenda"></table></body></html>"#);
    });

    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable?token=test-token-123")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert - should authenticate but fail with 404 since no classes
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_timetable_invalid_weeks_param() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act - weeks = 0 is invalid
    let response = app
        .call(
            Request::builder()
                .uri("/timetable?token=test-token-123&weeks=0")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_timetable_weeks_too_high() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act - weeks = 7 is invalid (max is 6)
    let response = app
        .call(
            Request::builder()
                .uri("/timetable?token=test-token-123&weeks=7")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::BAD_REQUEST);
}

#[tokio::test]
async fn test_timetable_with_single_class() {
    // Arrange
    let mock_server = MockServer::start();
    let state = create_test_state(Url::parse(&mock_server.base_url()).unwrap());

    // Get the current Monday
    use chrono::{Datelike, Duration as ChronoDuration, Local};
    let today = Local::now().date_naive();
    let monday = today - ChronoDuration::days(today.weekday().num_days_from_monday() as i64);

    // Mock response with a single class (using current Monday)
    let html_response = format!(
        r#"
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="1">Pn, {}</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Tomasz Nowosielski
                </td>
            </tr>
        </table>
        </body>
        </html>
    "#,
        monday.format("%Y-%m-%d")
    );

    mock_server.mock(|when, then| {
        when.method(GET).path_matches("kalendarz");
        then.status(200).body(html_response.as_str());
    });

    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable?token=test-token-123")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::OK);

    let body = response_body_string(response.into_body()).await;
    assert!(body.contains("WOD"));
    assert!(body.contains("Tomasz Nowosielski"));
}

#[tokio::test]
async fn test_timetable_with_multiple_classes() {
    // Arrange
    let mock_server = MockServer::start();
    let state = create_test_state(Url::parse(&mock_server.base_url()).unwrap());

    // Get the current Monday
    use chrono::{Datelike, Duration as ChronoDuration, Local};
    let today = Local::now().date_naive();
    let monday = today - ChronoDuration::days(today.weekday().num_days_from_monday() as i64);

    // Mock response with multiple classes
    let html_response = format!(
        r#"
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="2">Pn, {}</td>
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
    "#,
        monday.format("%Y-%m-%d")
    );

    mock_server.mock(|when, then| {
        when.method(GET).path_matches("kalendarz");
        then.status(200).body(html_response.as_str());
    });

    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable?token=test-token-123")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::OK);

    let body = response_body_string(response.into_body()).await;
    assert!(body.contains("WOD"));
    assert!(body.contains("HYROX"));
    assert!(body.contains("Tomasz Nowosielski"));
    assert!(body.contains("Jan Kowalski"));
}

#[tokio::test]
async fn test_ical_endpoint_no_auth() {
    // Arrange
    let state = create_test_state(Url::parse("http://example.com").unwrap());
    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable.ical")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::UNAUTHORIZED);
}

#[tokio::test]
async fn test_ical_endpoint_empty_classes() {
    // Arrange
    let mock_server = MockServer::start();
    let state = create_test_state(Url::parse(&mock_server.base_url()).unwrap());

    // Mock empty response
    mock_server.mock(|when, then| {
        when.method(GET).path_matches("kalendarz");
        then.status(200)
            .body(r#"<html><body><table class="calendar_table_agenda"></table></body></html>"#);
    });

    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable.ical?token=test-token-123")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert - should return 404 when no classes found
    assert_eq!(response.status(), StatusCode::NOT_FOUND);
}

#[tokio::test]
async fn test_ical_endpoint_with_classes() {
    // Arrange
    let mock_server = MockServer::start();
    let state = create_test_state(Url::parse(&mock_server.base_url()).unwrap());

    // Get the current Monday
    use chrono::{Datelike, Duration as ChronoDuration, Local};
    let today = Local::now().date_naive();
    let monday = today - ChronoDuration::days(today.weekday().num_days_from_monday() as i64);

    // Mock response with classes
    let html_response = format!(
        r#"
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="1">Pn, {}</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Coach Name
                </td>
            </tr>
        </table>
        </body>
        </html>
    "#,
        monday.format("%Y-%m-%d")
    );

    mock_server.mock(|when, then| {
        when.method(GET).path_matches("kalendarz");
        then.status(200).body(html_response.as_str());
    });

    let mut app = build_router(state);

    // Act
    let response = app
        .call(
            Request::builder()
                .uri("/timetable.ical?token=test-token-123")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::OK);

    // Check content type
    let content_type = response.headers().get(header::CONTENT_TYPE).unwrap();
    assert_eq!(content_type, "text/calendar");

    // Check content disposition
    let content_disposition = response.headers().get(header::CONTENT_DISPOSITION).unwrap();
    assert!(
        content_disposition
            .to_str()
            .unwrap()
            .contains("crossfit_timetable.ics")
    );

    // Check body contains iCal format
    let body = response_body_string(response.into_body()).await;
    assert!(body.contains("BEGIN:VCALENDAR"));
    assert!(body.contains("BEGIN:VEVENT"));
    assert!(body.contains("CrossFit: WOD"));
}

#[tokio::test]
async fn test_ical_endpoint_multiple_weeks() {
    // Arrange
    let mock_server = MockServer::start();
    let state = create_test_state(Url::parse(&mock_server.base_url()).unwrap());

    // Get the current Monday
    use chrono::{Datelike, Duration as ChronoDuration, Local};
    let today = Local::now().date_naive();
    let monday = today - ChronoDuration::days(today.weekday().num_days_from_monday() as i64);

    // Mock response with classes
    let html_response = format!(
        r#"
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="1">Pn, {}</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Coach
                </td>
            </tr>
        </table>
        </body>
        </html>
    "#,
        monday.format("%Y-%m-%d")
    );

    mock_server.mock(|when, then| {
        when.method(GET).path_matches("kalendarz");
        then.status(200).body(html_response.as_str());
    });

    let mut app = build_router(state);

    // Act - request 2 weeks
    let response = app
        .call(
            Request::builder()
                .uri("/timetable.ical?token=test-token-123&weeks=2")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    // Assert
    assert_eq!(response.status(), StatusCode::OK);

    let body = response_body_string(response.into_body()).await;
    assert!(body.contains("BEGIN:VCALENDAR"));
}
