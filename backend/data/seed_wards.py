"""
Seed Ward Data for Serilingampally Zone
----------------------------------------
Downloads the GHMC ward boundary GeoJSON from datameet/Municipal_Spatial_Data,
filters for Serilingampally-zone wards, computes each ward's centroid, and
inserts Ward records into the database.

Usage:
    cd backend
    python -m data.seed_wards          # normal run
    python -m data.seed_wards --dry    # preview without DB writes
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure the backend package is importable when running as  python -m data.seed_wards
# ---------------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import SessionLocal, Ward, init_db  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GEOJSON_URL = (
    "https://raw.githubusercontent.com/datameet/"
    "Municipal_Spatial_Data/master/Hyderabad/ghmc-wards.geojson"
)
CACHE_PATH = Path(__file__).resolve().parent / "ghmc-wards.geojson"

# Known Serilingampally-zone ward name fragments (case-insensitive).
# These cover the major colonies/areas in the zone regardless of which
# delimitation the GeoJSON uses (old 150-ward or new 150/200 scheme).
SERILINGAMPALLY_NAME_PATTERNS = [
    "gachibowli",
    "nallagandla",
    "serilingampally",
    "serlingampally",
    "serilingampalli",
    "masjid banda",
    "masjid-banda",
    "sriram nagar",
    "sri ram nagar",
    "kondapur",
    "hafeezpet",
    "hafizpet",
    "madeenaguda",
    "madinaguda",
    "chanda nagar",
    "chandanagar",
    "miyapur",
    "hitec city",
    "hi-tech city",
    "hitech city",
    "madhapur",
    "ayyappa society",
    "whitefields",
    "white fields",
    "tellapur",
    "gopanpally",
    "narsingi",
    "kokapet",
    "khajaguda",
    "raidurgam",
    "raidurg",
    "durgam cheruvu",
    "financial district",
    "nanakramguda",
    "puppalguda",
    "manchirevula",
    "kismatpur",
    "rajendranagar",
    "gandipet",
    "budvel",
    "shamshabad",
    "banjara hills",
    "jubilee hills",
    "film nagar",
]

# Fallback: if the GeoJSON carries numeric ward IDs that map to the
# Serilingampally zone under the old 150-ward scheme, these are roughly
# wards 1-18 in the old numbering.  Under the 2020 delimitation the range
# is approximately 127-141 or 225-241 depending on the source.
SERILINGAMPALLY_WARD_RANGES = [
    range(1, 19),       # old 150-ward numbering (zone 1)
    range(127, 151),    # alternate old numbering
    range(225, 242),    # 2020 delimitation numbering
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def download_geojson() -> dict:
    """Download (or load from cache) the full GHMC wards GeoJSON."""
    if CACHE_PATH.exists():
        print(f"[info] Loading cached GeoJSON from {CACHE_PATH}")
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    print(f"[info] Downloading GeoJSON from {GEOJSON_URL} ...")
    req = urllib.request.Request(GEOJSON_URL, headers={"User-Agent": "GVP-Watch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8")

    # Cache locally so subsequent runs are instant
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        f.write(raw)
    print(f"[info] Cached GeoJSON to {CACHE_PATH}")

    return json.loads(raw)


def detect_property_keys(features: list) -> dict:
    """
    Auto-detect the property key names used in the GeoJSON.
    Returns a dict with normalised keys:
        ward_name, ward_no, zone, circle
    mapped to the actual property key strings found in the data.
    """
    if not features:
        raise ValueError("GeoJSON has no features")

    sample_keys = list(features[0]["properties"].keys())
    print(f"[info] GeoJSON property keys: {sample_keys}")

    mapping = {}
    for key in sample_keys:
        kl = key.lower().replace(" ", "_")
        if kl in ("ward_name", "wardname", "ward_na", "name"):
            mapping["ward_name"] = key
        elif kl in ("ward_no", "wardno", "ward_number", "ward_num", "ward_id"):
            mapping["ward_no"] = key
        elif kl in ("zone", "zone_name", "zonename"):
            mapping["zone"] = key
        elif kl in ("circle", "circle_name", "circlename"):
            mapping["circle"] = key

    print(f"[info] Detected property mapping: {mapping}")
    return mapping


def _flatten_coords(coords):
    """Recursively yield all (lng, lat) pairs from a GeoJSON coordinate structure."""
    if isinstance(coords[0], (int, float)):
        yield coords  # single point [lng, lat]
    else:
        for item in coords:
            yield from _flatten_coords(item)


def compute_centroid(geometry: dict) -> tuple:
    """
    Compute a simple centroid (arithmetic mean) of all coordinate points
    in a Polygon or MultiPolygon geometry.
    Returns (lat, lng).
    """
    points = list(_flatten_coords(geometry["coordinates"]))
    if not points:
        return (0.0, 0.0)
    avg_lng = sum(p[0] for p in points) / len(points)
    avg_lat = sum(p[1] for p in points) / len(points)
    return (avg_lat, avg_lng)


def matches_serilingampally(props: dict, key_map: dict) -> bool:
    """
    Return True if this feature belongs to the Serilingampally zone.
    Strategy (in priority order):
      1. If a 'zone' property exists and contains 'serilingampally' -> match.
      2. If the ward name matches any known Serilingampally area name -> match.
      3. If the ward number falls in a known Serilingampally range -> match.
    """
    # --- Strategy 1: zone property ---
    zone_key = key_map.get("zone")
    if zone_key and props.get(zone_key):
        zone_val = str(props[zone_key]).lower()
        if "serilingampally" in zone_val or "serlingampally" in zone_val:
            return True
        # If zone exists but is a different zone, reject immediately
        if zone_val.strip():
            return False

    # --- Strategy 2: name matching ---
    name_key = key_map.get("ward_name")
    if name_key and props.get(name_key):
        name_val = str(props[name_key]).lower()
        for pattern in SERILINGAMPALLY_NAME_PATTERNS:
            if pattern in name_val:
                return True

    # --- Strategy 3: ward number range ---
    no_key = key_map.get("ward_no")
    if no_key and props.get(no_key):
        try:
            ward_num = int(props[no_key])
            for r in SERILINGAMPALLY_WARD_RANGES:
                if ward_num in r:
                    return True
        except (ValueError, TypeError):
            pass

    return False


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------

def seed_wards(dry_run: bool = False):
    geojson = download_geojson()
    features = geojson.get("features", [])
    print(f"[info] Total features in GeoJSON: {len(features)}")

    if not features:
        print("[error] No features found in GeoJSON. Aborting.")
        return

    # Print a few sample properties for debugging
    for i, f in enumerate(features[:3]):
        print(f"[debug] Feature {i} properties: {json.dumps(f['properties'], indent=2)}")

    key_map = detect_property_keys(features)

    # Filter for Serilingampally
    serilingampally_features = []
    for feat in features:
        if matches_serilingampally(feat["properties"], key_map):
            serilingampally_features.append(feat)

    print(f"[info] Matched {len(serilingampally_features)} Serilingampally ward(s)")

    if not serilingampally_features:
        print("[warn] No Serilingampally wards matched. Listing all ward names for debugging:")
        name_key = key_map.get("ward_name", "")
        for feat in features:
            name = feat["properties"].get(name_key, "?")
            no_key = key_map.get("ward_no", "")
            num = feat["properties"].get(no_key, "?")
            print(f"        Ward {num}: {name}")
        return

    if dry_run:
        print("\n[dry-run] Would insert the following wards:")
        for feat in serilingampally_features:
            props = feat["properties"]
            name = props.get(key_map.get("ward_name", ""), "Unknown")
            num = props.get(key_map.get("ward_no", ""), None)
            lat, lng = compute_centroid(feat["geometry"])
            print(f"    Ward {num}: {name}  center=({lat:.6f}, {lng:.6f})")
        return

    # Database insertion
    init_db()
    db = SessionLocal()

    try:
        inserted = 0
        skipped = 0
        for feat in serilingampally_features:
            props = feat["properties"]
            ward_name = str(props.get(key_map.get("ward_name", ""), "Unknown")).strip()
            ward_no_raw = props.get(key_map.get("ward_no", ""), None)
            circle_val = props.get(key_map.get("circle", ""), None)
            center_lat, center_lng = compute_centroid(feat["geometry"])

            ward_number = None
            if ward_no_raw is not None:
                try:
                    ward_number = int(ward_no_raw)
                except (ValueError, TypeError):
                    pass

            # Skip if a ward with the same name already exists
            existing = db.query(Ward).filter(Ward.ward_name == ward_name).first()
            if existing:
                print(f"[skip] Ward already exists: {ward_name}")
                skipped += 1
                continue

            ward = Ward(
                ward_name=ward_name,
                ward_number=ward_number,
                circle=str(circle_val) if circle_val else None,
                zone="Serilingampally",
                boundary_geojson=feat["geometry"],
                center_lat=center_lat,
                center_lng=center_lng,
            )
            db.add(ward)
            inserted += 1
            print(f"[add]  Ward {ward_number}: {ward_name}  "
                  f"center=({center_lat:.6f}, {center_lng:.6f})")

        db.commit()
        print(f"\n[done] Inserted {inserted} ward(s), skipped {skipped} duplicate(s).")

    except Exception as exc:
        db.rollback()
        print(f"[error] Database error: {exc}")
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    dry = "--dry" in sys.argv
    seed_wards(dry_run=dry)
