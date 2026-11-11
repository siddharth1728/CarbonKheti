"""FastAPI Backend for CarbonKheti PS-13 Carbon Intelligence Platform."""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import (
    BASE_DIR,
    CALIBRATION_LABEL,
    DATA_DIR,
    DB_PATH,
    MODEL_VERSION,
    SAMPLE_PHOTOS_DIR,
    TARGET_COST_BREAKDOWN_INR,
    TARGET_COST_INR_PER_HA_YR,
    UPLOADS_DIR,
)
from backend.db import get_conn, init_db
from backend.fraud_engine import (
    build_jpeg_with_exif,
    compute_farm_risk_summary,
    evaluate_evidence_fraud_signals,
    evaluate_vegetation_and_carbon_anomalies,
)
from backend.geo_engine import check_polygon_overlaps, compute_plot_spatial_metrics, generate_spatial_ndvi_grid
from backend.hash_chain import append_audit_event, verify_farm_chain
from backend.ml_engine import get_carbon_model, synthesize_satellite_observation
from backend.report_generator import render_carbon_passport_html
from backend.seed_data import seed_database_if_empty


_BOOTSTRAPPED = False


def ensure_initialized() -> None:
    """Initialize SQLite schema, sample seed data, and ML model once per runtime."""
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED and DB_PATH.exists():
        return
    init_db()
    seed_database_if_empty()
    get_carbon_model()
    _BOOTSTRAPPED = True


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_initialized()
    yield


app = FastAPI(
    title="CarbonKheti PS-13 MRV API",
    description="Open, conservative, tamper-evident smallholder agroforestry Carbon Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def _ensure_runtime_initialized(request: Request, call_next):
    ensure_initialized()
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.mount("/sample-photos", StaticFiles(directory=str(SAMPLE_PHOTOS_DIR)), name="sample-photos")


# --- Pydantic Schemas ---
class FarmerCreate(BaseModel):
    name: str = Field(..., min_length=2)
    phone: Optional[str] = ""
    village: str = Field(..., min_length=2)
    district: str = Field(..., min_length=2)
    state: str = Field(..., min_length=2)
    land_doc_ref: Optional[str] = ""


class FarmCreate(BaseModel):
    farmer_id: str
    name: str = Field(..., min_length=2)
    agroforestry_type: str = "Boundary / Bund Planting"
    species: str = "Teak + Neem"
    planting_year: int = 2024
    polygon_geojson: Dict[str, Any]
    baseline_biomass_t_ha: float = 3.0
    root_to_shoot_ratio: float = 0.24
    leakage_pct: float = 5.0
    permanence_buffer_pct: float = 15.0
    initial_ndvi: float = 0.62
    initial_cloud_cover_pct: float = 14.0


class RunEstimationRequest(BaseModel):
    obs_date: Optional[str] = None
    season: str = "Live Monitoring Run"
    ndvi_override: Optional[float] = None
    cloud_cover_pct: float = 15.0
    baseline_biomass_t_ha: Optional[float] = None
    permanence_buffer_pct: Optional[float] = None


class SimulateFraudRequest(BaseModel):
    farm_id: str
    scenario: str  # "duplicate_plot" | "reused_photo" | "spoofed_gps_exif" | "stripped_exif" | "ndvi_mismatch"


# --- Helpers ---
def _build_farm_dossier(conn, farm_id: str, simulate_tamper_seq: Optional[int] = None) -> Dict[str, Any]:
    farm_row = conn.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone()
    if not farm_row:
        raise HTTPException(status_code=404, detail=f"Farm {farm_id} not found")
    farm = dict(farm_row)
    farm["polygon_geojson"] = json.loads(farm["polygon_geojson"])
    spatial_extra = compute_plot_spatial_metrics(farm["polygon_geojson"])
    farm["core_polygon_geojson"] = spatial_extra["core_polygon_geojson"]
    farm["edge_loss_pct"] = spatial_extra["edge_loss_pct"]
    farm["gross_pixels_10m"] = spatial_extra["gross_pixels_10m"]

    farmer = dict(conn.execute("SELECT * FROM farmers WHERE id = ?", (farm["farmer_id"],)).fetchone())

    obs_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM satellite_observations WHERE farm_id = ? ORDER BY obs_date ASC",
            (farm_id,),
        ).fetchall()
    ]
    for o in obs_rows:
        o["ndvi_grid"] = json.loads(o.pop("ndvi_grid_json"))
        o["radar_fallback_used"] = bool(o["radar_fallback_used"])

    est_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM biomass_estimates WHERE farm_id = ? ORDER BY obs_date ASC, created_at ASC",
            (farm_id,),
        ).fetchall()
    ]
    for e in est_rows:
        e["assumptions"] = json.loads(e["assumptions_json"])

    ev_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM evidence_records WHERE farm_id = ? ORDER BY upload_timestamp DESC",
            (farm_id,),
        ).fetchall()
    ]

    alert_rows = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM fraud_alerts WHERE farm_id = ? ORDER BY created_at DESC",
            (farm_id,),
        ).fetchall()
    ]
    for a in alert_rows:
        a["evidence_details"] = json.loads(a.pop("evidence_details_json"))

    risk_summary = compute_farm_risk_summary(alert_rows)
    chain = verify_farm_chain(conn, farm_id, simulate_tamper_seq=simulate_tamper_seq)
    passport_row = conn.execute(
        "SELECT * FROM carbon_passports WHERE farm_id = ? ORDER BY issued_at DESC LIMIT 1",
        (farm_id,),
    ).fetchone()

    passport = dict(passport_row) if passport_row else {
        "passport_id": f"PENDING-{farm_id}",
        "farm_id": farm_id,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "model_version": MODEL_VERSION,
        "head_hash": chain["head_hash"] or ("0" * 64),
        "verification_status": farm["verification_status"],
    }

    return {
        "farm": farm,
        "farmer": farmer,
        "observations": obs_rows,
        "latest_observation": obs_rows[-1] if obs_rows else None,
        "estimates": est_rows,
        "latest_estimate": est_rows[-1] if est_rows else None,
        "evidence_records": ev_rows,
        "fraud_alerts": alert_rows,
        "risk_summary": risk_summary,
        "chain_verification": chain,
        "passport": passport,
    }


