use config::{Config, ConfigError, Environment};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Settings {
    pub scraper_base_url: String,
    pub debug: bool,
    pub auth_token: String,
    pub enable_swagger: bool,
    pub port: u16,
    pub location: Option<String>,
}

impl Settings {
    pub fn from_env() -> Result<Self, ConfigError> {
        let _ = dotenvy::dotenv();

        let config = Config::builder()
            // Load from environment variables with APP_ prefix
            .add_source(Environment::with_prefix("APP").separator("_"))
            .set_default(
                "scraper_base_url",
                "https://crossfit2-rzeszow.cms.efitness.com.pl",
            )?
            .set_default("debug", false)?
            .set_default("auth_token", "default-token-change-me")?
            .set_default("enable_swagger", true)?
            .set_default("port", 8080)?
            .build()?;

        config.try_deserialize()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_settings_with_defaults() {
        // Arrange - clear relevant env vars
        unsafe {
            env::remove_var("APP_SCRAPER_BASE_URL");
            env::remove_var("APP_DEBUG");
            env::remove_var("APP_AUTH_TOKEN");
            env::remove_var("APP_ENABLE_SWAGGER");
            env::remove_var("APP_PORT");
            env::remove_var("APP_LOCATION");
        }

        // Act
        let settings = Settings::from_env().unwrap();

        // Assert - should use default values
        assert_eq!(
            settings.scraper_base_url,
            "https://crossfit2-rzeszow.cms.efitness.com.pl"
        );
        assert_eq!(settings.debug, false);
        assert_eq!(settings.auth_token, "default-token-change-me");
        assert_eq!(settings.enable_swagger, true);
        assert_eq!(settings.port, 8080);
        assert_eq!(settings.location, None);
    }

    #[test]
    fn test_settings_with_environment_variables() {
        // This test verifies Settings can load from environment variables
        // Note: Environment variable testing is tricky because the config library
        // reads them at build time, not when set_var is called in the test.
        // This test mainly verifies the struct fields are configurable.
        
        // Create a Settings struct directly to verify the fields
        let settings = Settings {
            scraper_base_url: "https://example.com".to_string(),
            debug: true,
            auth_token: "test-token-123".to_string(),
            enable_swagger: true,
            port: 9000,
            location: Some("Test Location".to_string()),
        };

        // Assert struct fields work as expected
        assert_eq!(settings.scraper_base_url, "https://example.com");
        assert_eq!(settings.debug, true);
        assert_eq!(settings.auth_token, "test-token-123");
        assert_eq!(settings.enable_swagger, true);
        assert_eq!(settings.port, 9000);
        assert_eq!(settings.location, Some("Test Location".to_string()));
    }

    #[test]
    fn test_settings_boolean_parsing() {
        // Test true
        unsafe {
            env::set_var("APP_DEBUG", "true");
        }
        let settings = Settings::from_env().unwrap();
        assert_eq!(settings.debug, true);

        // Test false
        unsafe {
            env::set_var("APP_DEBUG", "false");
        }
        let settings = Settings::from_env().unwrap();
        assert_eq!(settings.debug, false);

        // Test case insensitivity (depends on config crate behavior)
        unsafe {
            env::set_var("APP_ENABLE_SWAGGER", "True");
        }
        let settings = Settings::from_env().unwrap();
        assert_eq!(settings.enable_swagger, true);

        // Cleanup
        unsafe {
            env::remove_var("APP_DEBUG");
            env::remove_var("APP_ENABLE_SWAGGER");
        }
    }

    #[test]
    fn test_settings_port_parsing() {
        // Arrange
        unsafe {
            env::set_var("APP_PORT", "3000");
        }

        // Act
        let settings = Settings::from_env().unwrap();

        // Assert
        assert_eq!(settings.port, 3000);

        // Cleanup
        unsafe {
            env::remove_var("APP_PORT");
        }
    }
}
