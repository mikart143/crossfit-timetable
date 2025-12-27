use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use tracing::error;

use crate::scraper::ScrapeError;

#[derive(Debug)]
pub enum ApiError {
    Unauthorized(String),
    BadRequest(String),
    NotFound(String),
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        match self {
            ApiError::Unauthorized(msg) => (StatusCode::UNAUTHORIZED, msg).into_response(),
            ApiError::BadRequest(msg) => (StatusCode::BAD_REQUEST, msg).into_response(),
            ApiError::NotFound(msg) => (StatusCode::NOT_FOUND, msg).into_response(),
            ApiError::Internal(msg) => (StatusCode::INTERNAL_SERVER_ERROR, msg).into_response(),
        }
    }
}

impl From<ScrapeError> for ApiError {
    fn from(value: ScrapeError) -> Self {
        match value {
            ScrapeError::InvalidMonday | ScrapeError::TooOld => {
                ApiError::BadRequest(value.to_string())
            }
            ScrapeError::MissingTable => ApiError::Internal(value.to_string()),
            ScrapeError::Http(err) => {
                error!("HTTP error: {err}");
                ApiError::Internal("Failed to fetch timetable".into())
            }
        }
    }
}
