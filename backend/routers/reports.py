"""
Reports Router — Web-based report submission and listing.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid
import os

from database import get_db, Ticket, Ward, User, ActionLog
from models import ReportResponse, ReportMapItem, WebReportCreate
from config import UPLOAD_DIR
from logger_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse)
async def create_web_report(
    latitude: float = Form(...),
    longitude: float = Form(...),
    severity: str = Form("MEDIUM"),
    category: str = Form("garbage_on_roads"),
    description: Optional[str] = Form(None),
    reporter_name: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    photo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    """Submit a new report via the web frontend."""
    ticket_id = f"tk-{uuid.uuid4().hex[:8]}"

    # Save photo if provided
    photo_url = None
    if photo and photo.filename:
        ext = os.path.splitext(photo.filename)[1] or ".jpg"
        filename = f"{ticket_id}{ext}"
        filepath = UPLOAD_DIR / filename
        content = await photo.read()
        with open(filepath, "wb") as f:
            f.write(content)
        photo_url = f"/uploads/{filename}"

    # Create a web user placeholder if needed
    web_user_phone = f"web-{uuid.uuid4().hex[:12]}"
    user = User(
        user_id=str(uuid.uuid4()),
        phone=web_user_phone,
        role="CITIZEN",
        name=reporter_name or "Web User",
    )
    db.add(user)
    db.flush()

    # Detect ward from coordinates (simple nearest-center approach)
    ward = _find_nearest_ward(db, latitude, longitude)

    ticket = Ticket(
        ticket_id=ticket_id,
        citizen_phone=web_user_phone,
        ward_id=ward.ward_id if ward else None,
        latitude=latitude,
        longitude=longitude,
        photo_url=photo_url,
        severity_score=severity.upper(),
        status="OPEN",
        source="WEB",
        description=description,
        category=category,
        address=address,
        reporter_name=reporter_name,
        upvote_count=0,
        moderation_status="APPROVED",
        created_at=datetime.utcnow(),
        photo_received_at=datetime.utcnow() if photo_url else None,
    )
    db.add(ticket)

    # Log action
    action = ActionLog(
        action_log_id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        action_type="STATUS_CHANGE",
        old_status=None,
        new_status="OPEN",
        actor="citizen",
        notes={"source": "WEB", "category": category},
    )
    db.add(action)
    db.commit()

    logger.info(f"Web report created: {ticket_id}")

    return _ticket_to_response(ticket, db)


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    ward_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """List reports with optional filters."""
    query = db.query(Ticket).filter(Ticket.moderation_status == "APPROVED")

    if status:
        query = query.filter(Ticket.status == status.upper())
    if ward_id:
        query = query.filter(Ticket.ward_id == ward_id)
    if severity:
        query = query.filter(Ticket.severity_score == severity.upper())
    if category:
        query = query.filter(Ticket.category == category)

    tickets = query.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()
    return [_ticket_to_response(t, db) for t in tickets]


@router.get("/map", response_model=List[ReportMapItem])
async def get_map_reports(db: Session = Depends(get_db)):
    """Get lightweight report data for map markers."""
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.moderation_status == "APPROVED",
            Ticket.latitude.isnot(None),
            Ticket.longitude.isnot(None),
        )
        .all()
    )
    return tickets


@router.get("/{ticket_id}", response_model=ReportResponse)
async def get_report(ticket_id: str, db: Session = Depends(get_db)):
    """Get a single report by ID."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Report not found")
    return _ticket_to_response(ticket, db)


@router.post("/{ticket_id}/mark-resolved", response_model=ReportResponse)
async def mark_report_resolved(
    ticket_id: str,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Public endpoint to mark a report as cleaned up / resolved. Requires a verification photo."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Report not found")
    if ticket.status == "RESOLVED":
        return _ticket_to_response(ticket, db)

    # Save resolution verification photo
    ext = os.path.splitext(photo.filename)[1] if photo.filename else ".jpg"
    filename = f"{ticket_id}_resolved{ext}"
    filepath = UPLOAD_DIR / filename
    content = await photo.read()
    with open(filepath, "wb") as f:
        f.write(content)
    resolution_photo_url = f"/uploads/{filename}"

    old_status = ticket.status
    ticket.status = "RESOLVED"
    ticket.resolved_at = datetime.utcnow()
    ticket.resolution_photo_url = resolution_photo_url
    action = ActionLog(
        action_log_id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        action_type="STATUS_CHANGE",
        old_status=old_status,
        new_status="RESOLVED",
        actor="citizen",
        notes={"action": "mark_resolved_web"},
    )
    db.add(action)
    db.commit()
    return _ticket_to_response(ticket, db)


def _find_nearest_ward(db: Session, lat: float, lng: float) -> Optional[Ward]:
    """Find the nearest ward by center point distance."""
    wards = db.query(Ward).filter(Ward.center_lat.isnot(None)).all()
    if not wards:
        return db.query(Ward).first()

    best = None
    best_dist = float("inf")
    for w in wards:
        dist = (w.center_lat - lat) ** 2 + (w.center_lng - lng) ** 2
        if dist < best_dist:
            best_dist = dist
            best = w
    return best


def _ticket_to_response(ticket: Ticket, db: Session) -> ReportResponse:
    """Convert a Ticket ORM object to a ReportResponse."""
    ward_name = None
    if ticket.ward_id:
        ward = db.query(Ward).filter(Ward.ward_id == ticket.ward_id).first()
        if ward:
            ward_name = ward.ward_name

    return ReportResponse(
        ticket_id=ticket.ticket_id,
        citizen_phone=ticket.citizen_phone if not ticket.citizen_phone.startswith("web-") else None,
        officer_phone=ticket.officer_phone,
        ward_id=ticket.ward_id,
        ward_name=ward_name,
        latitude=ticket.latitude,
        longitude=ticket.longitude,
        photo_url=ticket.photo_url,
        resolution_photo_url=ticket.resolution_photo_url,
        severity_score=ticket.severity_score,
        status=ticket.status,
        description=ticket.description,
        source=ticket.source or "WHATSAPP",
        upvote_count=ticket.upvote_count or 0,
        moderation_status=ticket.moderation_status or "APPROVED",
        address=ticket.address,
        category=ticket.category,
        reporter_name=ticket.reporter_name,
        created_at=ticket.created_at,
        resolved_at=ticket.resolved_at,
    )
