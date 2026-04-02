"""
GVP Watch Backend - Webhook Handler Tests
-------------------------------------------
Tests for webhook payload parsing and validation.
"""

import pytest
from webhook_handler import WebhookHandler


class TestWebhookParsing:
    """Test webhook payload parsing"""

    def test_parse_text_message(self, webhook_handler, sample_text_message):
        """Test parsing a text message"""
        events = webhook_handler.parse_webhook(sample_text_message)

        assert len(events) == 1
        event = events[0]
        assert event["type"] == "incoming_message"
        assert event["message_type"] == "text"
        assert event["sender_phone"] == "919876543210"
        assert event["content"] == "Hi"

    def test_parse_location_message(self, webhook_handler, sample_location_message):
        """Test parsing a location message"""
        events = webhook_handler.parse_webhook(sample_location_message)

        assert len(events) == 1
        event = events[0]
        assert event["type"] == "incoming_message"
        assert event["message_type"] == "location"
        assert event["location"] == (17.3850, 78.4867)

    def test_parse_image_message(self, webhook_handler, sample_image_message):
        """Test parsing an image message"""
        events = webhook_handler.parse_webhook(sample_image_message)

        assert len(events) == 1
        event = events[0]
        assert event["type"] == "incoming_message"
        assert event["message_type"] == "image"
        assert event["media"]["type"] == "image"
        assert event["media"]["id"] == "media_id_123"

    def test_parse_button_message(self, webhook_handler, sample_button_message):
        """Test parsing an interactive button message"""
        events = webhook_handler.parse_webhook(sample_button_message)

        assert len(events) == 1
        event = events[0]
        assert event["type"] == "incoming_message"
        assert event["message_type"] == "interactive"
        assert event["button_reply"] == "confirmed"

    def test_webhook_safety_validation(self, webhook_handler):
        """Test webhook safety validation"""
        # Valid payload
        valid = {"object": "whatsapp_business_account", "entry": []}
        assert webhook_handler.validate_safety(valid)

        # Invalid object type
        invalid_obj = {"object": "invalid", "entry": []}
        assert not webhook_handler.validate_safety(invalid_obj)

        # Missing entry
        invalid_entry = {"object": "whatsapp_business_account"}
        assert not webhook_handler.validate_safety(invalid_entry)

        # Not a dict
        assert not webhook_handler.validate_safety("not a dict")

    def test_invalid_payload_handling(self, webhook_handler):
        """Test handling of invalid payloads"""
        # Missing required fields
        invalid = {
            "object": "whatsapp_business_account",
            "entry": [{"changes": [{"value": {"messages": [{}]}}]}]
        }

        # Should not crash, should return empty
        events = webhook_handler.parse_webhook(invalid)
        assert isinstance(events, list)

    def test_multiple_messages_in_payload(self, webhook_handler):
        """Test parsing multiple messages from one payload"""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "919876543210",
                                        "id": "msg1",
                                        "timestamp": "1680513234",
                                        "type": "text",
                                        "text": {"body": "Hi"}
                                    },
                                    {
                                        "from": "919876543210",
                                        "id": "msg2",
                                        "timestamp": "1680513240",
                                        "type": "location",
                                        "location": {"latitude": 17.3850, "longitude": 78.4867}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        events = webhook_handler.parse_webhook(payload)
        assert len(events) == 2
        assert events[0]["message_type"] == "text"
        assert events[1]["message_type"] == "location"


class TestPhoneNumberExtraction:
    """Test phone number extraction from payloads"""

    def test_valid_phone_number(self, webhook_handler, sample_text_message):
        """Test extraction of valid phone number"""
        events = webhook_handler.parse_webhook(sample_text_message)
        assert events[0]["sender_phone"] == "919876543210"

    def test_invalid_phone_number(self, webhook_handler):
        """Test handling of invalid phone number"""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "invalid",
                                        "id": "msg1",
                                        "timestamp": "1680513234",
                                        "type": "text",
                                        "text": {"body": "Hi"}
                                    }
                                ]
                            }
                        }
                    ]
                }
            ]
        }

        # Should not return this event (invalid phone)
        events = webhook_handler.parse_webhook(payload)
        assert len(events) == 0
