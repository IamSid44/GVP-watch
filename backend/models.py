"""
GVP Watch Backend - Pydantic Models
------------------------------------
Request/response schemas for API validation and documentation.

These models handle:
- Incoming webhook payloads from Meta
- Outgoing message schemas for WhatsApp API
- Internal data transfer objects (DTOs)
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================================
# ENUMS FOR VALIDATION
# ============================================================================

class TicketStatus(str, Enum):
    INITIATED = "INITIATED"
    AWAITING_PHOTO = "AWAITING_PHOTO"
    OPEN = "OPEN"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    RESOLVED = "RESOLVED"
    UNRESPONSIVE = "UNRESPONSIVE"


class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


# ============================================================================
# WEBHOOK PAYLOAD MODELS (from Meta WhatsApp Cloud API)
# ============================================================================

class WebhookVerifyRequest(BaseModel):
    """
    GET request for webhook verification challenge.
    Meta sends this to verify we own the webhook URL.

    Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/verify-webhooks
    """
    hub_mode: str = Field(..., description="Should be 'subscribe'")
    hub_challenge: str = Field(..., description="Challenge string to echo back")
    hub_verify_token: str = Field(..., description="Token we provided in Meta settings")


class Contact(BaseModel):
    """Contact information from incoming message"""
    wa_id: str
    profile: Dict[str, Any] = {}


class Location(BaseModel):
    """Location data from incoming message"""
    latitude: float
    longitude: float
    address: Optional[str] = None
    name: Optional[str] = None


class Media(BaseModel):
    """Media metadata from incoming message"""
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    id: Optional[str] = None
    url: Optional[str] = None


class InteractiveObject(BaseModel):
    """Interactive button/reply data from incoming message"""
    type: Optional[str] = None  # button_reply, list_reply
    button_reply: Optional[Dict[str, Any]] = None
    list_reply: Optional[Dict[str, Any]] = None


class MessageContent(BaseModel):
    """
    Incoming message content (flexible structure).
    Can contain: text, location, image, interactive buttons, etc.

    Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/webhook-reference
    """
    from_: str = Field(..., alias="from")
    id: str
    timestamp: str
    type: str  # text, location, image, interactive, etc.
    text: Optional[Dict[str, str]] = None  # {"body": "message text"}
    location: Optional[Location] = None
    image: Optional[Media] = None
    video: Optional[Media] = None
    document: Optional[Media] = None
    interactive: Optional[InteractiveObject] = None

    class Config:
        allow_population_by_field_name = True


class Message(BaseModel):
    """Message object from webhook"""
    messaging_product: str = "whatsapp"
    contacts: List[Contact]
    messages: List[MessageContent]


class Status(BaseModel):
    """Message delivery status from webhook"""
    id: str
    status: str  # sent, delivered, read, failed


class Invoice(BaseModel):
    """Invoice status from webhook (rarely used)"""
    pass


class Entry(BaseModel):
    """Entry in webhook change"""
    id: str
    changes: List[Dict[str, Any]]


class WebhookPayload(BaseModel):
    """
    Complete webhook payload from Meta.
    Contains messages, status updates, and other events.
    """
    object: str  # Should be "whatsapp_business_account"
    entry: List[Entry]


# ============================================================================
# OUTGOING MESSAGE MODELS (to Meta WhatsApp Cloud API)
# ============================================================================

class TextMessage(BaseModel):
    """Send a simple text message"""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "text"
    text: Dict[str, str] = Field(...)

    class Config:
        schema_extra = {
            "example": {
                "messaging_product": "whatsapp",
                "to": "919876543210",
                "type": "text",
                "text": {"body": "Hello!"}
            }
        }


class ButtonReply(BaseModel):
    """A single button in interactive message"""
    type: str = "reply"
    reply: Dict[str, str]  # {"id": "button_id", "title": "Button Label"}


class HeaderComponent(BaseModel):
    """Message header (optional)"""
    type: str = "text"
    text: Optional[str] = None


class BodyComponent(BaseModel):
    """Message body content"""
    type: str = "text"
    text: str


class FooterComponent(BaseModel):
    """Message footer (optional)"""
    type: str = "text"
    text: Optional[str] = None


class ActionComponent(BaseModel):
    """Action component with buttons"""
    type: str = "buttons"
    buttons: List[ButtonReply]


class InteractiveMessage(BaseModel):
    """Send interactive message with buttons"""
    messaging_product: str = "whatsapp"
    to: str
    type: str = "interactive"
    interactive: Dict[str, Any]

    class Config:
        schema_extra = {
            "example": {
                "messaging_product": "whatsapp",
                "to": "919876543210",
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": "Confirm action?"},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": "yes", "title": "Yes"}},
                            {"type": "reply", "reply": {"id": "no", "title": "No"}}
                        ]
                    }
                }
            }
        }


class LocationMessage(BaseModel):
    """Send location message"""
    messaging_product: str = "whatsapp"
    to: str
    type: str = "location"
    location: Dict[str, float]


class TemplateComponent(BaseModel):
    """Component in template message"""
    type: str
    parameters: Optional[List[Dict[str, Any]]] = None


class TemplateMessage(BaseModel):
    """Send templated message (pre-approved by Meta)"""
    messaging_product: str = "whatsapp"
    to: str
    type: str = "template"
    template: Dict[str, Any]


# ============================================================================
# INTERNAL DATA TRANSFER OBJECTS (DTOs)
# ============================================================================

class TicketCreate(BaseModel):
    """DTO for creating a ticket"""
    citizen_phone: str
    ward_id: str
    latitude: float
    longitude: float
    photo_url: Optional[str] = None
    severity_score: Optional[SeverityLevel] = None


class TicketUpdate(BaseModel):
    """DTO for updating a ticket"""
    status: Optional[TicketStatus] = None
    officer_phone: Optional[str] = None
    severity_score: Optional[SeverityLevel] = None
    resolved_at: Optional[datetime] = None


class TicketResponse(BaseModel):
    """DTO for ticket response in APIs"""
    ticket_id: str
    citizen_phone: str
    officer_phone: Optional[str] = None
    ward_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_url: Optional[str] = None
    photo_id: Optional[str] = None
    severity_score: Optional[str] = None
    status: str
    created_at: datetime
    photo_received_at: Optional[datetime] = None
    officer_assigned_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    last_reminder_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ActionLogResponse(BaseModel):
    """DTO for action log response"""
    action_log_id: str
    ticket_id: str
    action_type: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    actor: str
    actor_phone: Optional[str] = None
    notes: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class MessageLogResponse(BaseModel):
    """DTO for message log response"""
    message_log_id: str
    external_message_id: Optional[str] = None
    ticket_id: Optional[str] = None
    direction: str
    sender: str
    receiver: str
    message_type: str
    payload: Dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime
    database: str = "connected"


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime


# ============================================================================
# WEB FRONTEND MODELS
# ============================================================================

class WebReportCreate(BaseModel):
    """Schema for submitting a report via the web frontend."""
    latitude: float
    longitude: float
    severity: str = "MEDIUM"
    category: str = "garbage_on_roads"
    description: Optional[str] = None
    reporter_name: Optional[str] = None
    address: Optional[str] = None


class ReportResponse(BaseModel):
    """Full report response for the web frontend."""
    ticket_id: str
    citizen_phone: Optional[str] = None
    officer_phone: Optional[str] = None
    ward_id: Optional[str] = None
    ward_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    photo_url: Optional[str] = None
    resolution_photo_url: Optional[str] = None
    severity_score: Optional[str] = None
    status: str
    description: Optional[str] = None
    source: str = "WHATSAPP"
    upvote_count: int = 0
    moderation_status: str = "APPROVED"
    address: Optional[str] = None
    category: Optional[str] = None
    reporter_name: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReportMapItem(BaseModel):
    """Lightweight report data for map markers."""
    ticket_id: str
    latitude: float
    longitude: float
    severity_score: Optional[str] = None
    status: str
    category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnalyticsSummary(BaseModel):
    """Summary analytics for the dashboard."""
    total_reports: int
    open_reports: int
    resolved_reports: int
    pending_reports: int
    unresponsive_reports: int
    resolution_rate: float
    avg_resolution_hours: Optional[float] = None


class DailyTrend(BaseModel):
    """Reports per day for trend charts."""
    date: str
    count: int


class WardStats(BaseModel):
    """Report stats grouped by ward."""
    ward_id: str
    ward_name: str
    ward_number: Optional[int] = None
    total: int
    open: int
    resolved: int


class SeverityStats(BaseModel):
    """Report stats grouped by severity."""
    severity: str
    count: int


class StatusStats(BaseModel):
    """Report stats grouped by status."""
    status: str
    count: int


class WardResponse(BaseModel):
    """Ward detail response."""
    ward_id: str
    ward_name: str
    ward_number: Optional[int] = None
    circle: Optional[str] = None
    zone: Optional[str] = None
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    total_reports: int = 0
    open_reports: int = 0
    resolved_reports: int = 0

    class Config:
        from_attributes = True


class RepresentativeResponse(BaseModel):
    """Representative response."""
    rep_id: str
    name: str
    title: str
    level: str
    phone: Optional[str] = None
    email: Optional[str] = None
    party: Optional[str] = None

    class Config:
        from_attributes = True


class UpvoteRequest(BaseModel):
    """Upvote request body."""
    fingerprint: str


class AdminLoginRequest(BaseModel):
    """Admin login request."""
    key: str


class AdminActionRequest(BaseModel):
    """Admin moderation action."""
    reason: Optional[str] = None


# ============================================================================
# VALIDATORS
# ============================================================================

def validate_phone_number(phone: str) -> str:
    """
    Validate phone number format.
    Accepts: +91234567890, 91234567890, or 234567890 formats.

    Args:
        phone: Phone number string

    Returns:
        Normalized phone number without + prefix

    Raises:
        ValueError: If phone number is invalid
    """
    # Remove + if present
    phone_clean = phone.lstrip("+")

    # Must be digits only, 10-20 characters
    if not phone_clean.isdigit() or len(phone_clean) < 10 or len(phone_clean) > 20:
        raise ValueError(f"Invalid phone number format: {phone}")

    return phone_clean


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate latitude and longitude values.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        True if valid

    Raises:
        ValueError: If coordinates are invalid
    """
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")
    return True
