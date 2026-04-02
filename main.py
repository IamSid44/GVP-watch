"""
GVP Watch Backend - Main FastAPI Application
----------------------------------------------
Core FastAPI application with webhook and admin endpoints.

Endpoints:
- GET /webhook  - Meta webhook verification
- POST /webhook - Receive incoming messages and events
- GET /health   - Health check
- GET /tickets  - List all tickets (paginated)
- GET /tickets/{ticket_id} - Get ticket details
- GET /logs/{ticket_id} - Get all logs for a ticket

The webhook endpoint is the heart of the system. Every incoming message from
Meta triggers processing:
1. Parse payload
2. Log message
3. Route to appropriate handler (ticket service)
4. Always return 200 OK to Meta (even if processing fails internally)
"""

from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import json

from config import VERIFY_TOKEN
from database import init_db, get_db, Ticket, MessageLog, ActionLog
from logger_config import get_logger
from webhook_handler import parse_incoming_webhook
from ticket_service import TicketService
from reminder_service import start_reminder_service
from models import (
    WebhookVerifyRequest, HealthCheckResponse, ErrorResponse,
    TicketResponse, ActionLogResponse, MessageLogResponse
)
from utils import (
    extract_text_from_message, extract_location_from_message,
    extract_media_from_message, extract_button_reply_from_message, generate_uuid
)

logger = get_logger(__name__)

# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="GVP Watch Backend",
    description="WhatsApp-based Solid Waste Management Grievance System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
