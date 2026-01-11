use crate::settings::Settings;
use axum_extra::headers::Authorization;
use axum_extra::headers::authorization::Bearer;

use crate::error::ApiError;

pub fn verify_token(
    settings: &Settings,
    auth: Option<Authorization<Bearer>>,
    query_token: Option<&str>,
) -> Result<(), ApiError> {
    let provided_token = auth
        .map(|a| a.token().to_string())
        .or_else(|| query_token.map(|s| s.to_string()));
    match provided_token {
        Some(token) if token == settings.auth_token => Ok(()),
        _ => Err(ApiError::Unauthorized(
            "Invalid authentication token".into(),
        )),
    }
}

#[cfg(test)]
mod tests {
    use url::Url;

    use super::*;

    #[test]
    fn test_verify_token_header() {
        let settings = Settings {
            scraper_base_url: Url::parse("https://example.com").unwrap(),
            debug: false,
            auth_token: "secret".to_string(),
            enable_swagger: true,
            port: 8080,
            location: None,
            gym_latitude: 50.0386,
            gym_longitude: 22.0026,
            gym_title: "CrossFit 2.0 Rzeszów".to_string(),
            gym_location: "Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland".to_string(),
        };
        let auth = Authorization::bearer("secret").unwrap();
        assert!(verify_token(&settings, Some(auth), None).is_ok());
    }

    #[test]
    fn test_verify_token_query() {
        let settings = Settings {
            scraper_base_url: Url::parse("https://example.com").unwrap(),
            debug: false,
            auth_token: "secret".to_string(),
            enable_swagger: true,
            port: 8080,
            location: None,
            gym_latitude: 50.0386,
            gym_longitude: 22.0026,
            gym_title: "CrossFit 2.0 Rzeszów".to_string(),
            gym_location: "Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland".to_string(),
        };
        assert!(verify_token(&settings, None, Some("secret")).is_ok());
        assert!(verify_token(&settings, None, Some("bad")).is_err());
    }
}
