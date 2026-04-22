"""
Comprehensive demo seed: 250 reports within wards 104, 105, 106, 111.

Points are generated randomly inside each ward polygon using a ray-casting
point-in-polygon test so all markers appear strictly within the jurisdiction.

Distribution:
  Ward 104 (Kondapur)        ~75 points
  Ward 105 (Gachibowli)      ~80 points
  Ward 106 (Serilingampally) ~75 points
  Ward 111 (Bharathi Nagar)  ~20 points  (tiny strip ~700m × 180m)

Usage:
    cd backend
    python -m data.seed_demo
"""

import sys
import json
import uuid
import random
from pathlib import Path
from datetime import datetime, timedelta

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

GEOJSON_PATH = BACKEND_DIR.parent / "ghmc_wards.geojson"

from database import SessionLocal, Ward, Ticket, User, ActionLog, init_db  # noqa: E402

# ---------------------------------------------------------------------------
# Ward config — number → (target_count, area_name_examples)
# ---------------------------------------------------------------------------
TARGET_WARDS_CONFIG = {
    104: {"count": 75,  "name": "Kondapur"},
    105: {"count": 80,  "name": "Gachibowli"},
    106: {"count": 75,  "name": "Serilingampally"},
    111: {"count": 20,  "name": "Bharathi Nagar"},
}

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
        "Trash dumped at the junction, vehicles have to swerve around it.",
        "Waste pile near the school gate — strong foul odour in the area.",
        "Rotting organic waste and plastic mixed together near the apartment complex.",
        "Street corner turned into an illegal dumping spot for weeks.",
    ],
    "overflowing_bins": [
        "Municipal bin overflowing for 4 days. Flies and mosquitoes breeding in standing water.",
        "Bin capacity far exceeded; waste piled 2 ft above the bin lid.",
        "Community bin not emptied since the weekend. Residents approaching corporation officials.",
        "Overflow bin attracting stray cattle and dogs to the residential lane.",
        "Garbage bin near the park hasn't been collected — strong smell affecting nearby shops.",
        "Two bins in this area have been overflowing since Monday with no response.",
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
        "Children's park next to blocked nala has become unusable due to waterlogging.",
    ],
    "green_waste": [
        "Tree branches from last week's storm still blocking half the road.",
        "Municipality tree-trimming waste left on footpath for 6 days.",
        "Fallen coconut fronds blocking the side lane near the temple.",
        "Large tree branch broke off and has not been cleared from the roadside.",
        "Lawn clippings and garden waste dumped on the open plot by a local contractor.",
    ],
    "other": [
        "Illegal slaughterhouse waste dumped in the open area at night.",
        "Industrial waste bags deposited near the residential colony boundary wall.",
        "Dead animal carcass left near the nala — urgent health concern.",
        "Chemical drums abandoned near the water body — potential contamination risk.",
        "Old furniture and appliances dumped blocking emergency vehicle access.",
    ],
}

# Realistic severity distribution
SEVERITY_WEIGHTS = ["LOW"] * 5 + ["MEDIUM"] * 12 + ["HIGH"] * 8

# Mostly OPEN, with some resolved and pending for variety
STATUS_WEIGHTS = (
    ["OPEN"] * 18
    + ["PENDING_VERIFICATION"] * 5
    + ["RESOLVED"] * 9
    + ["UNRESPONSIVE"] * 3
)

REPORTER_NAMES = [
    "Rajesh Kumar", "Priya Reddy", "Mohammed Farooq", "Sunita Sharma",
    "Venkat Rao", "Lakshmi Devi", "Suresh Nair", "Anita Patel",
    "Ravi Shankar", "Deepa Chowdary", "Arun Babu", "Meena Iyer",
    "Sanjay Gupta", "Kavitha Raju", "Naresh Goud", "Sneha Pillai",
    "Ramesh Tiwari", "Usha Rani", "Vishal Shetty", "Padma Latha",
    "Krishna Murthy", "Sudha Rani", "Bhaskar Reddy", "Hema Latha",
    "Ganesh Babu", "Rekha Sharma", "Sunil Kumar", "Nirmala Devi",
    "Pavan Kalyan", "Saritha Reddy",
]

# ---------------------------------------------------------------------------
# Point-in-polygon (ray casting)
# ---------------------------------------------------------------------------

