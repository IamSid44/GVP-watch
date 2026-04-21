"""
Seed sample reports for demo purposes.
Creates sample garbage reports scattered across Serilingampally zone.

Usage:
    cd backend
    python -m data.seed_reports
"""

import sys
import uuid
import random
from pathlib import Path
from datetime import datetime, timedelta

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal, Ward, Ticket, User, ActionLog, init_db  # noqa: E402

# Sample locations in Serilingampally zone (lat, lng, area_name)
SAMPLE_LOCATIONS = [
    (17.4939, 78.3158, "Gachibowli Main Road"),
    (17.4871, 78.3312, "HITEC City Metro Station"),
    (17.5000, 78.3050, "Kondapur Junction"),
    (17.4760, 78.3400, "Madhapur Flyover"),
    (17.4650, 78.3250, "Raidurgam"),
    (17.4980, 78.2890, "Miyapur X Roads"),
    (17.4810, 78.3500, "Jubilee Hills Check Post"),
    (17.5100, 78.3200, "Madinaguda Main Road"),
    (17.4700, 78.3700, "Banjara Hills Road No 12"),
    (17.4590, 78.3600, "Film Nagar"),
    (17.5200, 78.2800, "Chandanagar"),
    (17.4450, 78.3800, "Puppalguda"),
    (17.4300, 78.3500, "Narsingi"),
    (17.4200, 78.3600, "Kokapet"),
    (17.4100, 78.3700, "Gandipet"),
    (17.5300, 78.2900, "Hafeezpet"),
    (17.4850, 78.2700, "Nallagandla"),
    (17.4950, 78.3350, "Sriram Nagar"),
    (17.4780, 78.3150, "Ayyappa Society"),
    (17.4620, 78.3450, "Khajaguda"),
    (17.4680, 78.3300, "Financial District"),
    (17.5050, 78.3100, "Kothaguda"),
    (17.4890, 78.2850, "Gopanpally"),
]

CATEGORIES = [
    "garbage_on_roads",
    "overflowing_bins",
    "construction_debris",
    "drain_blockage",
    "green_waste",
    "other",
]

SEVERITIES = ["LOW", "MEDIUM", "HIGH"]
# Weighted toward OPEN so there are active hotspots
STATUSES = ["OPEN", "OPEN", "OPEN", "OPEN", "RESOLVED", "PENDING_VERIFICATION"]

DESCRIPTIONS = [
    "Large pile of garbage dumped on the roadside, blocking pedestrian path.",
    "Overflowing garbage bin near the park, bad odor and flies everywhere.",
    "Construction debris abandoned on the main road for several weeks.",
    "Mixed waste dump near the apartment complex gate.",
    "Garbage not collected for 5 days, residents complaining.",
    "Plastic bags and household waste scattered near the bus stop.",
    "Clogged drain with garbage causing waterlogging during rain.",
    "Green waste from tree cutting left blocking the footpath.",
    "Illegal dumping of household waste near the vacant plot.",
    "Overflowing bin near the school causing health concerns.",
]


def seed_reports(count: int = 23):
    init_db()
    db = SessionLocal()

    try:
        existing = db.query(Ticket).filter(Ticket.source == "SEED").count()
        if existing > 0:
            print(f"[info] {existing} seed reports already exist. Skipping.")
            return

        wards = db.query(Ward).all()
        seeded = 0

        random.seed(42)
        for i in range(min(count, len(SAMPLE_LOCATIONS))):
            lat, lng, area = SAMPLE_LOCATIONS[i]
            severity = random.choice(SEVERITIES)
            status = random.choice(STATUSES)
            category = random.choice(CATEGORIES)
            description = random.choice(DESCRIPTIONS)
            days_ago = random.randint(0, 14)
            created_at = datetime.utcnow() - timedelta(
                days=days_ago, hours=random.randint(0, 23)
            )

            # Find nearest ward if any exist
            ward = None
            if wards:
                best, best_dist = None, float("inf")
                for w in wards:
                    if w.center_lat and w.center_lng:
                        d = (w.center_lat - lat) ** 2 + (w.center_lng - lng) ** 2
                        if d < best_dist:
                            best_dist, best = d, w
                ward = best

            phone = f"seed-{uuid.uuid4().hex[:12]}"
            user = User(
                user_id=str(uuid.uuid4()),
                phone=phone,
                role="CITIZEN",
                name=f"Resident #{i + 1}",
                created_at=created_at,
            )
            db.add(user)
            db.flush()

            ticket_id = f"tk-{uuid.uuid4().hex[:8]}"
            resolved_at = (
                created_at + timedelta(days=random.randint(1, 3))
                if status == "RESOLVED"
                else None
            )

            ticket = Ticket(
                ticket_id=ticket_id,
                citizen_phone=phone,
                ward_id=ward.ward_id if ward else None,
                latitude=lat,
                longitude=lng,
                severity_score=severity,
                status=status,
                source="SEED",
                description=description,
                category=category,
                address=area,
                reporter_name=f"Resident #{i + 1}",
                upvote_count=random.randint(0, 15),
                moderation_status="APPROVED",
                created_at=created_at,
                resolved_at=resolved_at,
            )
            db.add(ticket)

            action = ActionLog(
                action_log_id=str(uuid.uuid4()),
                ticket_id=ticket_id,
                action_type="STATUS_CHANGE",
                old_status=None,
                new_status=status,
                actor="system",
                notes={"source": "SEED"},
                created_at=created_at,
            )
            db.add(action)
            seeded += 1

        db.commit()
        print(f"[done] Seeded {seeded} sample reports.")

    except Exception as e:
        db.rollback()
        print(f"[error] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_reports()
