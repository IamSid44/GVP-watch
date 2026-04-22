"""
Comprehensive demo seed: 50 reports across Serilingampally zone (wards 104-110).

- Severity distribution: ~30% HIGH, ~40% MEDIUM, ~30% LOW
- Status mix: OPEN, PENDING_VERIFICATION, RESOLVED, UNRESPONSIVE
- All 6 categories represented
- Clustered hotspots near key landmarks for visible map density
- Uses source="SEED" so normal seed check still works

Usage:
    cd backend
    python -m data.seed_demo
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

# ---------------------------------------------------------------------------
# Locations spread across wards 104-110 (Serilingampally zone)
# Format: (lat, lng, area_name, ward_hint)
# ---------------------------------------------------------------------------
DEMO_LOCATIONS = [
    # Ward 104 – Gachibowli / Financial District area
    (17.4410, 78.3480, "Gachibowli Stadium Junction", 104),
    (17.4385, 78.3520, "DLF Cyber City Gate 2", 104),
    (17.4360, 78.3550, "Financial District Flyover", 104),
    (17.4430, 78.3440, "Gachibowli Police Station", 104),
    (17.4470, 78.3390, "Gachibowli Main Road Median", 104),

    # Ward 105 – Madhapur / HITEC City
    (17.4490, 78.3840, "Madhapur Petrol Pump", 105),
    (17.4520, 78.3780, "HITEC City Metro Gate 3", 105),
    (17.4540, 78.3720, "Madhapur Cross Roads", 105),
    (17.4460, 78.3900, "Cyber Towers Roundabout", 105),
    (17.4480, 78.3860, "Madhapur Bus Depot", 105),

    # Ward 106 – Kondapur / Kothaguda
    (17.4690, 78.3600, "Kondapur Main Road", 106),
    (17.4710, 78.3570, "Kothaguda Junction", 106),
    (17.4730, 78.3540, "Kondapur Park Lane", 106),
    (17.4660, 78.3640, "ISB Road Kondapur", 106),
    (17.4680, 78.3620, "Kondapur Petrol Bunk", 106),

    # Ward 107 – Miyapur / Hafeezpet
    (17.4970, 78.3540, "Miyapur X Roads", 107),
    (17.4990, 78.3500, "Hafeezpet Main Road", 107),
    (17.5010, 78.3470, "Miyapur Auto Nagar", 107),
    (17.5030, 78.3440, "Hafeezpet Colony", 107),
    (17.4950, 78.3570, "Miyapur MMTS Bridge", 107),

    # Ward 108 – Chandanagar / Madinaguda
    (17.5100, 78.3230, "Chandanagar Main Road", 108),
    (17.5120, 78.3200, "Madinaguda Junction", 108),
    (17.5080, 78.3260, "Chandanagar Overhead Tank", 108),
    (17.5140, 78.3170, "Madinaguda Bus Stand", 108),
    (17.5060, 78.3290, "Chandanagar Police Quarters", 108),

    # Ward 109 – Nallagandla / Gopanpally
    (17.4830, 78.3110, "Nallagandla Lake Road", 109),
    (17.4850, 78.3070, "Gopanpally Main Road", 109),
    (17.4810, 78.3150, "Nallagandla Bypass", 109),
    (17.4870, 78.3040, "Gopanpally Colony", 109),
    (17.4790, 78.3200, "Nallagandla Crossroads", 109),

    # Ward 110 – Narsingi / Kokapet
    (17.4280, 78.3530, "Narsingi Junction", 110),
    (17.4260, 78.3560, "Kokapet Main Road", 110),
    (17.4300, 78.3500, "Narsingi Industrial Area", 110),
    (17.4240, 78.3590, "Kokapet Residential Gate", 110),
    (17.4320, 78.3470, "Narsingi Bus Stop", 110),

    # Dense hotspot cluster – Gachibowli (for visible clustering demo)
    (17.4395, 78.3475, "Gachibowli Outer Ring Road", 104),
    (17.4405, 78.3465, "Near Gachibowli Flyover", 104),
    (17.4415, 78.3455, "Gachibowli Bowl Area", 104),

    # Dense hotspot cluster – HITEC City center
    (17.4500, 78.3810, "HITEC City Central Plaza", 105),
    (17.4510, 78.3800, "HITEC City Phase 2", 105),

    # Dense hotspot cluster – Kondapur market
    (17.4700, 78.3580, "Kondapur Market", 106),
    (17.4715, 78.3565, "Kondapur Vegetable Mkt", 106),

    # Scattered filler
    (17.4580, 78.3350, "Raidurgam Park", 106),
    (17.4600, 78.3300, "Raidurgam Junction", 106),
    (17.4790, 78.3390, "Jubilee Hills Road 45", 105),
    (17.4820, 78.3360, "Jubilee Hills Check Post", 105),
    (17.5160, 78.3140, "Madinaguda Residential", 108),
    (17.4900, 78.3290, "Serilingampally Circle", 107),
    (17.4920, 78.3260, "Lingampally Station Rd", 107),
    (17.4940, 78.3230, "Lingampally Colony", 107),
]

CATEGORIES = [
    "garbage_on_roads",
    "overflowing_bins",
    "construction_debris",
    "drain_blockage",
    "green_waste",
    "other",
]

DESCRIPTIONS = {
    "garbage_on_roads": [
        "Large pile of mixed waste dumped on the footpath, completely blocking pedestrian access.",
        "Household garbage bags strewn across the road near the bus stop, creating a health hazard.",
        "Garbage scattered by stray dogs overnight — spread over 30 metres of road.",
        "Trash dumped at the turn, vehicles have to swerve around it.",
        "Waste pile near the school gate — strong foul odour in the area.",
    ],
    "overflowing_bins": [
        "Municipal bin overflowing for 4 days. Flies and mosquitoes breeding in standing water.",
        "Bin capacity far exceeded; waste piled 2 ft above the bin lid.",
        "Community bin not emptied since weekend. Residents approaching corporation officials.",
        "Overflow bin attracting stray cattle and dogs to the residential lane.",
        "Garbage bin near the park hasn't been collected — strong smell affecting nearby shops.",
    ],
    "construction_debris": [
        "Construction sand and bricks dumped on the service road, narrowing it to one lane.",
        "Debris from building renovation abandoned at the junction for two weeks.",
        "Cement bags and iron rods blocking the footpath near the apartment complex.",
        "Illegal rubble dumping on the roadside — contractor abandoned materials overnight.",
        "Broken tiles and plaster waste piled at the lane corner without any clearance.",
    ],
    "drain_blockage": [
        "Storm drain choked with plastic bags; water overflowing into the road.",
        "Clogged drain causing waterlogging after last night's rain; vehicles stuck.",
        "Drain blocked with silt and solid waste — overflow reaching ground floor shops.",
        "Manhole covered with debris; slow drainage causing mosquito breeding.",
        "Open drain packed with garbage, causing foul smell and seepage into adjacent plot.",
    ],
    "green_waste": [
        "Tree branches from last week's storm still blocking half the road.",
        "Municipality tree-trimming waste left on footpath for 6 days.",
        "Fallen coconut fronds blocking the side lane near the temple.",
        "Large tree branch broke off and has not been cleared from the roadside.",
        "Lawn clippings and garden waste dumped on the open plot by local contractor.",
    ],
    "other": [
        "Illegal slaughterhouse waste dumped in the open area at night.",
        "Industrial waste bags deposited near the residential colony boundary wall.",
        "Dead animal carcass left near the nala — urgent health concern.",
        "Chemical drums abandoned near the water body — potential contamination risk.",
        "Old furniture and appliances dumped blocking emergency vehicle access.",
    ],
}

# Severity weights: realistic urban distribution (~20% LOW, 48% MEDIUM, 32% HIGH)
SEVERITY_WEIGHTS = ["LOW"] * 5 + ["MEDIUM"] * 12 + ["HIGH"] * 8

# Status weights: mostly OPEN for an active dashboard look
STATUS_WEIGHTS = (
    ["OPEN"] * 18
    + ["PENDING_VERIFICATION"] * 6
    + ["RESOLVED"] * 8
    + ["UNRESPONSIVE"] * 3
)

REPORTER_NAMES = [
    "Rajesh Kumar", "Priya Reddy", "Mohammed Farooq", "Sunita Sharma",
    "Venkat Rao", "Lakshmi Devi", "Suresh Nair", "Anita Patel",
    "Ravi Shankar", "Deepa Chowdary", "Arun Babu", "Meena Iyer",
    "Sanjay Gupta", "Kavitha Raju", "Naresh Goud", "Sneha Pillai",
    "Ramesh Tiwari", "Usha Rani", "Vishal Shetty", "Padma Latha",
]


def seed_demo(count: int = 50):
    init_db()
    db = SessionLocal()

    try:
        existing = db.query(Ticket).filter(Ticket.source == "SEED").count()
        if existing > 0:
            print(f"[info] {existing} SEED reports already exist. Clearing and re-seeding...")
            from database import ActionLog as AL, MessageLog as ML
            seed_tickets = db.query(Ticket).filter(Ticket.source == "SEED").all()
            for t in seed_tickets:
                db.query(AL).filter(AL.ticket_id == t.ticket_id).delete()
                db.query(ML).filter(ML.ticket_id == t.ticket_id).delete()
            seed_phones = [t.citizen_phone for t in seed_tickets if t.citizen_phone.startswith("seed-")]
            db.query(Ticket).filter(Ticket.source == "SEED").delete()
            for phone in seed_phones:
                db.query(User).filter(User.phone == phone).delete()
            db.commit()

        wards = db.query(Ward).all()
        seeded = 0
        locations = DEMO_LOCATIONS[:count]
        random.seed(99)

        for i, (lat, lng, area, ward_hint) in enumerate(locations):
            severity = random.choice(SEVERITY_WEIGHTS)
            status = random.choice(STATUS_WEIGHTS)
            category = random.choice(CATEGORIES)
            description = random.choice(DESCRIPTIONS[category])
            days_ago = random.randint(0, 21)
            hours_ago = random.randint(0, 23)
            created_at = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)

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
            reporter = random.choice(REPORTER_NAMES)
            user = User(
                user_id=str(uuid.uuid4()),
                phone=phone,
                role="CITIZEN",
                name=reporter,
                created_at=created_at,
            )
            db.add(user)
            db.flush()

            ticket_id = f"tk-{uuid.uuid4().hex[:8]}"
            resolved_at = None
            if status == "RESOLVED":
                resolved_at = created_at + timedelta(days=random.randint(1, 4))
            elif status == "UNRESPONSIVE":
                resolved_at = created_at + timedelta(days=random.randint(3, 7))

            if severity == "HIGH":
                upvotes = random.randint(5, 30)
            elif severity == "MEDIUM":
                upvotes = random.randint(1, 12)
            else:
                upvotes = random.randint(0, 5)

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
                reporter_name=reporter,
                upvote_count=upvotes,
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
                notes={"source": "SEED_DEMO"},
                created_at=created_at,
            )
            db.add(action)
            seeded += 1

        db.commit()

        sev_counts = {}
        for sev in ["LOW", "MEDIUM", "HIGH"]:
            sev_counts[sev] = db.query(Ticket).filter(
                Ticket.source == "SEED", Ticket.severity_score == sev
            ).count()
        status_counts = {}
        for st in ["OPEN", "PENDING_VERIFICATION", "RESOLVED", "UNRESPONSIVE"]:
            status_counts[st] = db.query(Ticket).filter(
                Ticket.source == "SEED", Ticket.status == st
            ).count()

        print(f"\n[done] Seeded {seeded} demo reports.\n")
        print("Severity breakdown:")
        for k, v in sev_counts.items():
            print(f"  {k:8s} {v:3d}  {'█' * v}")
        print("\nStatus breakdown:")
        for k, v in status_counts.items():
            print(f"  {k:25s} {v:3d}  {'█' * v}")

    except Exception as e:
        db.rollback()
        print(f"[error] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()