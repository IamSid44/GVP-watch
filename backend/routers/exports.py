"""
Exports Router — CSV data export.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io
import csv

from database import get_db, Ticket, Ward

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("/csv")
async def export_csv(
    ward_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Download reports as CSV."""
    query = db.query(Ticket).filter(Ticket.moderation_status == "APPROVED")
    if ward_id:
        query = query.filter(Ticket.ward_id == ward_id)
    if status:
        query = query.filter(Ticket.status == status.upper())

    tickets = query.order_by(Ticket.created_at.desc()).all()

    # Build ward lookup
    wards = {w.ward_id: w for w in db.query(Ward).all()}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Report ID", "Ward Name", "Ward Number", "Zone",
        "Severity", "Category", "Status", "Address",
        "Latitude", "Longitude", "Description",
        "Source", "Upvotes", "Reported At", "Resolved At",
        "Photo URL",
    ])

    for t in tickets:
        ward = wards.get(t.ward_id)
        writer.writerow([
            t.ticket_id,
            ward.ward_name if ward else "",
            ward.ward_number if ward else "",
            ward.zone if ward else "",
            t.severity_score or "",
            t.category or "",
            t.status,
            t.address or "",
            t.latitude or "",
            t.longitude or "",
            t.description or "",
            t.source or "WHATSAPP",
            t.upvote_count or 0,
            t.created_at.isoformat() if t.created_at else "",
            t.resolved_at.isoformat() if t.resolved_at else "",
            t.photo_url or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gvp-watch-reports.csv"},
    )
