use crate::error::ApiError;

pub fn validate_weeks(value: u8) -> Result<u8, ApiError> {
    if (1..=6).contains(&value) {
        Ok(value)
    } else {
        Err(ApiError::BadRequest("weeks must be between 1 and 6".into()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_weeks() {
        assert!(validate_weeks(1).is_ok());
        assert!(validate_weeks(6).is_ok());
        assert!(validate_weeks(0).is_err());
        assert!(validate_weeks(7).is_err());
    }
}
