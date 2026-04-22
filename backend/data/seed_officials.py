"""
Seed Representative / Official Data for Serilingampally Zone (wards 104-110).

Inserts:
  - Zone-level: MLA, MP, Zonal Commissioner
  - Circle-level: two Circle Officers
  - Ward-level: Corporator + Sanitation Inspector for each of the 7 wards

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

# ---------------------------------------------------------------------------
# Zone / City level — not tied to a specific ward
# ---------------------------------------------------------------------------
ZONE_OFFICIALS = [
    {
        "name": "Arekapudi Gandhi",
        "title": "MLA, Serilingampally Constituency",
        "level": "ZONE",
        "party": "BRS",
        "phone": "+91-40-23452345",
        "email": "mla.serilingampally@telangana.gov.in",
    },
    {
        "name": "Konda Vishweshwar Reddy",
        "title": "Member of Parliament, Chevella",
        "level": "CITY",
        "party": "BJP",
        "phone": "+91-11-23034567",
        "email": "mp.chevella@parliament.gov.in",
    },
    {
        "name": "Hemanth Sahadeorao Borkhade IAS",
        "title": "Zonal Commissioner, Serilingampally Zone",
        "level": "ZONE",
        "party": None,
        "phone": "+91-40-23120100",
        "email": "zc.serilingampally@ghmc.gov.in",
    },
]

# ---------------------------------------------------------------------------
# Circle level — two circles cover the zone
# ---------------------------------------------------------------------------
CIRCLE_OFFICIALS = [
    {
        "name": "P. Venkat Ramana",
        "title": "Circle Officer, Serilingampally Circle (20)",
        "level": "CIRCLE",
        "party": None,
        "phone": "+91-40-23118820",
        "email": "co.circle20@ghmc.gov.in",
        "circle": "20-SERILINGAMPALLY",
    },
    {
        "name": "M. Rajeshwari Devi",
        "title": "Circle Officer, Chanda Nagar Circle (21)",
        "level": "CIRCLE",
        "party": None,
        "phone": "+91-40-23118821",
        "email": "co.circle21@ghmc.gov.in",
        "circle": "21-CHANDA NAGAR",
    },
]

# ---------------------------------------------------------------------------
# Ward level — Corporator + Sanitation Inspector for each ward
# ---------------------------------------------------------------------------
WARD_OFFICIALS = {
    104: {
        "ward_name": "Kondapur",
        "corporator": ("K. Srinivasa Rao", "+91-98480-10104"),
        "sanitation": ("B. Nagaraju", "+91-98480-20104"),
    },
    105: {
        "ward_name": "Gachibowli",
        "corporator": ("G. Padma Latha", "+91-98480-10105"),
        "sanitation": ("T. Ravi Kumar", "+91-98480-20105"),
    },
    106: {
        "ward_name": "Serilingampally",
        "corporator": ("S. Ramaiah Goud", "+91-98480-10106"),
        "sanitation": ("L. Anjaiah", "+91-98480-20106"),
    },
    111: {
        "ward_name": "Bharathi Nagar",
        "corporator": ("M. Venkatesh Reddy", "+91-98480-10111"),
        "sanitation": ("A. Suresh Babu", "+91-98480-20111"),
    },
}


def seed_officials():
    init_db()
    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0

        def _add(name, title, level, party=None, phone=None, email=None, ward_id=None):
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
                phone=phone,
                email=email,
                ward_id=ward_id,
            )
            db.add(rep)
            inserted += 1
            print(f"[add]  {name} — {title}")

        # Zone / City officials (no ward_id)
        for o in ZONE_OFFICIALS:
            _add(o["name"], o["title"], o["level"],
                 party=o.get("party"), phone=o.get("phone"), email=o.get("email"))

        # Circle officials (no ward_id — shown zone-wide)
        for o in CIRCLE_OFFICIALS:
            _add(o["name"], o["title"], o["level"],
                 phone=o.get("phone"), email=o.get("email"))

        # Ward officials — look up ward_id from DB
        wards_by_num = {w.ward_number: w for w in db.query(Ward).all()}

        for ward_num, info in WARD_OFFICIALS.items():
            ward = wards_by_num.get(ward_num)
            ward_id = ward.ward_id if ward else None
            ward_name = info["ward_name"]

            corp_name, corp_phone = info["corporator"]
            _add(
                corp_name,
                f"Ward Corporator, Ward {ward_num} ({ward_name})",
                "WARD",
                phone=corp_phone,
                ward_id=ward_id,
            )

            san_name, san_phone = info["sanitation"]
            _add(
                san_name,
                f"Sanitation Inspector, Ward {ward_num} ({ward_name})",
                "WARD",
                phone=san_phone,
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
