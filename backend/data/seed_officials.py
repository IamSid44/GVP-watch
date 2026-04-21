"""
Seed Representative / Official Data for Serilingampally Zone
-------------------------------------------------------------
Inserts key political and administrative representatives into the
representatives table.

Usage:
    cd backend
    python -m data.seed_officials
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the backend package is importable
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal, Representative, init_db  # noqa: E402

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
OFFICIALS = [
    {
        "name": "Arekapudi Gandhi",
        "title": "MLA, Serilingampally",
        "level": "ZONE",
        "party": "BRS",
        "phone": None,
        "email": None,
        "photo_url": None,
    },
    {
        "name": "Konda Vishweshwar Reddy",
        "title": "MP (Chevella)",
        "level": "CITY",
        "party": "BJP",
        "phone": None,
        "email": None,
        "photo_url": None,
    },
    {
        "name": "Hemanth Sahadeorao Borkhade IAS",
        "title": "Zonal Commissioner",
        "level": "ZONE",
        "party": None,
        "phone": None,
        "email": None,
        "photo_url": None,
    },
]


def seed_officials():
    init_db()
    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        for official in OFFICIALS:
            # Check for duplicate by name + title
            existing = (
                db.query(Representative)
                .filter(
                    Representative.name == official["name"],
                    Representative.title == official["title"],
                )
                .first()
            )
            if existing:
                print(f"[skip] Already exists: {official['name']} - {official['title']}")
                skipped += 1
                continue

            rep = Representative(
                name=official["name"],
                title=official["title"],
                level=official["level"],
                party=official["party"],
                phone=official["phone"],
                email=official["email"],
                photo_url=official["photo_url"],
                ward_id=None,  # zone/city-level reps are not tied to a single ward
            )
            db.add(rep)
            inserted += 1
            print(f"[add]  {official['name']} - {official['title']} ({official['level']})")

        db.commit()
        print(f"\n[done] Inserted {inserted} representative(s), skipped {skipped} duplicate(s).")

    except Exception as exc:
        db.rollback()
        print(f"[error] Database error: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_officials()
