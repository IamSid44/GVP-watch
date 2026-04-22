"""
Seed wards 104-110 from the local ghmc_wards.geojson file.

Usage:
    cd backend
    python -m data.seed_wards_local
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

GEOJSON_PATH = BACKEND_DIR.parent / "ghmc_wards.geojson"

TARGET_WARDS = {104, 105, 106, 111}

# Friendly names from ward_info.txt
WARD_NAMES = {
    104: "Kondapur",
    105: "Gachibowli",
    106: "Serilingampally",
    111: "Bharathi Nagar",
}

from database import SessionLocal, Ward, init_db  # noqa: E402


def _centroid(geometry: dict) -> tuple[float, float]:
    """Average of all exterior ring vertices."""
    coords: list[list[float]] = []
    if geometry["type"] == "Polygon":
        coords = geometry["coordinates"][0]
    elif geometry["type"] == "MultiPolygon":
        for poly in geometry["coordinates"]:
            coords.extend(poly[0])
    if not coords:
        return 0.0, 0.0
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return sum(lats) / len(lats), sum(lngs) / len(lngs)


def seed_wards_local():
    init_db()
    db = SessionLocal()

    try:
        with open(GEOJSON_PATH) as f:
            geojson = json.load(f)

        inserted = 0
        skipped = 0

        for feature in geojson["features"]:
            props = feature.get("properties", {})
            ward_str = props.get("ward", "")
            parts = ward_str.split("-", 1)
            if len(parts) < 2:
                continue
            try:
                ward_num = int(parts[0].strip())
            except ValueError:
                continue

            if ward_num not in TARGET_WARDS:
                continue

            ward_name = WARD_NAMES.get(ward_num, parts[1].strip().title())
            circle = props.get("CIRCLE", "")
            zone = props.get("ZONE", "")

            existing = db.query(Ward).filter(Ward.ward_number == ward_num).first()
            if existing:
                print(f"[skip] Ward {ward_num} ({ward_name}) already exists.")
                skipped += 1
                continue

            center_lat, center_lng = _centroid(feature["geometry"])

            ward = Ward(
                ward_id=str(uuid.uuid4()),
                ward_name=ward_name,
                ward_number=ward_num,
                circle=circle,
                zone=zone,
                boundary_geojson=feature["geometry"],
                center_lat=center_lat,
                center_lng=center_lng,
                created_at=datetime.utcnow(),
            )
            db.add(ward)
            inserted += 1
            print(f"[add] Ward {ward_num}: {ward_name}  center=({center_lat:.4f}, {center_lng:.4f})")

        db.commit()
        print(f"\n[done] Inserted {inserted} ward(s), skipped {skipped}.")

    except Exception as e:
        db.rollback()
        print(f"[error] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_wards_local()
