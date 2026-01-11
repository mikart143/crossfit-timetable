use std::sync::Arc;

use chrono::{Datelike, NaiveDate, NaiveDateTime, NaiveTime};
use url::Url;
use regex::Regex;
use scraper::{Html, Selector};
use thiserror::Error;

use crate::models::ClassItem;

#[derive(Debug, Error)]
pub enum ScrapeError {
    #[error("Date must be a Monday")]
    InvalidMonday,
    #[error("Date cannot be more than 2 weeks in the past")]
    TooOld,
    #[error("HTTP error: {0}")]
    Http(#[from] reqwest::Error),
    #[error("Table with class schedule not found on the page")]
    MissingTable,
}

#[derive(Clone)]
pub struct CrossfitScraper {
    client: reqwest::Client,
    base_url: Arc<Url>,
    date_regex: Regex,
}

impl CrossfitScraper {
    pub fn new(base_url: Url) -> Self {
        Self {
            client: reqwest::Client::new(),
            base_url: Arc::new(base_url),
            date_regex: Regex::new(r"\d{4}-\d{2}-\d{2}").expect("regex compiles"),
        }
    }

    pub fn get_valid_monday(target: Option<NaiveDate>) -> Result<NaiveDate, ScrapeError> {
        let today = chrono::Local::now().date_naive();
        let monday = today - chrono::Duration::days(today.weekday().num_days_from_monday() as i64);

        if let Some(given) = target {
            if given.weekday().num_days_from_monday() != 0 {
                return Err(ScrapeError::InvalidMonday);
            }
            let two_weeks_ago = today - chrono::Duration::days(14);
            if given < two_weeks_ago {
                return Err(ScrapeError::TooOld);
            }
            Ok(given)
        } else {
            Ok(monday)
        }
    }

    fn parse_time_range(&self, time_range: &str) -> Option<u32> {
        let parts: Vec<&str> = time_range.split('-').collect();
        if parts.len() != 2 {
            return None;
        }
        let (start, end) = (parts[0].trim(), parts[1].trim());
        let start_parts: Vec<&str> = start.split(':').collect();
        let end_parts: Vec<&str> = end.split(':').collect();
        if start_parts.len() != 2 || end_parts.len() != 2 {
            return None;
        }
        let start_hour = start_parts[0].parse::<i32>().ok()?;
        let start_min = start_parts[1].parse::<i32>().ok()?;
        let end_hour = end_parts[0].parse::<i32>().ok()?;
        let end_min = end_parts[1].parse::<i32>().ok()?;

        let start_total = start_hour * 60 + start_min;
        let end_total = end_hour * 60 + end_min;
        (end_total - start_total).try_into().ok()
    }

    fn parse_agenda_date(&self, text: &str) -> Option<NaiveDate> {
        let caps = self.date_regex.find(text)?;
        NaiveDate::parse_from_str(caps.as_str(), "%Y-%m-%d").ok()
    }

    async fn fetch_html(&self, url: &Url) -> Result<String, ScrapeError> {
        let response = self.client.get(url.as_str()).send().await?.error_for_status()?;
        let body = response.text().await?;
        Ok(body)
    }

    fn resolve_location(&self, html: &str) -> Option<String> {
        let document = Html::parse_document(html);
        let address_sel = Selector::parse("address").ok()?;
        let p_sel = Selector::parse("p").ok()?;
        let address = document.select(&address_sel).next()?;

        let mut lines = vec![];
        for p in address.select(&p_sel) {
            let text = p.text().collect::<Vec<_>>().join("").trim().to_string();
            if text.is_empty() || text == "Kontakt" {
                continue;
            }
            if text == "CrossFit Rzeszów 2.0" {
                continue;
            }
            lines.push(text);
        }

        if lines.is_empty() {
            return None;
        }
        let mut address = lines.join(", ");
        if !address.contains("Poland") {
            address.push_str(", Poland");
        }
        Some(address)
    }

    pub async fn fetch_location(&self) -> Option<String> {
        let html = self
            .fetch_html(&self.base_url)
            .await
            .map_err(|err| tracing::warn!(error = %err, "failed to fetch location"))
            .ok()?;
        self.resolve_location(&html)
    }

    pub async fn fetch_timetable(
        &self,
        start_date: Option<NaiveDate>,
        location: Option<String>,
    ) -> Result<Vec<ClassItem>, ScrapeError> {
        let monday = Self::get_valid_monday(start_date)?;

        let url = Url::parse_with_params(
            &format!("{}/kalendarz-zajec", self.base_url),
            &[("day", monday.to_string()), ("view", "Agenda".to_string())],
        ).unwrap();

        let html = self.fetch_html(&url).await?;
        let loc = match location {
            Some(loc) => Some(loc),
            None => self.fetch_location().await,
        };
        self.parse_timetable_html(&html, monday, loc, &url)
    }

