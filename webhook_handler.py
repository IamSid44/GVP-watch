"""
GVP Watch Backend - Webhook Handler
------------------------------------
Parses incoming webhook payloads from Meta WhatsApp Cloud API.

This module handles:
1. Extracting message content (text, location, images, buttons)
2. Identifying message type and sender
3. Routing to appropriate business logic (ticket_service.py)

Key challenge: Meta's JSON payloads are deeply nested and optional fields
vary based on message type. This module carefully extracts required data
and validates before passing to business logic.

Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/webhook-reference
"""

from typing import Optional, Dict, Any, Tuple
from datetime import datetime
import json

from logger_config import get_logger, log_with_context, log_ticket_action
from models import WebhookPayload, MessageContent
from utils import (
    extract_text_from_message,
    extract_location_from_message,
    extract_media_from_message,
    extract_button_reply_from_message,
    parse_meta_timestamp,
    normalize_phone
)

logger = get_logger(__name__)


class WebhookHandler:
    """
    Handles parsing and validation of incoming webhook payloads from Meta.

    Usage:
        handler = WebhookHandler()
        events = handler.parse_webhook(payload_dict)
        for event in events:
            if event['type'] == 'incoming_message':
                # Process incoming message
                process_message(event)
    """

    # Message types we care about
    SUPPORTED_MESSAGE_TYPES = ["text", "location", "image", "interactive"]

    def __init__(self):
        """Initialize webhook handler"""
        pass

    def parse_webhook(self, payload: Dict[str, Any]) -> list:
        """
        Parse complete webhook payload from Meta.

        Extracts messages and status updates, validates, and returns
        a list of events for the application to process.

        Args:
            payload: Raw webhook payload dict from Meta

        Returns:
            List of event dicts, each with:
            {
                'type': 'incoming_message' | 'delivery_status' | 'read_status' | 'unknown',
                'message': { ... }  # if incoming_message
                'status': { ... }   # if delivery/read status
            }

        Raises:
            ValueError: If payload structure is invalid
        """
        events = []

        try:
            # Validate basic structure
            if not isinstance(payload, dict):
                raise ValueError("Payload must be a dictionary")

            if payload.get("object") != "whatsapp_business_account":
                logger.warning(f"Unexpected webhook object type: {payload.get('object')}")
                return events

            # Extract entries (array of changes)
            entries = payload.get("entry", [])

            for entry in entries:
                if not isinstance(entry, dict):
                    logger.warning(f"Skipping invalid entry: {entry}")
                    continue

                changes = entry.get("changes", [])

                for change in changes:
                    if not isinstance(change, dict):
                        logger.warning(f"Skipping invalid change: {change}")
                        continue

                    # Parse the change value (contains messages and statuses)
                    value = change.get("value", {})

                    # ============================================================
                    # EXTRACT MESSAGES
                    # ============================================================
                    messages = value.get("messages", [])
                    for msg in messages:
                        try:
                            event = self._parse_incoming_message(msg)
                            if event:
                                events.append(event)
                        except Exception as e:
                            logger.error(f"Failed to parse message: {msg} | Error: {str(e)}")
                            continue

                    # ============================================================
                    # EXTRACT MESSAGE STATUSES (delivery, read, failed)
                    # ============================================================
                    statuses = value.get("statuses", [])
                    for status in statuses:
                        try:
                            event = self._parse_message_status(status)
                            if event:
                                events.append(event)
                        except Exception as e:
                            logger.error(f"Failed to parse status: {status} | Error: {str(e)}")
                            continue

        except Exception as e:
            logger.error(f"Critical error parsing webhook payload: {str(e)}")
            raise ValueError(f"Invalid webhook payload: {str(e)}")

        logger.info(f"Parsed webhook: extracted {len(events)} events")
        return events

    def _parse_incoming_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a single incoming message from webhook.

        Args:
            message: Single message dict from webhook

        Returns:
            Event dict or None if unable to parse
        """
        # Validate required fields
        message_id = message.get("id")
        sender_phone = message.get("from")
        message_type = message.get("type")
        timestamp = message.get("timestamp")

        if not all([message_id, sender_phone, message_type, timestamp]):
            logger.warning(f"Message missing required fields: {message}")
            return None

        # Validate message type is supported
        if message_type not in self.SUPPORTED_MESSAGE_TYPES:
            logger.debug(f"Unsupported message type '{message_type}', skipping")
            return None

        # Normalize sender phone number
        try:
            sender_phone = normalize_phone(sender_phone)
        except ValueError as e:
            logger.warning(f"Invalid sender phone number: {message.get('from')} | Error: {str(e)}")
            return None

        # Parse timestamp
        message_datetime = parse_meta_timestamp(timestamp)

        # Extract message content based on type
        message_content = None
        location_data = None
        media_data = None
        button_reply_id = None

        if message_type == "text":
            message_content = extract_text_from_message(message)
            if not message_content:
                logger.warning(f"Text message missing body: {message}")
                return None

        elif message_type == "location":
            location_data = extract_location_from_message(message)
            if not location_data:
                logger.warning(f"Location message missing coordinates: {message}")
                return None

        elif message_type == "image":
            media_data = extract_media_from_message(message)
            if not media_data:
                logger.warning(f"Image message missing media data: {message}")
                return None

        elif message_type == "interactive":
            button_reply_id = extract_button_reply_from_message(message)
            if not button_reply_id:
                logger.warning(f"Interactive message missing button_reply: {message}")
                return None

        # Build event
        event = {
            "type": "incoming_message",
            "message_id": message_id,
            "sender_phone": sender_phone,
            "message_type": message_type,
            "timestamp": message_datetime,
            "content": message_content,
            "location": location_data,
            "media": media_data,
            "button_reply": button_reply_id,
            "raw_message": message  # Keep raw for debugging
        }

        logger.info(
            f"Parsed incoming message: type={message_type}, "
            f"from={sender_phone}, id={message_id}"
        )

        return event

    def _parse_message_status(self, status: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Parse a message status update (delivery, read, failed).

        Args:
            status: Status dict from webhook

        Returns:
            Event dict or None if unable to parse
        """
        message_id = status.get("id")
        status_type = status.get("status")
        timestamp = status.get("timestamp")
        recipient_phone = status.get("recipient_id")

        if not all([message_id, status_type, timestamp]):
            logger.debug(f"Status update missing required fields: {status}")
            return None

        status_datetime = parse_meta_timestamp(timestamp)

        # Normalize recipient phone if present
        if recipient_phone:
            try:
                recipient_phone = normalize_phone(recipient_phone)
            except ValueError:
                recipient_phone = None

        event = {
            "type": "message_status",
            "message_id": message_id,
            "status": status_type,  # sent, delivered, read, failed
            "timestamp": status_datetime,
            "recipient_phone": recipient_phone,
            "raw_status": status
        }

        logger.debug(f"Parsed message status: {status_type} for message {message_id}")
        return event

    def validate_safety(self, payload: Dict[str, Any]) -> bool:
        """
        Basic safety validation on webhook payload.

        Checks for:
        - Payload is dict
        - Contains 'object' field
        - Contains 'entry' array

        Args:
            payload: Webhook payload

        Returns:
            True if payload passes safety checks
        """
        if not isinstance(payload, dict):
            return False

        if payload.get("object") != "whatsapp_business_account":
            return False

        if not isinstance(payload.get("entry"), list):
            return False

        return True


def parse_incoming_webhook(payload: Dict[str, Any]) -> list:
    """
    Convenience function to parse webhook with global handler instance.

    Args:
        payload: Webhook payload dict

    Returns:
        List of events
    """
    handler = WebhookHandler()
    return handler.parse_webhook(payload)


if __name__ == "__main__":
    # Test webhook parsing with sample payloads
    handler = WebhookHandler()

    # Test: Text message
    sample_text = {
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
                                    "id": "wamid.123",
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

    events = handler.parse_webhook(sample_text)
    print(f"Parsed text message: {events}")

    # Test: Location message
    sample_location = {
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
                                    "id": "wamid.456",
                                    "timestamp": "1680513240",
                                    "type": "location",
                                    "location": {
                                        "latitude": 17.3850,
                                        "longitude": 78.4867
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    events = handler.parse_webhook(sample_location)
    print(f"Parsed location message: {events}")

    print("\nWebhook handler tests completed!")
