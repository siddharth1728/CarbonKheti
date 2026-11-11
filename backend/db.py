"""SQLite database initialization and connection helpers for CarbonKheti."""

import sqlite3
from contextlib import contextmanager
from backend.config import DB_PATH


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS farmers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT,
    village TEXT NOT NULL,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    land_doc_ref TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS farms (
    id TEXT PRIMARY KEY,
    farmer_id TEXT NOT NULL,
    name TEXT NOT NULL,
    agroforestry_type TEXT NOT NULL,
    species TEXT NOT NULL,
    planting_year INTEGER NOT NULL,
    polygon_geojson TEXT NOT NULL,
    canonical_poly_hash TEXT NOT NULL,
    centroid_lat REAL NOT NULL,
    centroid_lon REAL NOT NULL,
    gross_area_ha REAL NOT NULL,
    core_area_ha REAL NOT NULL,
    core_pixels_10m INTEGER NOT NULL,
    baseline_biomass_t_ha REAL NOT NULL,
    root_to_shoot_ratio REAL NOT NULL,
    leakage_pct REAL NOT NULL,
    permanence_buffer_pct REAL NOT NULL,
    verification_status TEXT NOT NULL DEFAULT 'PENDING',
    created_at TEXT NOT NULL,
    FOREIGN KEY (farmer_id) REFERENCES farmers(id)
);

CREATE TABLE IF NOT EXISTS satellite_observations (
    id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL,
    obs_date TEXT NOT NULL,
    season TEXT NOT NULL,
    data_source TEXT NOT NULL,
    cloud_cover_pct REAL NOT NULL,
    optical_valid_pct REAL NOT NULL,
    radar_fallback_used INTEGER NOT NULL,
    b2_blue REAL NOT NULL,
    b4_red REAL NOT NULL,
    b5_re1 REAL NOT NULL,
    b8_nir REAL NOT NULL,
    ndvi_mean REAL NOT NULL,
    ndre_mean REAL NOT NULL,
    evi_mean REAL NOT NULL,
    s1_vv_db REAL NOT NULL,
    s1_vh_db REAL NOT NULL,
    s1_vh_vv_ratio REAL NOT NULL,
    ndvi_grid_json TEXT NOT NULL,
    is_simulated_label TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (farm_id) REFERENCES farms(id)
);

CREATE TABLE IF NOT EXISTS biomass_estimates (
    id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL,
    obs_id TEXT NOT NULL,
    obs_date TEXT NOT NULL,
    model_version TEXT NOT NULL,
    sensor_mode TEXT NOT NULL,
    agb_point_t_ha REAL NOT NULL,
    agb_ci_lower_t_ha REAL NOT NULL,
    agb_ci_upper_t_ha REAL NOT NULL,
    agb_lower_total_t REAL NOT NULL,
    bgb_lower_total_t REAL NOT NULL,
    total_biomass_lower_t REAL NOT NULL,
    baseline_total_t REAL NOT NULL,
    net_additional_biomass_t REAL NOT NULL,
    carbon_tC REAL NOT NULL,
    co2e_gross_t REAL NOT NULL,
    co2e_conservatively_issuable_t REAL NOT NULL,
    ci_width_t_ha REAL NOT NULL,
    assumptions_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (farm_id) REFERENCES farms(id),
    FOREIGN KEY (obs_id) REFERENCES satellite_observations(id)
);

CREATE TABLE IF NOT EXISTS evidence_records (
    id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL,
    farmer_id TEXT NOT NULL,
    file_path TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    perceptual_dhash TEXT NOT NULL,
    claimed_tree_presence INTEGER NOT NULL DEFAULT 1,
    capture_lat REAL,
    capture_lon REAL,
    exif_lat REAL,
    exif_lon REAL,
    exif_timestamp TEXT,
    exif_camera TEXT,
    exif_present INTEGER NOT NULL,
    upload_timestamp TEXT NOT NULL,
    offline_captured INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'RECORDED',
    FOREIGN KEY (farm_id) REFERENCES farms(id),
    FOREIGN KEY (farmer_id) REFERENCES farmers(id)
);

CREATE TABLE IF NOT EXISTS fraud_alerts (
    id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL,
    evidence_id TEXT,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    risk_score INTEGER NOT NULL,
    explanation TEXT NOT NULL,
    evidence_details_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (farm_id) REFERENCES farms(id)
);

CREATE TABLE IF NOT EXISTS audit_chain (
    seq_id INTEGER PRIMARY KEY AUTOINCREMENT,
    farm_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS carbon_passports (
    passport_id TEXT PRIMARY KEY,
    farm_id TEXT NOT NULL,
    issued_at TEXT NOT NULL,
    model_version TEXT NOT NULL,
    head_hash TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    FOREIGN KEY (farm_id) REFERENCES farms(id)
);
"""


def init_db() -> None:
    """Create tables if they do not yet exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(SCHEMA_SQL)
        conn.commit()


@contextmanager
def get_conn():
    """Yield a sqlite3 connection with Row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

