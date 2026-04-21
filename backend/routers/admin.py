"""
Admin Router — Moderation panel endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import hashlib

from database import get_db, Ticket, ActionLog
from models import ReportResponse, AdminLoginRequest, AdminActionRequest
from config import ADMIN_KEY
from routers.reports import _ticket_to_response

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _verify_admin(authorization: Optional[str] = Header(None)):
    """Verify admin token from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization")
    token = authorization.replace("Bearer ", "")
    expected = hashlib.sha256(ADMIN_KEY.encode()).hexdigest()
    if token != expected:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.post("/login")
async def admin_login(body: AdminLoginRequest):
    """Validate admin key and return a session token."""
    if body.key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    token = hashlib.sha256(ADMIN_KEY.encode()).hexdigest()
    return {"success": True, "token": token}


@router.get("/pending", response_model=List[ReportResponse])
async def get_pending_reports(
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin),
):
    """Get reports pending moderation."""
    tickets = (
        db.query(Ticket)
        .filter(Ticket.moderation_status == "PENDING")
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return [_ticket_to_response(t, db) for t in tickets]


@router.get("/reports", response_model=List[ReportResponse])
async def get_all_reports(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin),
):
    """Get all reports with optional status filter."""
    query = db.query(Ticket)
    if status:
        query = query.filter(Ticket.status == status.upper())
    tickets = query.order_by(Ticket.created_at.desc()).limit(100).all()
    return [_ticket_to_response(t, db) for t in tickets]


@router.post("/reports/{ticket_id}/approve", response_model=ReportResponse)
async def approve_report(
    ticket_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin),
):
    """Approve a pending report."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Report not found")

    ticket.moderation_status = "APPROVED"
    action = ActionLog(
        action_log_id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        action_type="STATUS_CHANGE",
        old_status="PENDING",
        new_status="APPROVED",
        actor="admin",
        notes={"action": "moderation_approve"},
    )
    db.add(action)
    db.commit()
    return _ticket_to_response(ticket, db)


@router.post("/reports/{ticket_id}/reject", response_model=ReportResponse)
async def reject_report(
    ticket_id: str,
    body: AdminActionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin),
):
    """Reject a pending report with a reason."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Report not found")

    ticket.moderation_status = "REJECTED"
    action = ActionLog(
        action_log_id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        action_type="STATUS_CHANGE",
        old_status="PENDING",
        new_status="REJECTED",
        actor="admin",
        notes={"action": "moderation_reject", "reason": body.reason},
    )
    db.add(action)
    db.commit()
    return _ticket_to_response(ticket, db)


@router.post("/reports/{ticket_id}/resolve", response_model=ReportResponse)
async def resolve_report(
    ticket_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_admin),
):
    """Mark a report as resolved (admin action)."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Report not found")

    old_status = ticket.status
    ticket.status = "RESOLVED"
    ticket.resolved_at = datetime.utcnow()
    action = ActionLog(
        action_log_id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        action_type="STATUS_CHANGE",
        old_status=old_status,
        new_status="RESOLVED",
        actor="admin",
        notes={"action": "admin_resolve"},
    )
    db.add(action)
    db.commit()
    return _ticket_to_response(ticket, db)
