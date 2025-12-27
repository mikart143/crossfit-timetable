use utoipa::openapi::security::{ApiKey, ApiKeyValue, HttpAuthScheme, HttpBuilder, SecurityScheme};
use utoipa::{Modify, OpenApi};

use crate::models::ClassItem;

pub struct SecurityAddon;

impl Modify for SecurityAddon {
    fn modify(&self, openapi: &mut utoipa::openapi::OpenApi) {
        let components = openapi.components.as_mut().unwrap();
        components.add_security_scheme(
            "bearer_auth",
            SecurityScheme::Http(
                HttpBuilder::new()
                    .scheme(HttpAuthScheme::Bearer)
                    .bearer_format("JWT")
                    .build(),
            ),
        );
        components.add_security_scheme(
            "query_token",
            SecurityScheme::ApiKey(ApiKey::Query(ApiKeyValue::new("token"))),
        );
    }
}

#[derive(OpenApi)]
#[openapi(
    paths(
        crate::handlers::root,
        crate::handlers::healthz_live,
        crate::handlers::healthz_ready,
        crate::handlers::get_timetable,
        crate::handlers::get_ical
    ),
    components(schemas(ClassItem)),
    tags(
        (name = "timetable", description = "CrossFit timetable operations")
    ),
    modifiers(&SecurityAddon),
)]
pub struct ApiDoc;