    pub fn parse_timetable_html(
        &self,
        html: &str,
        expected_monday: NaiveDate,
        location: Option<String>,
        source_url: &Url,
    ) -> Result<Vec<ClassItem>, ScrapeError> {
        let document = Html::parse_document(html);
        let table_sel = Selector::parse("table.calendar_table_agenda").unwrap();
        let row_sel = Selector::parse("tr").unwrap();
        let cell_sel = Selector::parse("td").unwrap();
        let event_sel = Selector::parse("p.event_name").unwrap();
        let link_sel = Selector::parse("a.schedule-agenda-link").unwrap();

        let table = document
            .select(&table_sel)
            .next()
            .ok_or(ScrapeError::MissingTable)?;

        let mut current_date: Option<NaiveDate> = None;
        let mut records: Vec<ClassItem> = Vec::new();

        for row in table.select(&row_sel) {
            let cells: Vec<_> = row.select(&cell_sel).collect();
            if cells.is_empty() {
                continue;
            }

            let (time_cell, content_cell) = if cells[0].value().attr("rowspan").is_some() {
                let date_text = cells[0]
                    .text()
                    .collect::<Vec<_>>()
                    .join("")
                    .trim()
                    .to_string();
                current_date = self.parse_agenda_date(&date_text);
                if current_date.is_none() {
                    continue;
                }
                if let Some(date_val) = current_date
                    && (date_val < expected_monday
                        || date_val > expected_monday + chrono::Duration::days(6))
                {
                    continue;
                }
                (cells.get(1), cells.get(2))
            } else {
                (cells.first(), cells.get(1))
            };

            let (Some(time_cell), Some(content_cell)) = (time_cell, content_cell) else {
                continue;
            };

            let time_range = time_cell
                .text()
                .collect::<Vec<_>>()
                .join("")
                .trim()
                .to_string();
            let duration_min = self.parse_time_range(&time_range);

            let start_time_str = time_range.split('-').next().unwrap_or("").trim();
            let time_parts: Vec<&str> = start_time_str.split(':').collect();
            if time_parts.len() != 2 {
                continue;
            }
            let hour = time_parts[0].parse::<u32>().ok();
            let minute = time_parts[1].parse::<u32>().ok();
            let Some(date_base) = current_date else {
                continue;
            };
            let start_dt = match (hour, minute) {
                (Some(h), Some(m)) => {
                    let Some(time) = NaiveTime::from_hms_opt(h, m, 0) else {
                        continue;
                    };
                    NaiveDateTime::new(date_base, time)
                }
                _ => continue,
            };

            let event_elem = content_cell.select(&event_sel).next();
            let Some(event_elem) = event_elem else {
                continue;
            };
            let event_name = event_elem
                .text()
                .collect::<Vec<_>>()
                .join("")
                .trim()
                .to_string();
            if event_name.is_empty() {
                continue;
            }

            let mut coach = String::new();
            for text in content_cell
                .text()
                .map(|t| t.trim())
                .filter(|t| !t.is_empty())
            {
                if text == event_name {
                    continue;
                }
                coach = text.to_string();
                break;
            }

            let source_url = content_cell
                .select(&link_sel)
                .next()
                .and_then(|a| a.value().attr("href"))
                .map(|href| format!("{}{}", self.base_url, href))
                .unwrap_or_else(|| source_url.to_string());

            records.push(ClassItem {
                date: start_dt,
                event_name: event_name.clone(),
                coach,
                duration_min,
                source_url,
                location: location.clone(),
            });
        }

        records.sort_by(|a, b| {
            a.date
                .cmp(&b.date)
                .then(a.event_name.cmp(&b.event_name))
                .then(a.coach.cmp(&b.coach))
        });
        Ok(records)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_valid_monday_valid() {
        let today = chrono::Local::now().date_naive();
        let monday = today - chrono::Duration::days(today.weekday().num_days_from_monday() as i64);
        assert_eq!(
            CrossfitScraper::get_valid_monday(Some(monday)).unwrap(),
            monday
        );
    }

    #[test]
    fn test_get_valid_monday_not_monday() {
        let tuesday = NaiveDate::from_ymd_opt(2025, 11, 11).unwrap();
        let err = CrossfitScraper::get_valid_monday(Some(tuesday)).unwrap_err();
        assert!(matches!(err, ScrapeError::InvalidMonday));
    }

    #[test]
    fn test_parse_time_range() {
        let scraper = CrossfitScraper::new(Url::parse("https://example.com").unwrap());
        assert_eq!(scraper.parse_time_range("06:00 - 07:00"), Some(60));
        assert_eq!(scraper.parse_time_range("18:00-19:30"), Some(90));
        assert_eq!(scraper.parse_time_range("invalid"), None);
    }

    #[test]
    fn test_parse_agenda_date() {
        let scraper = CrossfitScraper::new(Url::parse("https://example.com").unwrap());
        let parsed = scraper.parse_agenda_date("Pn, 2025-11-24");
        assert_eq!(parsed, Some(NaiveDate::from_ymd_opt(2025, 11, 24).unwrap()));
        assert!(scraper.parse_agenda_date("no date").is_none());
    }

    #[test]
    fn test_parse_timetable_html() {
        let scraper = CrossfitScraper::new(Url::parse("https://example.com").unwrap());
        let html = r#"
        <html>
        <body>
        <table class="calendar_table_agenda">
            <tr>
                <td rowspan="2">Pn, 2025-12-15</td>
                <td>06:00 - 07:00</td>
                <td>
                    <p class="event_name">WOD</p>
                    Tomasz Nowosielski
                </td>
            </tr>
            <tr>
                <td>07:00 - 08:00</td>
                <td>
                    <p class="event_name">HYROX</p>
                    Jan Kowalski
                </td>
            </tr>
        </table>
        </body>
        </html>
        "#;
        let monday = NaiveDate::from_ymd_opt(2025, 12, 15).unwrap();
        let result = scraper
            .parse_timetable_html(html, monday, None, &Url::parse("https://example.com/kalendarz").unwrap())
            .unwrap();
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].event_name, "WOD");
        assert_eq!(result[1].event_name, "HYROX");
    }
}
