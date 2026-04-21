"""
Analytics Router — Dashboard aggregation endpoints.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
from datetime import datetime, timedelta

from database import get_db, Ticket, Ward
from models import AnalyticsSummary, DailyTrend, WardStats, SeverityStats, StatusStats

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(db: Session = Depends(get_db)):
    """Get overall analytics summary."""
    total = db.query(func.count(Ticket.ticket_id)).filter(Ticket.moderation_status == "APPROVED").scalar() or 0
    open_count = db.query(func.count(Ticket.ticket_id)).filter(Ticket.status == "OPEN", Ticket.moderation_status == "APPROVED").scalar() or 0
    resolved = db.query(func.count(Ticket.ticket_id)).filter(Ticket.status == "RESOLVED", Ticket.moderation_status == "APPROVED").scalar() or 0
    pending = db.query(func.count(Ticket.ticket_id)).filter(Ticket.status == "PENDING_VERIFICATION", Ticket.moderation_status == "APPROVED").scalar() or 0
    unresponsive = db.query(func.count(Ticket.ticket_id)).filter(Ticket.status == "UNRESPONSIVE", Ticket.moderation_status == "APPROVED").scalar() or 0

    resolution_rate = (resolved / total * 100) if total > 0 else 0.0

    # Average resolution time (hours)
    avg_hours = None
    resolved_tickets = (
        db.query(Ticket)
        .filter(Ticket.status == "RESOLVED", Ticket.resolved_at.isnot(None))
        .all()
    )
    if resolved_tickets:
        total_hours = sum(
            (t.resolved_at - t.created_at).total_seconds() / 3600
            for t in resolved_tickets
        )
        avg_hours = round(total_hours / len(resolved_tickets), 1)

    return AnalyticsSummary(
        total_reports=total,
        open_reports=open_count,
        resolved_reports=resolved,
        pending_reports=pending,
        unresponsive_reports=unresponsive,
        resolution_rate=round(resolution_rate, 1),
        avg_resolution_hours=avg_hours,
    )


@router.get("/daily", response_model=List[DailyTrend])
async def get_daily_trend(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """Get daily report count for the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    tickets = (
        db.query(Ticket)
        .filter(Ticket.created_at >= cutoff, Ticket.moderation_status == "APPROVED")
        .all()
    )

    # Group by date
    counts = {}
    for t in tickets:
        date_str = t.created_at.strftime("%Y-%m-%d")
        counts[date_str] = counts.get(date_str, 0) + 1

    # Fill in missing days
    result = []
    for i in range(days):
        d = (datetime.utcnow() - timedelta(days=days - 1 - i)).strftime("%Y-%m-%d")
        result.append(DailyTrend(date=d, count=counts.get(d, 0)))

    return result


@router.get("/by-ward", response_model=List[WardStats])
async def get_by_ward(db: Session = Depends(get_db)):
    """Get report stats grouped by ward."""
    wards = db.query(Ward).all()
    result = []
    for w in wards:
        total = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.ward_id == w.ward_id, Ticket.moderation_status == "APPROVED"
        ).scalar() or 0
        open_count = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.ward_id == w.ward_id, Ticket.status == "OPEN", Ticket.moderation_status == "APPROVED"
        ).scalar() or 0
        resolved = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.ward_id == w.ward_id, Ticket.status == "RESOLVED", Ticket.moderation_status == "APPROVED"
        ).scalar() or 0
        result.append(WardStats(
            ward_id=w.ward_id,
            ward_name=w.ward_name,
            ward_number=w.ward_number,
            total=total,
            open=open_count,
            resolved=resolved,
        ))
    result.sort(key=lambda x: x.total, reverse=True)
    return result


@router.get("/by-severity", response_model=List[SeverityStats])
async def get_by_severity(db: Session = Depends(get_db)):
    """Get report count grouped by severity."""
    result = []
    for sev in ["LOW", "MEDIUM", "HIGH"]:
        count = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.severity_score == sev, Ticket.moderation_status == "APPROVED"
        ).scalar() or 0
        result.append(SeverityStats(severity=sev, count=count))
    return result


@router.get("/by-status", response_model=List[StatusStats])
async def get_by_status(db: Session = Depends(get_db)):
    """Get report count grouped by status."""
    result = []
    for status in ["INITIATED", "AWAITING_PHOTO", "OPEN", "PENDING_VERIFICATION", "RESOLVED", "UNRESPONSIVE"]:
        count = db.query(func.count(Ticket.ticket_id)).filter(
            Ticket.status == status, Ticket.moderation_status == "APPROVED"
        ).scalar() or 0
        result.append(StatusStats(status=status, count=count))
    return result
