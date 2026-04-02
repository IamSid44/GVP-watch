"""
GVP Watch Backend - Utility Functions Tests
---------------------------------------------
Tests for helper functions and utilities.
"""

import pytest
from utils import (
    normalize_phone,
    is_valid_phone,
    analyze_image,
    extract_text_from_message,
    extract_location_from_message,
    extract_media_from_message,
    extract_button_reply_from_message,
    parse_meta_timestamp,
    time_since,
    should_send_first_reminder,
    should_auto_resolve
)
from datetime import datetime, timedelta


class TestPhoneNumberNormalization:
    """Test phone number parsing and normalization"""

    def test_normalize_with_country_code(self):
        """Test normalizing phone with country code"""
        assert normalize_phone("+919876543210") == "919876543210"
        assert normalize_phone("919876543210") == "919876543210"

    def test_normalize_with_spaces(self):
        """Test normalizing phone with spaces"""
        assert normalize_phone("+91 9876 543210") == "919876543210"
        assert normalize_phone("91-9876-543210") == "919876543210"

    def test_invalid_phone_raises_error(self):
        """Test that invalid phones raise ValueError"""
        with pytest.raises(ValueError):
            normalize_phone("abc123")  # Non-digits

        with pytest.raises(ValueError):
            normalize_phone("123")  # Too short

    def test_is_valid_phone(self):
        """Test phone validation without errors"""
        assert is_valid_phone("919876543210") is True
        assert is_valid_phone("+919876543210") is True
        assert is_valid_phone("invalid") is False


class TestImageAnalysis:
    """Test image analysis mock function"""

    def test_analyze_image_returns_severity(self):
        """Test that analyze_image returns valid severity"""
        result = analyze_image("test_image_id")
        assert result in ["LOW", "MEDIUM", "HIGH"]

    def test_same_image_same_severity(self):
        """Test that same image ID always returns same severity"""
        id = "consistent_test_id"
        result1 = analyze_image(id)
        result2 = analyze_image(id)
        assert result1 == result2

    def test_different_images_different_severity(self):
        """Test that different image IDs can return different severities"""
        # This is probabilistic but should work with enough IDs
        results = set()
        for i in range(20):
            result = analyze_image(f"test_image_{i}")
            results.add(result)

        # Should have at least 2 different severities
        assert len(results) >= 2


class TestMessageExtraction:
    """Test extracting data from message payloads"""

    def test_extract_text_from_text_message(self):
        """Test extracting text from text message"""
        message = {
            "type": "text",
            "text": {"body": "Hello World"}
        }
        assert extract_text_from_message(message) == "Hello World"

    def test_extract_text_missing(self):
        """Test handling missing text"""
        message = {"type": "text"}
        assert extract_text_from_message(message) is None

    def test_extract_location_from_message(self):
        """Test extracting location coordinates"""
        message = {
            "type": "location",
            "location": {
                "latitude": 17.3850,
                "longitude": 78.4867
            }
        }
        result = extract_location_from_message(message)
        assert result == (17.3850, 78.4867)

    def test_extract_invalid_location_coordinates(self):
        """Test handling invalid coordinates"""
        message = {
            "type": "location",
            "location": {
                "latitude": 200.0,  # Invalid
                "longitude": 78.4867
            }
        }
        assert extract_location_from_message(message) is None

    def test_extract_media_from_image_message(self):
        """Test extracting media from image message"""
        message = {
            "type": "image",
            "image": {
                "id": "media_123",
                "mime_type": "image/jpeg"
            }
        }
        result = extract_media_from_message(message)
        assert result is not None
        assert result["type"] == "image"
        assert result["id"] == "media_123"

    def test_extract_button_reply(self):
        """Test extracting button reply ID"""
        message = {
            "type": "interactive",
            "interactive": {
                "button_reply": {
                    "id": "confirmed",
                    "title": "Confirmed"
                }
            }
        }
        assert extract_button_reply_from_message(message) == "confirmed"


class TestTimestampParsing:
    """Test timestamp utilities"""

    def test_parse_meta_timestamp(self):
        """Test parsing Meta's Unix timestamp"""
        # 2024-04-02 14:30:45 UTC
        timestamp_str = "1712071845"
        result = parse_meta_timestamp(timestamp_str)
        assert isinstance(result, datetime)

    def test_time_since(self):
        """Test human-readable time differences"""
        now = datetime.utcnow()

        # 2 hours ago
        past = now - timedelta(hours=2)
        assert "hour" in time_since(past).lower()

        # 1 day ago
        past = now - timedelta(days=1)
        assert "day" in time_since(past).lower()

        # Just now
        past = now - timedelta(seconds=5)
        assert "now" in time_since(past).lower()


class TestReminderLogic:
    """Test reminder and auto-resolution logic"""

    def test_should_send_first_reminder_on_initial(self):
        """Test that first reminder should be sent if never sent"""
        assert should_send_first_reminder(None) is True

    def test_should_send_first_reminder_after_one_day(self):
        """Test reminder after 1 day"""
        past = datetime.utcnow() - timedelta(days=1, hours=1)
        assert should_send_first_reminder(past) is True

    def test_should_not_send_reminder_within_one_day(self):
        """Test no reminder within 1 day"""
        past = datetime.utcnow() - timedelta(hours=12)
        assert should_send_first_reminder(past) is False

    def test_should_auto_resolve_after_two_days(self):
        """Test auto-resolve after 2 days from reminder"""
        past = datetime.utcnow() - timedelta(days=1, hours=1)
        assert should_auto_resolve(past) is True

    def test_should_not_auto_resolve_within_2_days(self):
        """Test no auto-resolve within 2 days"""
        past = datetime.utcnow() - timedelta(hours=24)
        assert should_auto_resolve(past) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
