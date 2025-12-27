pub mod auth;
pub mod error;
pub mod handlers;
pub mod ical;
pub mod models;
pub mod openapi;
pub mod scraper;
pub mod settings;
pub mod validation;

use std::net::SocketAddr;
use std::sync::Arc;

use axum::{Router, routing::get};
use handlers::{get_ical, get_timetable, healthz_live, healthz_ready, root};
use tower_http::LatencyUnit;
use tower_http::trace::{DefaultMakeSpan, DefaultOnResponse, TraceLayer};
use tracing::{Level, info};
use utoipa::OpenApi;
use utoipa_swagger_ui::SwaggerUi;

use crate::ical::ICalExporter;
use crate::openapi::ApiDoc;
use crate::scraper::CrossfitScraper;
use crate::settings::Settings;

#[derive(Clone)]
pub struct AppState {
    pub(crate) settings: Settings,
    pub(crate) scraper: Arc<CrossfitScraper>,
    pub(crate) exporter: Arc<ICalExporter>,
}

pub async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let settings = Settings::from_env()?;

    let env_filter = if settings.debug { "debug" } else { "info" };
    tracing_subscriber::fmt()
        .with_env_filter(env_filter)
        .without_time()
        .init();

    let state = AppState {
        settings: settings.clone(),
        scraper: Arc::new(CrossfitScraper::new(settings.scraper_base_url.clone())),
        exporter: Arc::new(ICalExporter::new()),
    };

    let app = build_router(state.clone());

    let addr = SocketAddr::from(([0, 0, 0, 0], state.settings.port));
    info!("Starting CrossFit Timetable API on {addr}");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

pub(crate) fn build_router(state: AppState) -> Router {
    let trace_layer = TraceLayer::new_for_http()
        .make_span_with(DefaultMakeSpan::new().level(Level::INFO))
        .on_response(
            DefaultOnResponse::new()
                .level(Level::INFO)
                .latency_unit(LatencyUnit::Millis),
        );

    let mut router = Router::new()
        .route("/", get(root))
        .route("/healthz/live", get(healthz_live))
        .route("/healthz/ready", get(healthz_ready))
        .route("/timetable", get(get_timetable))
        .route("/timetable.ical", get(get_ical))
        .with_state(state.clone());

    if state.settings.enable_swagger {
        let openapi = ApiDoc::openapi();
        let swagger = SwaggerUi::new("/docs").url("/openapi.json", openapi);
        router = router.merge(swagger);
    }

    router.layer(trace_layer)
}

#[cfg(test)]
mod tests {}
