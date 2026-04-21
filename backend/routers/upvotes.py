"""
Upvotes Router — Fingerprint-based upvote system.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import uuid

from database import get_db, Ticket, Upvote
from models import UpvoteRequest

router = APIRouter(prefix="/api/reports", tags=["upvotes"])


@router.post("/{ticket_id}/upvote")
async def upvote_report(
    ticket_id: str,
    body: UpvoteRequest,
    db: Session = Depends(get_db),
):
    """Upvote a report. One vote per fingerprint per report."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Report not found")

    upvote = Upvote(
        upvote_id=str(uuid.uuid4()),
        ticket_id=ticket_id,
        fingerprint=body.fingerprint,
    )

    try:
        db.add(upvote)
        ticket.upvote_count = (ticket.upvote_count or 0) + 1
        db.commit()
        return {"success": True, "upvote_count": ticket.upvote_count}
    except IntegrityError:
        db.rollback()
        return {"success": False, "message": "Already upvoted", "upvote_count": ticket.upvote_count or 0}
