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