# --- API Endpoints ---
@app.get("/api/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION, "calibration": CALIBRATION_LABEL}


@app.get("/api/dashboard")
def get_dashboard_overview():
    model = get_carbon_model()
    with get_conn() as conn:
        farms = [dict(r) for r in conn.execute("SELECT * FROM farms ORDER BY created_at DESC").fetchall()]
        farmers = [dict(r) for r in conn.execute("SELECT * FROM farmers ORDER BY created_at DESC").fetchall()]
        all_alerts = [dict(r) for r in conn.execute("SELECT * FROM fraud_alerts ORDER BY created_at DESC").fetchall()]
        for a in all_alerts:
            a["evidence_details"] = json.loads(a.pop("evidence_details_json"))

        total_gross_ha = 0.0
        total_core_ha = 0.0
        total_biomass_lower_t = 0.0
        total_carbon_tC = 0.0
        total_co2e_gross_t = 0.0
        total_co2e_issuable_t = 0.0
        verified_chains = 0

        enriched_farms = []
        for f in farms:
            f["polygon_geojson"] = json.loads(f["polygon_geojson"])
            f["core_polygon_geojson"] = compute_plot_spatial_metrics(f["polygon_geojson"])["core_polygon_geojson"]
            farmer_obj = next((fm for fm in farmers if fm["id"] == f["farmer_id"]), {})
            latest_est = conn.execute(
                "SELECT * FROM biomass_estimates WHERE farm_id = ? ORDER BY obs_date DESC, created_at DESC LIMIT 1",
                (f["id"],),
            ).fetchone()
            latest_obs = conn.execute(
                "SELECT id, obs_date, season, cloud_cover_pct, radar_fallback_used, ndvi_mean, ndre_mean, evi_mean, s1_vv_db, s1_vh_db FROM satellite_observations WHERE farm_id = ? ORDER BY obs_date DESC LIMIT 1",
                (f["id"],),
            ).fetchone()
            farm_alerts = [al for al in all_alerts if al["farm_id"] == f["id"]]
            risk = compute_farm_risk_summary(farm_alerts)
            chain = verify_farm_chain(conn, f["id"])
            if chain["verified"]:
                verified_chains += 1

            est_dict = dict(latest_est) if latest_est else None
            obs_dict = dict(latest_obs) if latest_obs else None
            if obs_dict:
                obs_dict["radar_fallback_used"] = bool(obs_dict["radar_fallback_used"])

            total_gross_ha += f["gross_area_ha"]
            total_core_ha += f["core_area_ha"]
            if est_dict:
                total_biomass_lower_t += est_dict["total_biomass_lower_t"]
                total_carbon_tC += est_dict["carbon_tC"]
                total_co2e_gross_t += est_dict["co2e_gross_t"]
                total_co2e_issuable_t += est_dict["co2e_conservatively_issuable_t"]

            enriched_farms.append({
                **f,
                "farmer_name": farmer_obj.get("name", "Unknown"),
                "district": farmer_obj.get("district", ""),
                "state": farmer_obj.get("state", ""),
                "latest_estimate": est_dict,
                "latest_observation": obs_dict,
                "risk_summary": risk,
                "chain_verified": chain["verified"],
                "head_hash": chain["head_hash"],
            })

        # Historical aggregate trend across years
        trend_rows = conn.execute(
            """
            SELECT substr(obs_date, 1, 4) AS year,
                   ROUND(AVG(ndvi_mean), 3) AS avg_ndvi,
                   COUNT(*) AS obs_count
            FROM satellite_observations
            GROUP BY substr(obs_date, 1, 4)
            ORDER BY year ASC
            """
        ).fetchall()

        return {
            "summary": {
                "total_farmers": len(farmers),
                "total_farms": len(farms),
                "total_gross_hectares": round(total_gross_ha, 3),
                "total_core_hectares": round(total_core_ha, 3),
                "total_conservative_biomass_t": round(total_biomass_lower_t, 2),
                "total_carbon_tC": round(total_carbon_tC, 2),
                "total_co2e_gross_t": round(total_co2e_gross_t, 2),
                "total_co2e_issuable_t": round(total_co2e_issuable_t, 2),
                "active_fraud_alerts": sum(1 for a in all_alerts if not a["resolved"]),
                "chains_verified": verified_chains,
                "target_cost_inr_ha_yr": TARGET_COST_INR_PER_HA_YR,
            },
            "cost_breakdown": TARGET_COST_BREAKDOWN_INR,
            "model_metrics": model.metrics,
            "historical_trend": [dict(r) for r in trend_rows],
            "farms": enriched_farms,
            "farmers": farmers,
            "recent_alerts": all_alerts[:25],
        }


@app.get("/api/farmers")
def list_farmers():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM farmers ORDER BY created_at DESC").fetchall()
        return {"farmers": [dict(r) for r in rows]}


@app.post("/api/farmers")
def create_farmer(payload: FarmerCreate):
    farmer_id = f"FMR-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO farmers (id, name, phone, village, district, state, land_doc_ref, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (farmer_id, payload.name, payload.phone, payload.village, payload.district, payload.state, payload.land_doc_ref, now),
        )
    return {"farmer": {"id": farmer_id, **payload.model_dump(), "created_at": now}}