def _point_in_polygon(lat: float, lng: float, ring: list) -> bool:
    """Ray-casting test. ring is list of [lng, lat] pairs."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_feature(lat: float, lng: float, feature: dict) -> bool:
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        return _point_in_polygon(lat, lng, geom["coordinates"][0])
    elif geom["type"] == "MultiPolygon":
        return any(
            _point_in_polygon(lat, lng, poly[0])
            for poly in geom["coordinates"]
        )
    return False


def _bbox(feature: dict) -> tuple:
    geom = feature["geometry"]
    if geom["type"] == "Polygon":
        coords = geom["coordinates"][0]
    else:
        coords = [c for poly in geom["coordinates"] for c in poly[0]]
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return min(lats), max(lats), min(lngs), max(lngs)


def generate_points_in_ward(feature: dict, count: int, rng: random.Random) -> list:
    """Generate random (lat, lng) pairs strictly inside the ward polygon."""
    min_lat, max_lat, min_lng, max_lng = _bbox(feature)
    points = []
    max_attempts = count * 200
    attempts = 0
    while len(points) < count and attempts < max_attempts:
        lat = rng.uniform(min_lat, max_lat)
        lng = rng.uniform(min_lng, max_lng)
        if _point_in_feature(lat, lng, feature):
            points.append((lat, lng))
        attempts += 1
    return points


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed_demo():
    init_db()
    db = SessionLocal()

    try:
        # Clear existing SEED data
        existing = db.query(Ticket).filter(Ticket.source == "SEED").count()
        if existing > 0:
            print(f"[info] Clearing {existing} existing SEED reports...")
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

        # Load ward polygons from GeoJSON
        with open(GEOJSON_PATH) as f:
            geojson = json.load(f)

        ward_features = {}
        for feat in geojson["features"]:
            ward_str = feat["properties"].get("ward", "")
            parts = ward_str.split("-", 1)
            if len(parts) < 2:
                continue
            try:
                num = int(parts[0].strip())
            except ValueError:
                continue
            if num in TARGET_WARDS_CONFIG:
                ward_features[num] = feat

        missing = set(TARGET_WARDS_CONFIG) - set(ward_features)
        if missing:
            print(f"[warn] Ward(s) not found in GeoJSON: {missing}")

        # DB ward lookup by ward_number
        wards_by_num = {w.ward_number: w for w in db.query(Ward).all()}

        rng = random.Random(42)
        seeded = 0

        for ward_num, cfg in sorted(TARGET_WARDS_CONFIG.items()):
            feature = ward_features.get(ward_num)
            if feature is None:
                print(f"[skip] Ward {ward_num} not in GeoJSON.")
                continue

            target_count = cfg["count"]
            ward_label = cfg["name"]
            db_ward = wards_by_num.get(ward_num)

            print(f"[ward {ward_num}] Generating {target_count} points in {ward_label}...")
            points = generate_points_in_ward(feature, target_count, rng)
            if len(points) < target_count:
                print(f"  [warn] Only got {len(points)}/{target_count} points (polygon too small)")

            for lat, lng in points:
                severity = rng.choice(SEVERITY_WEIGHTS)
                status = rng.choice(STATUS_WEIGHTS)
                category = rng.choice(CATEGORIES)
                description = rng.choice(DESCRIPTIONS[category])
                days_ago = rng.randint(0, 28)
                hours_ago = rng.randint(0, 23)
                created_at = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)

                phone = f"seed-{uuid.uuid4().hex[:12]}"
                reporter = rng.choice(REPORTER_NAMES)
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
                    resolved_at = created_at + timedelta(days=rng.randint(1, 4))
                elif status == "UNRESPONSIVE":
                    resolved_at = created_at + timedelta(days=rng.randint(3, 7))

                if severity == "HIGH":
                    upvotes = rng.randint(5, 35)
                elif severity == "MEDIUM":
                    upvotes = rng.randint(1, 15)
                else:
                    upvotes = rng.randint(0, 5)

                ticket = Ticket(
                    ticket_id=ticket_id,
                    citizen_phone=phone,
                    ward_id=db_ward.ward_id if db_ward else None,
                    latitude=lat,
                    longitude=lng,
                    photo_url="/sample_image.jpg",
                    severity_score=severity,
                    status=status,
                    source="SEED",
                    description=description,
                    category=category,
                    address=f"{ward_label} area",
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

        # Summary
        sev_counts = {}
        for sev in ["LOW", "MEDIUM", "HIGH"]:
            sev_counts[sev] = db.query(Ticket).filter(
                Ticket.source == "SEED", Ticket.severity_score == sev
            ).count()
        st_counts = {}
        for st in ["OPEN", "PENDING_VERIFICATION", "RESOLVED", "UNRESPONSIVE"]:
            st_counts[st] = db.query(Ticket).filter(
                Ticket.source == "SEED", Ticket.status == st
            ).count()

        print(f"\n[done] Seeded {seeded} reports across wards 104/105/106/111.\n")
        print("Severity:  " + "  ".join(f"{k}={v}" for k, v in sev_counts.items()))
        print("Status:    " + "  ".join(f"{k}={v}" for k, v in st_counts.items()))

    except Exception as e:
        db.rollback()
        print(f"[error] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
