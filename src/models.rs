use chrono::NaiveDateTime;
use serde::{Deserialize, Serialize};
use utoipa::ToSchema;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, ToSchema)]
pub struct ClassItem {
    #[schema(value_type = String, format = "date-time", example = "2025-11-24T06:00:00")]
    pub date: NaiveDateTime,
    pub event_name: String,
    pub coach: String,
    pub duration_min: Option<u32>,
    pub source_url: String,
    pub location: Option<String>,
}
