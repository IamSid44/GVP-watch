"""
Seed Representative / Official Data (prototype phase).

Four levels of responsibility shown per ward:
  1. MLA (zone-wide)
  2. Zonal Commissioner (zone-wide)
  3. Ward Corporator (per ward)
  4. Sanitation Inspector (per ward)

Phone numbers are placeholders (xxx...). Real contact data will be wired up
once the prototype is approved.

Usage:
    cd backend
    python -m data.seed_officials
"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal, Representative, Ward, init_db  # noqa: E402

PLACEHOLDER_PHONE = "+91-xxxxx-xxxxx"

# ---------------------------------------------------------------------------
# Zone-wide officials (no ward_id — visible for every ward in the jurisdiction)
# ---------------------------------------------------------------------------
ZONE_OFFICIALS = [
    {
        "name": "Arekapudi Gandhi",
        "title": "MLA, Serilingampally Constituency",
        "level": "ZONE",
        "party": "BRS",
    },
    {
        "name": "Hemanth Sahadeorao Borkhade IAS",
        "title": "Zonal Commissioner, Serilingampally Zone",
        "level": "ZONE",
        "party": None,
    },
]

# ---------------------------------------------------------------------------
# Ward-level officials
# ---------------------------------------------------------------------------
WARD_OFFICIALS = {
    104: {
        "ward_name": "Kondapur",
        "corporator": "K. Srinivasa Rao",
        "sanitation": "B. Nagaraju",
    },
    105: {
        "ward_name": "Gachibowli",
        "corporator": "G. Padma Latha",
        "sanitation": "T. Ravi Kumar",
    },
    106: {
        "ward_name": "Serilingampally",
        "corporator": "S. Ramaiah Goud",
        "sanitation": "L. Anjaiah",
    },
    111: {
        "ward_name": "Bharathi Nagar",
        "corporator": "M. Venkatesh Reddy",
        "sanitation": "A. Suresh Babu",
    },
}


def seed_officials():
    init_db()
    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        def _add(name, title, level, party=None, ward_id=None):
            nonlocal inserted, skipped
            existing = db.query(Representative).filter(
                Representative.name == name,
                Representative.title == title,
            ).first()
            if existing:
                print(f"[skip] {name} — {title}")
                skipped += 1
                return
            rep = Representative(
                name=name,
                title=title,
                level=level,
                party=party,
                phone=PLACEHOLDER_PHONE,
                email=None,
                ward_id=ward_id,
            )
            db.add(rep)
            inserted += 1
            print(f"[add]  {name} — {title}")

        # Zone-wide officials
        for o in ZONE_OFFICIALS:
            _add(o["name"], o["title"], o["level"], party=o.get("party"))

        # Ward officials
        wards_by_num = {w.ward_number: w for w in db.query(Ward).all()}
        for ward_num, info in WARD_OFFICIALS.items():
            ward = wards_by_num.get(ward_num)
            ward_id = ward.ward_id if ward else None
            ward_name = info["ward_name"]

            _add(
                info["corporator"],
                f"Ward Corporator, Ward {ward_num} ({ward_name})",
                "WARD",
                ward_id=ward_id,
            )
            _add(
                info["sanitation"],
                f"Sanitation Inspector, Ward {ward_num} ({ward_name})",
                "WARD",
                ward_id=ward_id,
            )

        db.commit()
        print(f"\n[done] Inserted {inserted} official(s), skipped {skipped} duplicate(s).")

    except Exception as exc:
        db.rollback()
        print(f"[error] {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_officials()