@app.get("/api/farms/{farm_id}")
def get_farm_detail(farm_id: str, simulate_tamper_seq: Optional[int] = Query(default=None)):
    with get_conn() as conn:
        return _build_farm_dossier(conn, farm_id, simulate_tamper_seq=simulate_tamper_seq)


@app.post("/api/farms")
def register_farm(payload: FarmCreate):
    try:
        spatial = compute_plot_spatial_metrics(payload.polygon_geojson)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid polygon geometry: {exc}")

    farm_id = f"FARM-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    obs_date = now[:10]
    model = get_carbon_model()

    with get_conn() as conn:
        farmer = conn.execute("SELECT * FROM farmers WHERE id = ?", (payload.farmer_id,)).fetchone()
        if not farmer:
            raise HTTPException(status_code=404, detail=f"Farmer {payload.farmer_id} not found")

        existing_farms = [dict(r) for r in conn.execute("SELECT * FROM farms").fetchall()]
        overlaps = check_polygon_overlaps(spatial["polygon_geojson"], existing_farms)
        status = "FLAGGED_REVIEW" if overlaps else "VERIFIED_PROTOTYPE"

        conn.execute(
            """
            INSERT INTO farms (
                id, farmer_id, name, agroforestry_type, species, planting_year,
                polygon_geojson, canonical_poly_hash, centroid_lat, centroid_lon,
                gross_area_ha, core_area_ha, core_pixels_10m, baseline_biomass_t_ha,
                root_to_shoot_ratio, leakage_pct, permanence_buffer_pct,
                verification_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                farm_id, payload.farmer_id, payload.name, payload.agroforestry_type,
                payload.species, payload.planting_year, json.dumps(spatial["polygon_geojson"]),
                spatial["canonical_poly_hash"], spatial["centroid_lat"], spatial["centroid_lon"],
                spatial["gross_area_ha"], spatial["core_area_ha"], spatial["core_pixels_10m"],
                payload.baseline_biomass_t_ha, payload.root_to_shoot_ratio,
                payload.leakage_pct, payload.permanence_buffer_pct, status, now,
            ),
        )

        append_audit_event(
            conn, farm_id, "FARM_REGISTERED",
            {
                "farmer_id": payload.farmer_id,
                "gross_area_ha": spatial["gross_area_ha"],
                "core_area_ha": spatial["core_area_ha"],
                "canonical_poly_hash": spatial["canonical_poly_hash"],
            },
            timestamp=now,
        )

        for ov in overlaps:
            alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
            conn.execute(
                """
                INSERT INTO fraud_alerts (id, farm_id, evidence_id, alert_type, severity, risk_score, explanation, evidence_details_json, created_at, resolved)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    alert_id, farm_id,
                    "DUPLICATE_PLOT_HASH" if ov["exact_duplicate_hash"] else "POLYGON_OVERLAP_DOUBLE_COUNTING",
                    "CRITICAL", 93,
                    f"New boundary overlaps {ov['overlap_pct_of_new_plot']}% ({ov['intersection_ha']} ha, IoU={ov['iou']}) with {ov['existing_farm_name']} ({ov['existing_farm_id']}).",
                    json.dumps(ov), now,
                ),
            )
            append_audit_event(conn, farm_id, "FRAUD_ALERT_TRIGGERED", {"alert_id": alert_id, **ov}, timestamp=now)

        # Create initial baseline (2 years prior) + current satellite observation & estimate
        baseline_date = f"{max(2021, payload.planting_year)}-11-15"
        obs_base = synthesize_satellite_observation(farm_id, baseline_date, "Initial Baseline", max(0.26, payload.initial_ndvi - 0.24), 12.0)
        grid_base = generate_spatial_ndvi_grid(spatial["polygon_geojson"], obs_base["ndvi_mean"], obs_base["s1_vv_db"], f"{farm_id}-base")
        conn.execute(
            """
            INSERT INTO satellite_observations (
                id, farm_id, obs_date, season, data_source, cloud_cover_pct, optical_valid_pct,
                radar_fallback_used, b2_blue, b4_red, b5_re1, b8_nir, ndvi_mean, ndre_mean,
                evi_mean, s1_vv_db, s1_vh_db, s1_vh_vv_ratio, ndvi_grid_json, is_simulated_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"OBS-{farm_id}-BASE", farm_id, baseline_date, obs_base["season"], obs_base["data_source"],
                obs_base["cloud_cover_pct"], obs_base["optical_valid_pct"], int(obs_base["radar_fallback_used"]),
                obs_base["b2_blue"], obs_base["b4_red"], obs_base["b5_re1"], obs_base["b8_nir"],
                obs_base["ndvi_mean"], obs_base["ndre_mean"], obs_base["evi_mean"],
                obs_base["s1_vv_db"], obs_base["s1_vh_db"], obs_base["s1_vh_vv_ratio"],
                json.dumps(grid_base), obs_base["is_simulated_label"], now,
            ),
        )

        obs_curr = synthesize_satellite_observation(farm_id, obs_date, "Current Registration Scan", payload.initial_ndvi, payload.initial_cloud_cover_pct)
        obs_id = f"OBS-{uuid.uuid4().hex[:8].upper()}"
        grid_curr = generate_spatial_ndvi_grid(spatial["polygon_geojson"], obs_curr["ndvi_mean"], obs_curr["s1_vv_db"], f"{farm_id}-{obs_date}")
        conn.execute(
            """
            INSERT INTO satellite_observations (
                id, farm_id, obs_date, season, data_source, cloud_cover_pct, optical_valid_pct,
                radar_fallback_used, b2_blue, b4_red, b5_re1, b8_nir, ndvi_mean, ndre_mean,
                evi_mean, s1_vv_db, s1_vh_db, s1_vh_vv_ratio, ndvi_grid_json, is_simulated_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs_id, farm_id, obs_date, obs_curr["season"], obs_curr["data_source"],
                obs_curr["cloud_cover_pct"], obs_curr["optical_valid_pct"], int(obs_curr["radar_fallback_used"]),
                obs_curr["b2_blue"], obs_curr["b4_red"], obs_curr["b5_re1"], obs_curr["b8_nir"],
                obs_curr["ndvi_mean"], obs_curr["ndre_mean"], obs_curr["evi_mean"],
                obs_curr["s1_vv_db"], obs_curr["s1_vh_db"], obs_curr["s1_vh_vv_ratio"],
                json.dumps(grid_curr), obs_curr["is_simulated_label"], now,
            ),
        )

        est = model.estimate_biomass_and_carbon(
            ndvi=obs_curr["ndvi_mean"], ndre=obs_curr["ndre_mean"], evi=obs_curr["evi_mean"],
            s1_vv_db=obs_curr["s1_vv_db"], s1_vh_db=obs_curr["s1_vh_db"],
            cloud_cover_pct=obs_curr["cloud_cover_pct"],
            gross_area_ha=spatial["gross_area_ha"], core_area_ha=spatial["core_area_ha"],
            core_pixels_10m=spatial["core_pixels_10m"],
            baseline_biomass_t_ha=payload.baseline_biomass_t_ha,
            root_to_shoot_ratio=payload.root_to_shoot_ratio,
            leakage_pct=payload.leakage_pct,
            permanence_buffer_pct=payload.permanence_buffer_pct,
        )
        est_id = f"EST-{uuid.uuid4().hex[:8].upper()}"
        conn.execute(
            """
            INSERT INTO biomass_estimates (
                id, farm_id, obs_id, obs_date, model_version, sensor_mode,
                agb_point_t_ha, agb_ci_lower_t_ha, agb_ci_upper_t_ha,
                agb_lower_total_t, bgb_lower_total_t, total_biomass_lower_t,
                baseline_total_t, net_additional_biomass_t, carbon_tC,
                co2e_gross_t, co2e_conservatively_issuable_t, ci_width_t_ha,
                assumptions_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                est_id, farm_id, obs_id, obs_date, est["model_version"], est["sensor_mode"],
                est["agb_point_t_ha"], est["agb_ci_lower_t_ha"], est["agb_ci_upper_t_ha"],
                est["agb_lower_total_t"], est["bgb_lower_total_t"], est["total_biomass_lower_t"],
                est["baseline_total_t"], est["net_additional_biomass_t"], est["carbon_tC"],
                est["co2e_gross_t"], est["co2e_conservatively_issuable_t"], est["ci_width_t_ha"],
                json.dumps(est["assumptions"]), now,
            ),
        )
        append_audit_event(
            conn, farm_id, "BIOMASS_ESTIMATED",
            {"estimate_id": est_id, "co2e_conservatively_issuable_t": est["co2e_conservatively_issuable_t"]},
            timestamp=now,
        )

        return _build_farm_dossier(conn, farm_id)


@app.post("/api/farms/{farm_id}/estimate")
def run_farm_estimation(farm_id: str, payload: RunEstimationRequest):
    """Run fresh satellite processing + Scikit-learn bootstrap biomass pipeline on a farm."""
    model = get_carbon_model()
    now = datetime.now(timezone.utc).isoformat()
    obs_date = payload.obs_date or now[:10]

    with get_conn() as conn:
        farm_row = conn.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone()
        if not farm_row:
            raise HTTPException(status_code=404, detail="Farm not found")
        farm = dict(farm_row)
        poly = json.loads(farm["polygon_geojson"])

        latest_obs = conn.execute(
            "SELECT * FROM satellite_observations WHERE farm_id = ? ORDER BY obs_date DESC LIMIT 1",
            (farm_id,),
        ).fetchone()
        base_ndvi = payload.ndvi_override if payload.ndvi_override is not None else (float(latest_obs["ndvi_mean"]) if latest_obs else 0.62)

        obs = synthesize_satellite_observation(
            farm_id, obs_date, payload.season, base_ndvi, payload.cloud_cover_pct, seed_salt=now
        )
        obs_id = f"OBS-{uuid.uuid4().hex[:8].upper()}"
        grid = generate_spatial_ndvi_grid(poly, obs["ndvi_mean"], obs["s1_vv_db"], f"{farm_id}-{obs_id}")

        conn.execute(
            """
            INSERT INTO satellite_observations (
                id, farm_id, obs_date, season, data_source, cloud_cover_pct, optical_valid_pct,
                radar_fallback_used, b2_blue, b4_red, b5_re1, b8_nir, ndvi_mean, ndre_mean,
                evi_mean, s1_vv_db, s1_vh_db, s1_vh_vv_ratio, ndvi_grid_json, is_simulated_label, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                obs_id, farm_id, obs_date, obs["season"], obs["data_source"],
                obs["cloud_cover_pct"], obs["optical_valid_pct"], int(obs["radar_fallback_used"]),
                obs["b2_blue"], obs["b4_red"], obs["b5_re1"], obs["b8_nir"],
                obs["ndvi_mean"], obs["ndre_mean"], obs["evi_mean"],
                obs["s1_vv_db"], obs["s1_vh_db"], obs["s1_vh_vv_ratio"],
                json.dumps(grid), obs["is_simulated_label"], now,
            ),
        )

        baseline_bio = payload.baseline_biomass_t_ha if payload.baseline_biomass_t_ha is not None else farm["baseline_biomass_t_ha"]
        perm_buf = payload.permanence_buffer_pct if payload.permanence_buffer_pct is not None else farm["permanence_buffer_pct"]

        est = model.estimate_biomass_and_carbon(
            ndvi=obs["ndvi_mean"], ndre=obs["ndre_mean"], evi=obs["evi_mean"],
            s1_vv_db=obs["s1_vv_db"], s1_vh_db=obs["s1_vh_db"],
            cloud_cover_pct=obs["cloud_cover_pct"],
            gross_area_ha=farm["gross_area_ha"], core_area_ha=farm["core_area_ha"],
            core_pixels_10m=farm["core_pixels_10m"],
            baseline_biomass_t_ha=baseline_bio,
            root_to_shoot_ratio=farm["root_to_shoot_ratio"],
            leakage_pct=farm["leakage_pct"],
            permanence_buffer_pct=perm_buf,
        )
        est_id = f"EST-{uuid.uuid4().hex[:8].upper()}"
        conn.execute(
            """
            INSERT INTO biomass_estimates (
                id, farm_id, obs_id, obs_date, model_version, sensor_mode,
                agb_point_t_ha, agb_ci_lower_t_ha, agb_ci_upper_t_ha,
                agb_lower_total_t, bgb_lower_total_t, total_biomass_lower_t,
                baseline_total_t, net_additional_biomass_t, carbon_tC,
                co2e_gross_t, co2e_conservatively_issuable_t, ci_width_t_ha,
                assumptions_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                est_id, farm_id, obs_id, obs_date, est["model_version"], est["sensor_mode"],
                est["agb_point_t_ha"], est["agb_ci_lower_t_ha"], est["agb_ci_upper_t_ha"],
                est["agb_lower_total_t"], est["bgb_lower_total_t"], est["total_biomass_lower_t"],
                est["baseline_total_t"], est["net_additional_biomass_t"], est["carbon_tC"],
                est["co2e_gross_t"], est["co2e_conservatively_issuable_t"], est["ci_width_t_ha"],
                json.dumps(est["assumptions"]), now,
            ),
        )

        # Anomaly check across time series
        obs_all = [dict(r) for r in conn.execute("SELECT * FROM satellite_observations WHERE farm_id = ?", (farm_id,)).fetchall()]
        est_all = [dict(r) for r in conn.execute("SELECT * FROM biomass_estimates WHERE farm_id = ?", (farm_id,)).fetchall()]
        anom_alerts = evaluate_vegetation_and_carbon_anomalies(farm_id, obs_all, est_all)
        for al in anom_alerts:
            al_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
            conn.execute(
                """
                INSERT INTO fraud_alerts (id, farm_id, evidence_id, alert_type, severity, risk_score, explanation, evidence_details_json, created_at, resolved)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 0)
                """,
                (al_id, farm_id, al["alert_type"], al["severity"], al["risk_score"], al["explanation"], json.dumps(al["evidence_details"]), now),
            )

        append_audit_event(
            conn, farm_id, "BIOMASS_ESTIMATED",
            {
                "estimate_id": est_id,
                "cloud_cover_pct": obs["cloud_cover_pct"],
                "radar_fallback_used": obs["radar_fallback_used"],
                "agb_ci_lower_t_ha": est["agb_ci_lower_t_ha"],
                "co2e_conservatively_issuable_t": est["co2e_conservatively_issuable_t"],
            },
            timestamp=now,
        )
        return _build_farm_dossier(conn, farm_id)


@app.post("/api/evidence/upload")
async def upload_evidence(
    farm_id: str = Form(...),
    claimed_tree_presence: bool = Form(True),
    capture_lat: Optional[float] = Form(None),
    capture_lon: Optional[float] = Form(None),
    offline_captured: bool = Form(False),
    notes: str = Form(""),
    photo: UploadFile = File(...),
):
    """Upload farmer field photograph, extract EXIF, compute SHA-256 & perceptual dHash, run Fraud Radar."""
    file_bytes = await photo.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
    safe_ext = Path(photo.filename or "evidence.jpg").suffix or ".jpg"
    saved_name = f"{ev_id}{safe_ext}"
    (UPLOADS_DIR / saved_name).write_bytes(file_bytes)

    with get_conn() as conn:
        farm_row = conn.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone()
        if not farm_row:
            raise HTTPException(status_code=404, detail="Farm not found")
        farm = dict(farm_row)

        existing_ev = [dict(r) for r in conn.execute("SELECT * FROM evidence_records").fetchall()]
        latest_obs = conn.execute(
            "SELECT * FROM satellite_observations WHERE farm_id = ? ORDER BY obs_date DESC LIMIT 1",
            (farm_id,),
        ).fetchone()
        latest_obs_dict = dict(latest_obs) if latest_obs else None

        meta, alerts = evaluate_evidence_fraud_signals(
            farm=farm,
            file_bytes=file_bytes,
            capture_lat=capture_lat,
            capture_lon=capture_lon,
            claimed_tree_presence=claimed_tree_presence,
            offline_captured=offline_captured,
            upload_ts=now,
            existing_evidence=existing_ev,
            latest_sat_obs=latest_obs_dict,
        )

        ev_status = "FLAGGED" if alerts else "VERIFIED"
        conn.execute(
            """
            INSERT INTO evidence_records (
                id, farm_id, farmer_id, file_path, original_filename,
                file_sha256, perceptual_dhash, claimed_tree_presence,
                capture_lat, capture_lon, exif_lat, exif_lon, exif_timestamp,
                exif_camera, exif_present, upload_timestamp, offline_captured, notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev_id, farm_id, farm["farmer_id"], f"/uploads/{saved_name}", photo.filename or saved_name,
                meta["file_sha256"], meta["perceptual_dhash"], int(claimed_tree_presence),
                capture_lat, capture_lon, meta["exif_lat"], meta["exif_lon"], meta["exif_timestamp"],
                meta["exif_camera"], int(meta["exif_present"]), now_iso, int(offline_captured),
                notes, ev_status,
            ),
        )

        created_alerts = []
        for al in alerts:
            al_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
            conn.execute(
                """
                INSERT INTO fraud_alerts (id, farm_id, evidence_id, alert_type, severity, risk_score, explanation, evidence_details_json, created_at, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (al_id, farm_id, ev_id, al["alert_type"], al["severity"], al["risk_score"], al["explanation"], json.dumps(al["evidence_details"]), now_iso),
            )
            created_alerts.append({"id": al_id, **al})

        if any(a["severity"] in ("CRITICAL", "HIGH") for a in alerts):
            conn.execute("UPDATE farms SET verification_status = 'FLAGGED_REVIEW' WHERE id = ?", (farm_id,))

        append_audit_event(
            conn, farm_id, "EVIDENCE_UPLOADED",
            {
                "evidence_id": ev_id,
                "sha256": meta["file_sha256"],
                "dhash": meta["perceptual_dhash"],
                "alerts_triggered": [a["alert_type"] for a in alerts],
            },
            timestamp=now_iso,
        )

        return {
            "evidence_id": ev_id,
            "status": ev_status,
            "metadata": meta,
            "alerts_triggered": created_alerts,
            "dossier": _build_farm_dossier(conn, farm_id),
        }


@app.post("/api/fraud/simulate")
def simulate_fraud_scenario(payload: SimulateFraudRequest):
    """
    Live hackathon demonstration endpoint: trigger realistic fraud detection on demand
    (reused photo, spoofed GPS EXIF, stripped EXIF, NDVI mismatch, or duplicate overlapping plot).
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    with get_conn() as conn:
        farm_row = conn.execute("SELECT * FROM farms WHERE id = ?", (payload.farm_id,)).fetchone()
        if not farm_row:
            raise HTTPException(status_code=404, detail="Farm not found")
        farm = dict(farm_row)

        if payload.scenario == "duplicate_plot":
            # Register a slightly shifted duplicate polygon overlapping ~65% with target farm
            poly = json.loads(farm["polygon_geojson"])
            shifted_coords = [[round(pt[0] + 0.00022, 6), round(pt[1] + 0.00018, 6)] for pt in poly["coordinates"][0]]
            shifted_poly = {"type": "Polygon", "coordinates": [shifted_coords]}
            existing = [dict(r) for r in conn.execute("SELECT * FROM farms").fetchall()]
            overlaps = check_polygon_overlaps(shifted_poly, existing)
            al_id = f"ALT-SIM-{uuid.uuid4().hex[:6].upper()}"
            ov = overlaps[0] if overlaps else {"overlap_pct_of_new_plot": 62.5, "iou": 0.45, "intersection_ha": round(farm["gross_area_ha"] * 0.62, 3), "existing_farm_id": farm["id"], "existing_farm_name": farm["name"]}
            conn.execute(
                """
                INSERT INTO fraud_alerts (id, farm_id, evidence_id, alert_type, severity, risk_score, explanation, evidence_details_json, created_at, resolved)
                VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    al_id, farm["id"], "POLYGON_OVERLAP_DOUBLE_COUNTING", "CRITICAL", 94,
                    f"Simulated duplicate submission detected: overlaps {ov['overlap_pct_of_new_plot']}% ({ov['intersection_ha']} ha, IoU={ov['iou']}) with {farm['name']}.",
                    json.dumps(ov), now_iso,
                ),
            )
            conn.execute("UPDATE farms SET verification_status = 'FLAGGED_REVIEW' WHERE id = ?", (farm["id"],))
            append_audit_event(conn, farm["id"], "FRAUD_ALERT_TRIGGERED", {"scenario": payload.scenario, **ov}, timestamp=now_iso)
            return _build_farm_dossier(conn, farm["id"])

        # Photo-based fraud scenarios
        existing_ev = [dict(r) for r in conn.execute("SELECT * FROM evidence_records").fetchall()]
        latest_obs = conn.execute("SELECT * FROM satellite_observations WHERE farm_id = ? ORDER BY obs_date DESC LIMIT 1", (farm["id"],)).fetchone()
        latest_obs_dict = dict(latest_obs) if latest_obs else None

        if payload.scenario == "reused_photo" and existing_ev:
            # Copy bytes from an existing photo (or re-save slightly) to trigger SHA-256 / dHash match
            src_name = Path(existing_ev[0]["file_path"]).name
            src_path = UPLOADS_DIR / src_name
            photo_bytes = src_path.read_bytes() if src_path.exists() else build_jpeg_with_exif(lat=farm["centroid_lat"], lon=farm["centroid_lon"])
            fname = f"reused_attack_{uuid.uuid4().hex[:4]}.jpg"
            cap_lat, cap_lon = farm["centroid_lat"], farm["centroid_lon"]
        elif payload.scenario == "spoofed_gps_exif":
            # Embed EXIF GPS 42 km away from farm
            photo_bytes = build_jpeg_with_exif(
                lat=farm["centroid_lat"] + 0.35, lon=farm["centroid_lon"] + 0.28,
                capture_dt_str=now.strftime("%Y:%m:%d %H:%M:%S"),
                label_text="SPOOFED REMOTE GPS PHOTO", seed=777, strip_exif=False,
            )
            fname = f"spoofed_gps_{uuid.uuid4().hex[:4]}.jpg"
            cap_lat, cap_lon = farm["centroid_lat"], farm["centroid_lon"]
        elif payload.scenario == "ndvi_mismatch":
            photo_bytes = build_jpeg_with_exif(
                lat=farm["centroid_lat"], lon=farm["centroid_lon"],
                capture_dt_str=now.strftime("%Y:%m:%d %H:%M:%S"),
                tree_density="high", label_text="CLAIMED DENSE TREES", seed=888,
            )
            fname = f"ndvi_mismatch_{uuid.uuid4().hex[:4]}.jpg"
            cap_lat, cap_lon = farm["centroid_lat"], farm["centroid_lon"]
            latest_obs_dict = {"ndvi_mean": 0.17, "cloud_cover_pct": 8.0, "obs_date": now_iso[:10]}
        else:
            # stripped_exif
            photo_bytes = build_jpeg_with_exif(tree_density="high", label_text="STRIPPED EXIF PHOTO", seed=999, strip_exif=True)
            fname = f"stripped_exif_{uuid.uuid4().hex[:4]}.jpg"
            cap_lat, cap_lon = farm["centroid_lat"], farm["centroid_lon"]

        ev_id = f"EVD-{uuid.uuid4().hex[:8].upper()}"
        (UPLOADS_DIR / fname).write_bytes(photo_bytes)

        meta, alerts = evaluate_evidence_fraud_signals(
            farm=farm,
            file_bytes=photo_bytes,
            capture_lat=cap_lat,
            capture_lon=cap_lon,
            claimed_tree_presence=True,
            offline_captured=False,
            upload_ts=now,
            existing_evidence=existing_ev,
            latest_sat_obs=latest_obs_dict,
        )
        conn.execute(
            """
            INSERT INTO evidence_records (
                id, farm_id, farmer_id, file_path, original_filename,
                file_sha256, perceptual_dhash, claimed_tree_presence,
                capture_lat, capture_lon, exif_lat, exif_lon, exif_timestamp,
                exif_camera, exif_present, upload_timestamp, offline_captured, notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev_id, farm["id"], farm["farmer_id"], f"/uploads/{fname}", fname,
                meta["file_sha256"], meta["perceptual_dhash"], 1,
                cap_lat, cap_lon, meta["exif_lat"], meta["exif_lon"], meta["exif_timestamp"],
                meta["exif_camera"], int(meta["exif_present"]), now_iso, 0,
                f"Simulated Fraud Radar test ({payload.scenario})", "FLAGGED" if alerts else "VERIFIED",
            ),
        )
        for al in alerts:
            al_id = f"ALT-SIM-{uuid.uuid4().hex[:6].upper()}"
            conn.execute(
                """
                INSERT INTO fraud_alerts (id, farm_id, evidence_id, alert_type, severity, risk_score, explanation, evidence_details_json, created_at, resolved)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (al_id, farm["id"], ev_id, al["alert_type"], al["severity"], al["risk_score"], al["explanation"], json.dumps(al["evidence_details"]), now_iso),
            )
        conn.execute("UPDATE farms SET verification_status = 'FLAGGED_REVIEW' WHERE id = ?", (farm["id"],))
        append_audit_event(conn, farm["id"], "FRAUD_SIMULATION_CHECK", {"scenario": payload.scenario, "alerts": [a["alert_type"] for a in alerts]}, timestamp=now_iso)
        return _build_farm_dossier(conn, farm["id"])


@app.post("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM fraud_alerts WHERE id = ?", (alert_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        conn.execute("UPDATE fraud_alerts SET resolved = 1 WHERE id = ?", (alert_id,))
        remaining = conn.execute(
            "SELECT COUNT(*) AS c FROM fraud_alerts WHERE farm_id = ? AND resolved = 0",
            (row["farm_id"],),
        ).fetchone()["c"]
        if remaining == 0:
            conn.execute("UPDATE farms SET verification_status = 'VERIFIED_PROTOTYPE' WHERE id = ?", (row["farm_id"],))
        append_audit_event(conn, row["farm_id"], "FRAUD_ALERT_RESOLVED", {"alert_id": alert_id})
        return {"resolved": True, "alert_id": alert_id, "remaining_active": remaining}


@app.post("/api/passports/{farm_id}/issue")
def issue_carbon_passport(farm_id: str):
    """Generate or refresh a farm's tamper-evident Carbon Passport anchored to its latest SHA-256 head hash."""
    now = datetime.now(timezone.utc).isoformat()
    with get_conn() as conn:
        dossier = _build_farm_dossier(conn, farm_id)
        risk = dossier["risk_summary"]
        status = "VERIFIED_PROTOTYPE" if (dossier["chain_verification"]["verified"] and risk["risk_score"] < 45) else "FLAGGED_REVIEW"
        passport_id = f"CK-PASS-2026-{uuid.uuid4().hex[:4].upper()}"

        head_ev = append_audit_event(
            conn,
            farm_id,
            "CARBON_PASSPORT_ISSUED",
            {
                "passport_id": passport_id,
                "model_version": MODEL_VERSION,
                "co2e_conservatively_issuable_t": dossier["latest_estimate"]["co2e_conservatively_issuable_t"] if dossier["latest_estimate"] else 0.0,
                "risk_score": risk["risk_score"],
            },
            timestamp=now,
        )

        conn.execute(
            """
            INSERT INTO carbon_passports (passport_id, farm_id, issued_at, model_version, head_hash, verification_status, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                passport_id, farm_id, now, MODEL_VERSION, head_ev["record_hash"],
                status, json.dumps({"risk_score": risk["risk_score"]}),
            ),
        )
        return _build_farm_dossier(conn, farm_id)


@app.get("/api/passports/{farm_id}/verify")
def verify_passport_chain(farm_id: str, simulate_tamper_seq: Optional[int] = Query(default=None)):
    with get_conn() as conn:
        return verify_farm_chain(conn, farm_id, simulate_tamper_seq=simulate_tamper_seq)


@app.get("/api/passports/{farm_id}/report.html", response_class=HTMLResponse)
def download_passport_html_report(farm_id: str, lang: str = Query(default="en")):
    with get_conn() as conn:
        dossier = _build_farm_dossier(conn, farm_id)
        html_str = render_carbon_passport_html(dossier, lang=lang)
        return HTMLResponse(
            content=html_str,
            headers={"Content-Disposition": f'attachment; filename="CarbonKheti_Passport_{farm_id}_{lang}.html"'},
        )


@app.get("/api/passports/{farm_id}/bundle.json")
def download_passport_json_bundle(farm_id: str):
    with get_conn() as conn:
        dossier = _build_farm_dossier(conn, farm_id)
        return JSONResponse(
            content=dossier,
            headers={"Content-Disposition": f'attachment; filename="CarbonKheti_AuditBundle_{farm_id}.json"'},
        )


@app.get("/api/sample-photos")
def list_sample_photos():
    files = sorted(p.name for p in SAMPLE_PHOTOS_DIR.glob("*.jpg"))
    return {"sample_photos": [{"filename": f, "url": f"/sample-photos/{f}"} for f in files]}


# Serve built React frontend in production if frontend/dist exists
DIST_DIR = BASE_DIR / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("uploads/") or full_path.startswith("sample-photos/"):
            raise HTTPException(status_code=404, detail="Not found")
        index_file = DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        raise HTTPException(status_code=404, detail="Frontend not built")

