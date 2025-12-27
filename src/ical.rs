use chrono::Duration;
use icalendar::{Calendar, Component, Event, EventLike};

use crate::models::ClassItem;

#[derive(Clone, Default)]
pub struct ICalExporter;

impl ICalExporter {
    pub fn new() -> Self {
        Self
    }

    pub fn generate(&self, classes: &[ClassItem]) -> Vec<u8> {
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
                .unwrap_or_else(|| "CrossFit 2.0 Rzeszów".to_string());
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
            calendar.push(event);
        }

        calendar.to_string().into_bytes()
    }
}

#[cfg(test)]
mod tests {
    use chrono::NaiveDateTime;

    use super::*;

    #[test]
    fn test_generate_single_class() {
        let exporter = ICalExporter::new();
        let class = ClassItem {
            date: NaiveDateTime::parse_from_str("2025-11-24 06:00:00", "%Y-%m-%d %H:%M:%S")
                .unwrap(),
            event_name: "WOD".to_string(),
            coach: "Coach".to_string(),
            duration_min: Some(60),
            source_url: "https://example.com".to_string(),
            location: None,
        };
        let bytes = exporter.generate(&[class]);
        let body = String::from_utf8(bytes).unwrap();
        assert!(body.contains("BEGIN:VEVENT"));
        assert!(body.contains("CrossFit: WOD"));
    }

    #[test]
    fn test_generate_empty() {
        let exporter = ICalExporter::new();
        let bytes = exporter.generate(&[]);
        assert!(bytes.is_empty());
    }
}