async def startup_event():
    """
    Initialize database and start background services on app startup.
    """
    logger.info("GVP Watch Backend starting up...")

    # Initialize database tables
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")

    # Start reminder service (background jobs)
    try:
        start_reminder_service()
        logger.info("Reminder service started")
    except Exception as e:
        logger.error(f"Failed to start reminder service: {str(e)}")

    logger.info("Startup complete!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    logger.info("GVP Watch Backend shutting down...")


# ============================================================================
# WEBHOOK ENDPOINTS (Meta WhatsApp Cloud API)
# ============================================================================

@app.get("/webhook", response_class=JSONResponse)
async def webhook_get(
    hub_mode: str = Query(default=None),
    hub_challenge: str = Query(default=None),
    hub_verify_token: str = Query(default=None)
):
    """
    GET /webhook - Webhook verification challenge from Meta.

    Meta sends a GET request to verify we own the webhook URL.
    We must echo back the hub_challenge if hub_verify_token matches.

    Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/verify-webhooks

    Args:
        hub_mode: Should be "subscribe"
        hub_challenge: Challenge string to echo back
        hub_verify_token: Token we provided in Meta settings (must match VERIFY_TOKEN)

    Returns:
        Challenge string if verified, error otherwise
    """
    logger.debug(f"Webhook verification request: mode={hub_mode}, token={hub_verify_token}")

    # Verify token matches
    if hub_verify_token != VERIFY_TOKEN:
        logger.warning(f"Webhook verification failed: invalid token {hub_verify_token}")
        return JSONResponse(status_code=403, content={"error": "Invalid verification token"})

    # Verify mode is "subscribe"
    if hub_mode != "subscribe":
        logger.warning(f"Webhook verification failed: invalid mode {hub_mode}")
        return JSONResponse(status_code=400, content={"error": "Invalid hub_mode"})

    logger.info("Webhook verified successfully!")
    return hub_challenge


@app.post("/webhook")
async def webhook_post(request: Request, db: Session = Depends(get_db)):
    """
    POST /webhook - Receive incoming messages from Meta WhatsApp Cloud API.

    This endpoint receives ALL incoming events:
    - Text messages
    - Location pins
    - Media uploads (photos)
    - Interactive button clicks
    - Message delivery/read statuses

    Flow:
    1. Parse and validate payload
    2. Log message in MessageLog
    3. Route to appropriate handler (TicketService)
    4. Always return 200 OK to Meta (prevents throttling)

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        200 OK (always, even if processing fails)
    """
    try:
        # Parse request body
        payload = await request.json()

        logger.debug(f"Incoming webhook payload: {json.dumps(payload, indent=2)}")

        # Parse webhook using handler
        try:
            events = parse_incoming_webhook(payload)
        except Exception as e:
            logger.error(f"Failed to parse webhook: {str(e)}")
            # Still return 200 to Meta
            return JSONResponse(status_code=200, content={"status": "received"})

        # Process each event
        ticket_service = TicketService(db)

        for event in events:
            try:
                event_type = event.get("type")

                if event_type == "incoming_message":
                    await _handle_incoming_message(event, ticket_service, db)

                elif event_type == "message_status":
                    await _handle_message_status(event, db)

                else:
                    logger.debug(f"Skipping event type: {event_type}")

            except Exception as e:
                logger.error(f"Error processing event: {str(e)}")
                # Continue processing other events
                continue

        return JSONResponse(status_code=200, content={"status": "received"})

    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook request")
        return JSONResponse(status_code=200, content={"status": "received"})

    except Exception as e:
        logger.error(f"Unexpected error in webhook: {str(e)}")
        return JSONResponse(status_code=200, content={"status": "received"})


async def _handle_incoming_message(event: dict, ticket_service: TicketService, db: Session):
    """
    Internal: Handle incoming message event.

    Routes to appropriate handler based on message content.
    Logs all messages for audit trail.

    Args:
        event: Parsed event from webhook
        ticket_service: TicketService instance
        db: Database session
    """
    sender_phone = event.get("sender_phone")
    message_type = event.get("message_type")
    message_id = event.get("message_id")
    timestamp = event.get("timestamp")

    logger.info(
        f"Processing incoming message: type={message_type}, "
        f"from={sender_phone}, id={message_id}"
    )

    # Log message
    try:
        normalized_message_type = {
            "text": "TEXT",
            "interactive": "INTERACTIVE",
            "location": "LOCATION",
            "image": "MEDIA",
        }.get(str(message_type).lower(), "TEXT")

        message_log = MessageLog(
            message_log_id=generate_uuid(),
            external_message_id=message_id,
            direction="INCOMING",
            sender=sender_phone,
            receiver="BOT",
            message_type=normalized_message_type,
            payload=event.get("raw_message", {}),
            created_at=timestamp
        )
        db.add(message_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log message: {str(e)}")

    # Route to handler based on message type
    if message_type == "text":
        text_body = event.get("content", "").lower().strip()

        # Check for specific keywords
        if text_body == "hi" or text_body == "hello":
            ticket_service.handle_citizen_initial_message(sender_phone)

        elif text_body == "report" or text_body == "report_gvp":
            # Citizen clicked "Report GVP" button
            ticket_service.start_citizen_report(sender_phone)

        elif "not resolved" in text_body or "resolved" in text_body:
            # Officer responding with resolution status
            # Extract ticket ID from message
            ticket_id = _extract_ticket_id_from_text(text_body)
            if ticket_id:
                action = "not_resolved" if "not resolved" in text_body else "resolved"
                ticket_service.handle_officer_response(sender_phone, ticket_id, action)
            else:
                logger.warning(f"Could not extract ticket ID from officer response: {text_body}")

        else:
            logger.debug(f"Unrecognized text message: {text_body}")

    elif message_type == "location":
        # Citizen sent location
        location = event.get("location")
        if location:
            ticket_service.handle_photo_and_location(
                sender_phone,
                location=location
            )

    elif message_type == "image":
        # Citizen sent photo
        media = event.get("media", {})
        photo_id = media.get("id")
        photo_url = media.get("url")

        ticket_service.handle_photo_and_location(
            sender_phone,
            has_photo=True,
            photo_url=photo_url,
            photo_id=photo_id
        )

    elif message_type == "interactive":
        # Citizen clicked a button
        button_reply = event.get("button_reply")

        if button_reply == "report_gvp":
            # Ask for photo and location
            # First, move ticket to AWAITING_PHOTO
            ticket_service.start_citizen_report(sender_phone)

        elif button_reply in ["confirmed", "not_resolved"]:
            # Citizen verification response
            ticket_id = _get_citizen_pending_ticket(sender_phone, db)
            if ticket_id:
                verified = button_reply == "confirmed"
                ticket_service.handle_citizen_verification(
                    sender_phone, ticket_id, verified
                )

        else:
            logger.debug(f"Unknown button reply: {button_reply}")


async def _handle_message_status(event: dict, db: Session):
    """
    Internal: Handle message status update (delivery, read, failed).

    Currently just logs for audit trail. Can be extended to update
    message delivery status in MessageLog.

    Args:
        event: Status event from webhook
        db: Database session
    """
    message_id = event.get("message_id")
    status = event.get("status")

    logger.debug(f"Message {message_id} status: {status}")

    # Could update MessageLog here if needed for delivery tracking
    # For now, just log


def _extract_ticket_id_from_text(text: str) -> Optional[str]:
    """
    Extract ticket ID from officer's response text.

    Pattern: "tk-xxxxxxxx"

    Args:
        text: Officer's message text

    Returns:
        Ticket ID if found
    """
    import re
    match = re.search(r"tk-[\w]{8}", text, re.IGNORECASE)
    if match:
        return match.group(0).lower()
    return None


def _get_citizen_pending_ticket(citizen_phone: str, db: Session) -> Optional[str]:
    """
    Get the ticket ID for a citizen's pending verification.

    Args:
        citizen_phone: Citizen's phone number
        db: Database session

    Returns:
        Ticket ID or None if not found
    """
    ticket = db.query(Ticket).filter(
        Ticket.citizen_phone == citizen_phone,
        Ticket.status == "PENDING_VERIFICATION"
    ).order_by(Ticket.created_at.desc()).first()

    return ticket.ticket_id if ticket else None


# ============================================================================
# HEALTH CHECK & ADMIN ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """
    GET /health - Health check endpoint.

    Returns:
        Health status and timestamp
    """
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        database="connected"
    )


@app.get("/tickets", response_model=List[TicketResponse])
async def list_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    GET /tickets - List all tickets with optional filtering.

    Args:
        skip: Number of tickets to skip (for pagination)
        limit: Number of tickets to return (default 10, max 100)
        status: Optional status filter (e.g., "OPEN", "RESOLVED")
        db: Database session

    Returns:
        List of tickets
    """
    query = db.query(Ticket)

    if status:
        query = query.filter(Ticket.status == status)

    tickets = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()

    return tickets


@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """
    GET /tickets/{ticket_id} - Get detailed ticket information.

    Args:
        ticket_id: Ticket ID
        db: Database session

    Returns:
        Ticket details or 404 if not found
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()

    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} not found")

    return ticket


@app.get("/logs/{ticket_id}")
async def get_ticket_logs(
    ticket_id: str,
    log_type: Optional[str] = Query(None),  # "action" or "message"
    db: Session = Depends(get_db)
):
    """
    GET /logs/{ticket_id} - Get all audit logs for a ticket.

    Args:
        ticket_id: Ticket ID
        log_type: Optional filter ("action" or "message")
        db: Database session

    Returns:
        List of action logs and/or message logs
    """
    logs = {
        "actions": [],
        "messages": []
    }

    if log_type in [None, "action"]:
        actions = db.query(ActionLog).filter(
            ActionLog.ticket_id == ticket_id
        ).order_by(ActionLog.created_at.asc()).all()
        logs["actions"] = actions

    if log_type in [None, "message"]:
        messages = db.query(MessageLog).filter(
            MessageLog.ticket_id == ticket_id
        ).order_by(MessageLog.created_at.asc()).all()
        logs["messages"] = messages

    return logs


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with API information"""
    return {
        "name": "GVP Watch Backend",
        "version": "1.0.0",
        "status": "running",
        "documentation": "/docs",
        "webhook": "/webhook"
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper error response"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting GVP Watch Backend on http://127.0.0.1:8000")
    logger.info("API documentation at http://127.0.0.1:8000/docs")

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
