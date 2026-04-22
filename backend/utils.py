"""
GVP Watch Backend - Utility Functions
--------------------------------------
Helper functions for common operations across the application.

Includes:
- Phone number validation and normalization
- Image analysis mock function
- Message body extraction from complex payloads
- Timestamp utilities
- Severity score calculation
"""

import uuid
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
import hashlib
import hmac
import json
from enum import Enum

from logger_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# PHONE NUMBER UTILITIES
# ============================================================================

def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to international format without + prefix.

    Args:
        phone: Phone number in various formats
               - {91}1234567890
               - +{91}1234567890
               - 1234567890

    Returns:
        Normalized phone number (e.g., "919876543210")

    Raises:
        ValueError: If phone number is invalid
    """
    # Remove whitespace and special characters except digits and +
    phone_clean = re.sub(r"[^\d+]", "", phone)

    # Remove + prefix if present
    if phone_clean.startswith("+"):
        phone_clean = phone_clean[1:]

    # Validate: must be digits only, 10-20 chars
    if not phone_clean.isdigit():
        raise ValueError(f"Invalid phone number (non-digit chars): {phone}")

    if not (10 <= len(phone_clean) <= 20):
        raise ValueError(f"Invalid phone number (length): {phone}")

    logger.debug(f"Normalized phone {phone} -> {phone_clean}")
    return phone_clean


def is_valid_phone(phone: str) -> bool:
    """
    Check if phone number is valid without raising exception.

    Args:
        phone: Phone number string

    Returns:
        True if valid, False otherwise
    """
    try:
        normalize_phone(phone)
        return True
    except ValueError:
        return False


def extract_country_code(phone: str) -> str:
    """
    Extract country code from phone number.
    Assumes first 1-3 digits are country code.

    Args:
        phone: Normalized phone number

    Returns:
        Country code (e.g., "91" for India)
    """
    if len(phone) >= 12:
        return phone[:2]  # 2-digit code (e.g., "91")
    return phone[:1]  # Fallback to 1-digit


# ============================================================================
# IMAGE ANALYSIS MOCK
# ============================================================================

def analyze_image(image_id: str, image_url: Optional[str] = None) -> str:
    """
    Mock image analysis function simulating ML waste detection model.

    In production, this would:
    1. Download image from image_url
    2. Run ML model to classify waste type and severity
    3. Return confidence scores

    Current implementation:
    - Uses a hash of image_id to pseudo-randomly assign severity
    - Returns deterministic but varied results for testing

    Args:
        image_id: Image ID from Meta (unique identifier)
        image_url: Optional URL for the image (not used in mock)

    Returns:
        Severity level: "LOW", "MEDIUM", or "HIGH"
    """
    # Use hash of image_id to pseudo-randomly determine severity
    # This ensures same image always gets same score (deterministic)
    hash_val = int(hashlib.md5(image_id.encode()).hexdigest(), 16)
    severity_idx = hash_val % 3

    severity_map = {
        0: "LOW",
        1: "MEDIUM",
        2: "HIGH"
    }

    result = severity_map[severity_idx]

    logger.info(f"Image analysis: {image_id} -> {result}")
    return result


# ============================================================================
# MESSAGE EXTRACTION UTILITIES
# ============================================================================

def extract_text_from_message(message: dict) -> Optional[str]:
    """
    Extract text from a text message payload.

    Args:
        message: Message dict from webhook

    Returns:
        Message text or None if not found
    """
    if message.get("type") == "text":
        text_body = message.get("text", {})
        if isinstance(text_body, dict):
            return text_body.get("body")
    return None


def extract_location_from_message(message: dict) -> Optional[dict]:
    """
    Extract latitude and longitude from a location message.

    Args:
        message: Message dict from webhook

    Returns:
        Dict with 'latitude' and 'longitude' keys, or None if not found
    """
    if message.get("type") == "location":
        location = message.get("location", {})
        lat = location.get("latitude")
        lon = location.get("longitude")

        if lat is not None and lon is not None:
            # Validate coordinates
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return {"latitude": lat, "longitude": lon}
            else:
                logger.warning(f"Invalid coordinates in location: lat={lat}, lon={lon}")

    return None


def extract_media_from_message(message: dict) -> Optional[dict]:
    """
    Extract media (image, video, document) from message.

    Args:
        message: Message dict from webhook

    Returns:
        Dict with media info {'type': 'image', 'id': '...', 'mime_type': '...'}
        or None if no media found
    """
    message_type = message.get("type")

    if message_type in ["image", "video", "document"]:
        media_data = message.get(message_type, {})
        return {
            "type": message_type,
            "id": media_data.get("id"),
            "mime_type": media_data.get("mime_type"),
            "sha256": media_data.get("sha256")
        }

    return None


def extract_button_reply_from_message(message: dict) -> Optional[str]:
    """
    Extract button reply ID from interactive message.

    Args:
        message: Message dict from webhook

    Returns:
        Button ID (e.g., "yes", "report_gvp") or None
    """
    if message.get("type") == "interactive":
        interactive = message.get("interactive", {})
        button_reply = interactive.get("button_reply", {})
        return button_reply.get("id")

    return None


# ============================================================================
# TIMESTAMP & TIME UTILITIES
# ============================================================================

def parse_meta_timestamp(timestamp_str: str) -> datetime:
    """
    Parse Meta's webhook timestamp (Unix epoch as string) to datetime.

    Args:
        timestamp_str: Unix timestamp as string (e.g., "1680513234")

    Returns:
        datetime object in UTC
    """
    try:
        timestamp = int(timestamp_str)
        return datetime.utcfromtimestamp(timestamp)
    except (ValueError, TypeError):
        logger.warning(f"Failed to parse timestamp: {timestamp_str}")
        return datetime.utcnow()


def time_since(dt: datetime) -> str:
    """
    Calculate human-readable time difference from now.

    Args:
        dt: Past datetime

    Returns:
        String like "2 hours ago", "1 day ago", etc.
    """
    now = datetime.utcnow()
    diff = now - dt

    if diff.days > 0:
        return f"{diff.days} day(s) ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hour(s) ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minute(s) ago"
    else:
        return "just now"


def should_send_first_reminder(last_reminder: Optional[datetime]) -> bool:
    """
    Check if 1-day reminder should be sent (ticket in PENDING_VERIFICATION).

    Args:
        last_reminder: When last reminder was sent (None if never sent)

    Returns:
        True if more than 1 day has passed
    """
    if last_reminder is None:
        # First reminder should be sent after 1 day from creation
        return True

    elapsed = datetime.utcnow() - last_reminder
    return elapsed >= timedelta(days=1)


def should_auto_resolve(last_reminder: Optional[datetime]) -> bool:
    """
    Check if ticket should be auto-resolved (2 days of inactivity).

    Args:
        last_reminder: When first reminder was sent

    Returns:
        True if more than 1 day has passed since first reminder
    """
    if last_reminder is None:
        return False

    elapsed = datetime.utcnow() - last_reminder
    return elapsed > timedelta(days=1)


# ============================================================================
# SIGNATURE VERIFICATION
# ============================================================================

def verify_webhook_signature(payload_body: str, signature: str, verify_token: str) -> bool:
    """
    Verify webhook signature from Meta for security.

    Meta sends X-Hub-Signature header with HMAC-SHA256 signature.
    Format: sha1=<signature>

    Args:
        payload_body: Raw request body as string
        signature: X-Hub-Signature header value from Meta
        verify_token: APP_SECRET (not webhook token)

    Returns:
        True if signature is valid
    """
    # Note: In production, use APP_SECRET, not VERIFY_TOKEN
    # Format of signature: "sha256=<hex>"
    expected_signature = "sha256=" + hmac.new(
        verify_token.encode(),
        payload_body.encode(),
        hashlib.sha256
    ).hexdigest()

    # Safe comparison to prevent timing attacks
    return hmac.compare_digest(signature, expected_signature)


# ============================================================================
# ID GENERATION
# ============================================================================

def generate_ticket_id() -> str:
    """
    Generate a human-friendly ticket ID.

    Returns:
        ID like "tk-a1b2c3d4" (prefix + 8 hex chars)
    """
    # Use first 8 chars of UUID hex, remove hyphens
    unique_part = uuid.uuid4().hex[:8]
    return f"tk-{unique_part}"


def generate_uuid() -> str:
    """
    Generate a UUID string.

    Returns:
        UUID as string
    """
    return str(uuid.uuid4())


# ============================================================================
# JSON UTILITIES
# ============================================================================

def safe_json_loads(json_str: str, default: dict = None) -> dict:
    """
    Safely parse JSON string with fallback.

    Args:
        json_str: JSON string to parse
        default: Default dict if parsing fails

    Returns:
        Parsed dict or default
    """
    if default is None:
        default = {}

    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to parse JSON: {json_str}")
        return default


def safe_json_dumps(obj: dict, indent: int = 2) -> str:
    """
    Safely convert dict to JSON string.

    Args:
        obj: Dict to serialize
        indent: JSON indentation level

    Returns:
        JSON string or "{}" if serialization fails
    """
    try:
        return json.dumps(obj, indent=indent, default=str)
    except (TypeError, ValueError):
        logger.warning(f"Failed to serialize to JSON: {obj}")
        return "{}"


if __name__ == "__main__":
    # Test utility functions
    print("Testing utility functions...")

    # Phone number tests
    print(f"normalize_phone('+91 9876 543210'): {normalize_phone('+91 9876 543210')}")
    print(f"is_valid_phone('919876543210'): {is_valid_phone('919876543210')}")

    # Image analysis test
    print(f"analyze_image('test_id_1'): {analyze_image('test_id_1')}")
    print(f"analyze_image('test_id_2'): {analyze_image('test_id_2')}")

    # UUID test
    print(f"generate_ticket_id(): {generate_ticket_id()}")

    print("\nAll utility tests passed!")
