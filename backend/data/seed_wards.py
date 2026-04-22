"""
Seed Ward Data for Serilingampally Zone
----------------------------------------
Fetches GHMC ward boundary relations from the OpenStreetMap Overpass API
for the Serilingampally constituency bounding box, converts OSM relation
geometry to GeoJSON polygons, and inserts Ward records into the database.

Data source: OpenStreetMap contributors, ODbL licence.

Usage:
    cd backend
    python -m data.seed_wards          # normal run
    python -m data.seed_wards --dry    # preview without DB writes
    python -m data.seed_wards --reset  # delete existing wards first, then seed
"""

import json
import math
import sys
import urllib.request
import urllib.parse
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal, Ward, init_db  # noqa: E402

# ---------------------------------------------------------------------------
# Overpass query — all admin-level-10 relations in Serilingampally bbox
# ---------------------------------------------------------------------------
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SERILINGAMPALLY_BBOX = "17.40,78.26,17.55,78.44"  # south,west,north,east

OVERPASS_QUERY = f"""
[out:json][timeout:60];
relation["boundary"="administrative"]["admin_level"="10"]({SERILINGAMPALLY_BBOX});
out geom;
"""

CACHE_PATH = Path(__file__).resolve().parent / "overpass_wards.json"


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def fetch_overpass() -> dict:
    if CACHE_PATH.exists():
        print(f"[info] Loading cached Overpass data from {CACHE_PATH}")
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[info] Querying Overpass API for Serilingampally wards…")
    encoded = urllib.parse.urlencode({"data": OVERPASS_QUERY})
    url = f"{OVERPASS_URL}?{encoded}"
    req = urllib.request.Request(url, headers={"User-Agent": "GVP-Watch/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        raw = resp.read().decode("utf-8")

    data = json.loads(raw)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        f.write(raw)
    print(f"[info] Cached Overpass response to {CACHE_PATH}")
    return data


# ---------------------------------------------------------------------------
# OSM relation → GeoJSON geometry
# ---------------------------------------------------------------------------

def _pt_dist2(a, b):
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2


def assemble_ring(outer_ways: list) -> list:
    """
    Assemble a list of way-geometry arrays (each [{lat, lon}, …]) into a
    single closed GeoJSON ring [[lng, lat], …].

    Uses a greedy nearest-endpoint chain algorithm that handles ways given
    in arbitrary order and orientation.
    """
    # Convert each way to a [lng, lat] segment
    segments = [[[p["lon"], p["lat"]] for p in w["geometry"]] for w in outer_ways]

    if not segments:
        return []

    ring = list(segments[0])
    used = {0}

    while len(used) < len(segments):
        end = ring[-1]
        best_i, best_rev, best_d = None, False, math.inf

        for i, seg in enumerate(segments):
            if i in used:
                continue
            d_fwd = _pt_dist2(seg[0], end)
            d_rev = _pt_dist2(seg[-1], end)
            if d_fwd < best_d:
                best_d, best_i, best_rev = d_fwd, i, False
            if d_rev < best_d:
                best_d, best_i, best_rev = d_rev, i, True

        seg = segments[best_i]
        if best_rev:
            seg = seg[::-1]
        ring.extend(seg[1:])   # drop first point; it's the same as current tail
        used.add(best_i)

    # Close ring
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    return ring


def relation_to_geojson(element: dict) -> dict | None:
    """Convert an OSM relation element (with embedded geometry) to a GeoJSON geometry."""
    outer = [m for m in element.get("members", [])
             if m.get("role") == "outer" and m.get("geometry")]
    inner = [m for m in element.get("members", [])
             if m.get("role") == "inner" and m.get("geometry")]

    if not outer:
        return None

    # Group outer ways into separate rings (a relation can have multiple outer rings
    # if it's a MultiPolygon — e.g. a ward with a detached enclave).
    # Simple heuristic: if the outer ways form one continuous chain → Polygon;
    # otherwise build each disjoint chain as a separate ring → MultiPolygon.
    outer_ring = assemble_ring(outer)
    if not outer_ring:
        return None

    rings = [outer_ring]
    for m in inner:
        hole = assemble_ring([m])
        if hole:
            rings.append(hole)

    return {"type": "Polygon", "coordinates": rings}


def compute_centroid(geometry: dict) -> tuple[float, float]:
    """Arithmetic centroid of all coordinate points. Returns (lat, lng)."""
    coords = geometry["coordinates"]

    def flatten(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for item in c:
                yield from flatten(item)

    pts = list(flatten(coords))
    if not pts:
        return 0.0, 0.0
    return (
        sum(p[1] for p in pts) / len(pts),
        sum(p[0] for p in pts) / len(pts),
    )


# ---------------------------------------------------------------------------
# Ward-number extraction
# ---------------------------------------------------------------------------

def extract_ward_number(name: str) -> int | None:
    """'Ward 106 Serilingampally' → 106"""
    import re
    m = re.search(r"\b(\d+)\b", name)
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------

def seed_wards(dry_run: bool = False, reset: bool = False):
    data = fetch_overpass()
    elements = data.get("elements", [])
    print(f"[info] Overpass returned {len(elements)} relation(s)")

    if not elements:
        print("[error] No elements returned. Check the Overpass query or bbox.")
        return

    init_db()
    db = SessionLocal()

    try:
        if reset:
            deleted = db.query(Ward).delete()
            db.commit()
            print(f"[reset] Deleted {deleted} existing ward(s).")

        inserted = skipped = errors = 0

        for el in elements:
            tags = el.get("tags", {})
            name = tags.get("name", "").strip()
            if not name:
                continue

            geometry = relation_to_geojson(el)
            if geometry is None:
                print(f"[warn] Could not build geometry for: {name}")
                errors += 1
                continue

            center_lat, center_lng = compute_centroid(geometry)
            ward_number = extract_ward_number(name)

            if dry_run:
                print(f"  [dry] {name}  #{ward_number}  "
                      f"center=({center_lat:.5f}, {center_lng:.5f})  "
                      f"pts={len(geometry['coordinates'][0])}")
                inserted += 1
                continue

            existing = db.query(Ward).filter(Ward.ward_name == name).first()
            if existing:
                # Update geometry in case it improved
                existing.boundary_geojson = geometry
                existing.center_lat = center_lat
                existing.center_lng = center_lng
                if ward_number:
                    existing.ward_number = ward_number
                print(f"[upd]  {name}")
                skipped += 1
            else:
                ward = Ward(
                    ward_name=name,
                    ward_number=ward_number,
                    zone="Serilingampally",
                    boundary_geojson=geometry,
                    center_lat=center_lat,
                    center_lng=center_lng,
                )
                db.add(ward)
                print(f"[add]  {name}  #{ward_number}  "
                      f"center=({center_lat:.5f}, {center_lng:.5f})")
                inserted += 1

        if not dry_run:
            db.commit()

        action = "Would insert" if dry_run else "Inserted"
        print(f"\n[done] {action} {inserted}, updated {skipped}, "
              f"failed {errors}  (total={len(elements)})")

    except Exception as exc:
        db.rollback()
        print(f"[error] {exc}")
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    dry = "--dry" in sys.argv
    reset = "--reset" in sys.argv
    seed_wards(dry_run=dry, reset=reset)
