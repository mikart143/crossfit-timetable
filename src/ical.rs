use chrono::Duration;
use icalendar::{Calendar, Component, Event, EventLike, Property};

use crate::models::ClassItem;
use crate::settings::Settings;

#[derive(Clone, Default)]
pub struct ICalExporter;

impl ICalExporter {
    pub fn new() -> Self {
        Self
    }

    fn create_structured_location(
        location: &str,
        gym_latitude: f64,
        gym_longitude: f64,
        gym_title: &str,
    ) -> Property {
        // Format address for X-ADDRESS parameter (use \n for line breaks)
        let address_formatted = location.replace(", ", "\\n");

        // Build the geo URI with coordinates
        let geo_uri = format!("geo:{},{}", gym_latitude, gym_longitude);

        // Create X-APPLE-STRUCTURED-LOCATION property
        // This is an Apple-specific extension (not part of RFC 5545)
        // Enables map integration, travel time alerts, and location-based features
        let mut property = Property::new("X-APPLE-STRUCTURED-LOCATION", &geo_uri);
        property.add_parameter("VALUE", "URI");
        property.add_parameter("X-ADDRESS", &address_formatted);
        property.add_parameter("X-TITLE", gym_title);
        property.add_parameter("X-APPLE-RADIUS", "49.91"); // ~50 meters radius

        property
    }

    pub fn generate(&self, classes: &[ClassItem], settings: &Settings) -> Vec<u8> {
        if classes.is_empty() {
            return Vec::new();
        }

        let mut calendar = Calendar::new();
        calendar.name("CrossFit 2.0 Rzeszów Timetable");

        for item in classes {
            let start = item.date;
            let end_dt = if let Some(duration) = item.duration_min {
                item.date + Duration::minutes(duration as i64)
            } else {
                item.date + Duration::hours(1)
            };

            let mut event = Event::new();
            event.summary(&format!("CrossFit: {}", item.event_name));
            event.starts(start);
            event.ends(end_dt);
            let location = item
                .location
                .clone()
                .unwrap_or_else(|| settings.gym_location.clone());
            event.location(&location);
            event.description(&format!(
                "CrossFit Class\nCoach: {}\nSource: {}",
                item.coach, item.source_url
            ));
            event.uid(&format!(
                "{}-{}-{}-crossfit-timetable",
                item.date.format("%Y%m%dT%H%M%S"),
                item.event_name.replace(' ', "-"),
                item.coach.replace(' ', "-")
            ));

            // Add X-APPLE-STRUCTURED-LOCATION for enhanced Apple Calendar support
            let structured_location = Self::create_structured_location(
                &location,
                settings.gym_latitude,
                settings.gym_longitude,
                &settings.gym_title,
            );
            event.append_property(structured_location);

            calendar.push(event);
        }

        calendar.to_string().into_bytes()
    }
}

#[cfg(test)]
mod tests {
    use chrono::NaiveDateTime;

    use super::*;

    fn create_test_settings() -> Settings {
        Settings {
            scraper_base_url: "https://example.com".to_string(),
            debug: false,
            auth_token: "test".to_string(),
            enable_swagger: true,
            port: 8080,
            location: None,
            gym_latitude: 50.0386,
            gym_longitude: 22.0026,
            gym_title: "CrossFit 2.0 Rzeszów".to_string(),
            gym_location: "Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland".to_string(),
        }
    }

    #[test]
    fn test_generate_single_class() {
        let exporter = ICalExporter::new();
        let settings = create_test_settings();
        let class = ClassItem {
            date: NaiveDateTime::parse_from_str("2025-11-24 06:00:00", "%Y-%m-%d %H:%M:%S")
                .unwrap(),
            event_name: "WOD".to_string(),
            coach: "Coach".to_string(),
            duration_min: Some(60),
            source_url: "https://example.com".to_string(),
            location: None,
        };
        let bytes = exporter.generate(&[class], &settings);
        let body = String::from_utf8(bytes).unwrap();
        assert!(body.contains("BEGIN:VEVENT"));
        assert!(body.contains("CrossFit: WOD"));
    }

    #[test]
    fn test_generate_empty() {
        let exporter = ICalExporter::new();
        let settings = create_test_settings();
        let bytes = exporter.generate(&[], &settings);
        assert!(bytes.is_empty());
    }

    #[test]
    fn test_x_apple_structured_location() {
        let exporter = ICalExporter::new();
        let settings = create_test_settings();
        let class = ClassItem {
            date: NaiveDateTime::parse_from_str("2025-11-24 06:00:00", "%Y-%m-%d %H:%M:%S")
                .unwrap(),
            event_name: "WOD".to_string(),
            coach: "Coach".to_string(),
            duration_min: Some(60),
            source_url: "https://example.com".to_string(),
            location: Some("Boya-Żeleńskiego 15, 35-105 Rzeszów, Poland".to_string()),
        };
        let bytes = exporter.generate(&[class], &settings);
        let body = String::from_utf8(bytes).unwrap();

        // Remove RFC 5545 line folding (lines starting with space are continuations)
        let normalized = body.replace("\r\n ", "").replace("\n ", "");

        // Check that X-APPLE-STRUCTURED-LOCATION is present
        assert!(normalized.contains("X-APPLE-STRUCTURED-LOCATION"));
        // Check that it contains geo URI with coordinates
        assert!(normalized.contains("geo:50.0386,22.0026"));
        // Check that it has the VALUE=URI parameter
        assert!(normalized.contains("VALUE=URI"));
        // Check that X-TITLE parameter is present
        assert!(normalized.contains("X-TITLE=CrossFit 2.0 Rzeszów"));
        // Check that X-APPLE-RADIUS is present
        assert!(normalized.contains("X-APPLE-RADIUS=49.91"));
        // Check that X-ADDRESS is present with proper formatting
        assert!(normalized.contains("X-ADDRESS="));
    }
}
