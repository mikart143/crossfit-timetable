use axum::{Json, extract::State, http::StatusCode, response::IntoResponse};
use axum_extra::extract::TypedHeader;
use axum_extra::headers::{Authorization, authorization::Bearer};
use chrono::{Datelike, Duration, Local, NaiveDate};
use futures::future::try_join_all;

use crate::{
    AppState, auth::verify_token, error::ApiError, models::ClassItem, validation::validate_weeks,
};

#[derive(Debug, serde::Deserialize)]
pub struct TimetableQuery {
    #[serde(default = "default_weeks")]
    pub weeks: u8,
    pub token: Option<String>,
}

fn default_weeks() -> u8 {
    1
}

#[utoipa::path(get, path = "/", tag = "timetable")]
pub async fn root() -> impl IntoResponse {
    Json(serde_json::json!({
        "message": "CrossFit Timetable API",
        "endpoints": {
            "/timetable": "Get timetable data as JSON",
            "/timetable.ical": "Download timetable as iCal file"
        }
    }))
}

#[utoipa::path(get, path = "/healthz/live", tag = "timetable")]
pub async fn healthz_live() -> impl IntoResponse {
    Json(serde_json::json!({"status": "ok"}))
}

#[utoipa::path(get, path = "/healthz/ready", tag = "timetable")]
pub async fn healthz_ready() -> impl IntoResponse {
    Json(serde_json::json!({"status": "ok"}))
}

#[utoipa::path(
    get,
    path = "/timetable",
    params(
        ("weeks" = u8, Query, description = "Number of weeks (1-6)"),
        ("token" = Option<String>, Query, description = "Authentication token (alternative to Bearer header)")
    ),
    responses(
        (status = 200, description = "List of classes", body = [ClassItem]),
        (status = 401, description = "Invalid authentication token"),
        (status = 404, description = "No classes found")
    ),
    security(("bearer_auth" = []), ("query_token" = [])), 
    tag = "timetable"
)]
pub async fn get_timetable(
    State(state): State<AppState>,
    auth: Option<TypedHeader<Authorization<Bearer>>>,
    axum::extract::Query(query): axum::extract::Query<TimetableQuery>,
) -> Result<impl IntoResponse, ApiError> {
    let auth_header = auth.map(|TypedHeader(a)| a);
    verify_token(&state.settings, auth_header, query.token.as_deref())?;

    let weeks = validate_weeks(query.weeks)?;

    let today = Local::now().date_naive();
    let current_monday = today - Duration::days(today.weekday().num_days_from_monday() as i64);
    let mondays: Vec<NaiveDate> = (0..weeks)
        .map(|i| current_monday + Duration::weeks(i.into()))
        .collect();

    let futures = mondays
        .into_iter()
        .map(|monday| state.scraper.fetch_timetable(Some(monday), None));

    let week_results: Vec<Vec<ClassItem>> = try_join_all(futures).await?;
    let classes: Vec<ClassItem> = week_results.into_iter().flatten().collect();

    if classes.is_empty() {
        return Err(ApiError::NotFound("No classes found".into()));
    }

    Ok(Json(classes))
}

#[utoipa::path(
    get,
    path = "/timetable.ical",
    params(
        ("weeks" = u8, Query, description = "Number of weeks (1-6)"),
        ("token" = Option<String>, Query, description = "Authentication token (alternative to Bearer header)")
    ),
    responses(
        (status = 200, description = "iCal file", content_type = "text/calendar"),
        (status = 401, description = "Invalid authentication token"),
        (status = 404, description = "No classes found")
    ),
    security(("bearer_auth" = []), ("query_token" = [])),
    tag = "timetable"
)]
pub async fn get_ical(
    State(state): State<AppState>,
    auth: Option<TypedHeader<Authorization<Bearer>>>,
    axum::extract::Query(query): axum::extract::Query<TimetableQuery>,
) -> Result<impl IntoResponse, ApiError> {
    let auth_header = auth.map(|TypedHeader(a)| a);
    verify_token(&state.settings, auth_header, query.token.as_deref())?;
    let weeks = validate_weeks(query.weeks)?;

    let today = Local::now().date_naive();
    let current_monday = today - Duration::days(today.weekday().num_days_from_monday() as i64);
    let mondays: Vec<NaiveDate> = (0..weeks)
        .map(|i| current_monday + Duration::weeks(i.into()))
        .collect();

    let location = match &state.settings.location {
        Some(loc) => Some(loc.clone()),
        None => state.scraper.fetch_location().await,
    };
    let futures = mondays.into_iter().map(|monday| {
        state
            .scraper
            .fetch_timetable(Some(monday), location.clone())
    });

    let week_results: Vec<Vec<ClassItem>> = try_join_all(futures).await?;
    let classes: Vec<ClassItem> = week_results.into_iter().flatten().collect();

    if classes.is_empty() {
        return Err(ApiError::NotFound("No classes found".into()));
    }

    let body = state.exporter.generate(&classes);
    Ok((
        StatusCode::OK,
        [
            ("content-type", "text/calendar"),
            (
                "content-disposition",
                "attachment; filename=crossfit_timetable.ics",
            ),
        ],
        body,
    ))
}
