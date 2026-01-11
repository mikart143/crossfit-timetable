use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};
use thiserror::Error;
use tracing::error;

use crate::scraper::ScrapeError;

#[derive(Debug, Error)]
pub enum ApiError {
    #[error("Unauthorized: {0}")]
    Unauthorized(String),
    #[error("Bad request: {0}")]
    BadRequest(String),
    #[error("Not found: {0}")]
    NotFound(String),
    #[error("Internal error: {0}")]
    Internal(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let status = match self {
            ApiError::Unauthorized(_) => StatusCode::UNAUTHORIZED,
            ApiError::BadRequest(_) => StatusCode::BAD_REQUEST,
            ApiError::NotFound(_) => StatusCode::NOT_FOUND,
            ApiError::Internal(_) => StatusCode::INTERNAL_SERVER_ERROR,
        };
        (status, self.to_string()).into_response()
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
