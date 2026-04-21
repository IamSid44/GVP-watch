"""
Wards Router — Ward data and GeoJSON boundaries.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db, Ward, Ticket, Representative
from models import WardResponse, RepresentativeResponse

router = APIRouter(prefix="/api/wards", tags=["wards"])


@router.get("", response_model=List[WardResponse])
async def list_wards(db: Session = Depends(get_db)):
    """List all wards with report counts."""
    wards = db.query(Ward).order_by(Ward.ward_number).all()
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
        result.append(WardResponse(
            ward_id=w.ward_id,
            ward_name=w.ward_name,
            ward_number=w.ward_number,
            circle=w.circle,
            zone=w.zone,
            center_lat=w.center_lat,
            center_lng=w.center_lng,
            total_reports=total,
            open_reports=open_count,
            resolved_reports=resolved,
        ))
    return result


@router.get("/boundaries")
async def get_ward_boundaries(db: Session = Depends(get_db)):
    """Return GeoJSON FeatureCollection of all ward polygons."""
    wards = db.query(Ward).filter(Ward.boundary_geojson.isnot(None)).all()
    features = []
    for w in wards:
        features.append({
            "type": "Feature",
            "properties": {
                "ward_id": w.ward_id,
                "ward_name": w.ward_name,
                "ward_number": w.ward_number,
                "circle": w.circle,
                "zone": w.zone,
            },
            "geometry": w.boundary_geojson,
        })
    return {"type": "FeatureCollection", "features": features}


@router.get("/{ward_id}", response_model=WardResponse)
async def get_ward(ward_id: str, db: Session = Depends(get_db)):
    """Get ward detail with stats."""
    ward = db.query(Ward).filter(Ward.ward_id == ward_id).first()
    if not ward:
        raise HTTPException(status_code=404, detail="Ward not found")

    total = db.query(func.count(Ticket.ticket_id)).filter(
        Ticket.ward_id == ward_id, Ticket.moderation_status == "APPROVED"
    ).scalar() or 0
    open_count = db.query(func.count(Ticket.ticket_id)).filter(
        Ticket.ward_id == ward_id, Ticket.status == "OPEN", Ticket.moderation_status == "APPROVED"
    ).scalar() or 0
    resolved = db.query(func.count(Ticket.ticket_id)).filter(
        Ticket.ward_id == ward_id, Ticket.status == "RESOLVED", Ticket.moderation_status == "APPROVED"
    ).scalar() or 0

    return WardResponse(
        ward_id=ward.ward_id,
        ward_name=ward.ward_name,
        ward_number=ward.ward_number,
        circle=ward.circle,
        zone=ward.zone,
        center_lat=ward.center_lat,
        center_lng=ward.center_lng,
        total_reports=total,
        open_reports=open_count,
        resolved_reports=resolved,
    )


@router.get("/{ward_id}/representatives", response_model=List[RepresentativeResponse])
async def get_ward_representatives(ward_id: str, db: Session = Depends(get_db)):
    """Get representatives for a ward."""
    reps = db.query(Representative).filter(
        (Representative.ward_id == ward_id) | (Representative.ward_id.is_(None))
    ).order_by(Representative.level).all()
    return reps
