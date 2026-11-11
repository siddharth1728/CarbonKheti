"""Seed realistic Indian smallholder agroforestry dataset, EXIF sample photos, and initial audit chains."""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from backend.config import DATA_DIR, SAMPLE_PHOTOS_DIR, UPLOADS_DIR
from backend.db import get_conn, init_db
from backend.fraud_engine import (
    build_jpeg_with_exif,
    compute_perceptual_dhash,
    compute_sha256_bytes,
    evaluate_evidence_fraud_signals,
    extract_exif_metadata,
)
from backend.geo_engine import check_polygon_overlaps, compute_plot_spatial_metrics, generate_spatial_ndvi_grid
from backend.hash_chain import append_audit_event, verify_farm_chain
from backend.ml_engine import get_carbon_model, synthesize_satellite_observation


def _rect_polygon(lat: float, lon: float, d_lat: float, d_lon: float, skew: float = 0.0) -> Dict[str, Any]:
    coords = [
        [round(lon - d_lon, 6), round(lat - d_lat, 6)],
        [round(lon + d_lon + skew, 6), round(lat - d_lat * 0.92, 6)],
        [round(lon + d_lon, 6), round(lat + d_lat, 6)],
        [round(lon - d_lon + skew * 0.5, 6), round(lat + d_lat * 1.04, 6)],
        [round(lon - d_lon, 6), round(lat - d_lat, 6)],
    ]
    return {"type": "Polygon", "coordinates": [coords]}


SAMPLE_FARMERS = [
    {"id": "FMR-101", "name": "Ramesh Reddy", "phone": "+91-98480-11204", "village": "Nangunur", "district": "Siddipet", "state": "Telangana", "land_doc_ref": "TS-PATTA-88412"},
    {"id": "FMR-102", "name": "Lakshmi Devi", "phone": "+91-94401-55318", "village": "Kalyandurg", "district": "Anantapur", "state": "Andhra Pradesh", "land_doc_ref": "AP-ROR-20419"},
    {"id": "FMR-103", "name": "Gurpreet Singh", "phone": "+91-98154-77092", "village": "Jagraon", "district": "Ludhiana", "state": "Punjab", "land_doc_ref": "PB-JAM-55103"},
    {"id": "FMR-104", "name": "Sunita Deshmukh", "phone": "+91-97650-33821", "village": "Ralegaon", "district": "Yavatmal", "state": "Maharashtra", "land_doc_ref": "MH-712-90314"},
    {"id": "FMR-105", "name": "Basavaraj Patil", "phone": "+91-99002-44180", "village": "Kalghatgi", "district": "Dharwad", "state": "Karnataka", "land_doc_ref": "KA-RTC-61207"},
    {"id": "FMR-106", "name": "Vikram Rao (Test Overlap)", "phone": "+91-90001-00999", "village": "Nangunur", "district": "Siddipet", "state": "Telangana", "land_doc_ref": "TS-PATTA-99001"},
]


SAMPLE_FARMS_SPEC = [
    {
        "id": "FARM-TLG-01",
        "farmer_id": "FMR-101",
        "name": "Nangunur Bund-Teak Agroforestry",
        "agroforestry_type": "Boundary / Bund Planting",
        "species": "Teak (Tectona grandis) + Neem",
        "planting_year": 2021,
        "polygon": _rect_polygon(18.0985, 78.8942, 0.00052, 0.00060, skew=0.00008),
        "baseline_biomass_t_ha": 3.4,
        "timeline": [
            ("2023-11-15", "Post-Monsoon 2023 (Baseline)", 0.34, 14.0),
            ("2024-07-22", "Monsoon 2024 (Radar Fallback)", 0.44, 86.0),
            ("2024-11-18", "Post-Monsoon 2024", 0.53, 11.0),
            ("2025-11-20", "Post-Monsoon 2025", 0.62, 9.0),
            ("2026-10-28", "Current Monitoring 2026", 0.69, 12.0),
        ],
    },
    {
        "id": "FARM-AP-02",
        "farmer_id": "FMR-102",
        "name": "Kalyandurg Mango Horti-Silviculture",
        "agroforestry_type": "Horti-Silviculture",
        "species": "Mango + Red Gram Intercrop",
        "planting_year": 2022,
        "polygon": _rect_polygon(14.5521, 77.1084, 0.00044, 0.00052),
        "baseline_biomass_t_ha": 2.8,
        "timeline": [
            ("2023-11-10", "Post-Monsoon 2023 (Baseline)", 0.30, 10.0),
            ("2024-08-05", "Monsoon 2024 (Radar Fallback)", 0.39, 74.0),
            ("2025-11-12", "Post-Monsoon 2025", 0.51, 8.0),
            ("2026-10-25", "Current Monitoring 2026", 0.58, 15.0),
        ],
    },
    {
        "id": "FARM-PNJ-03",
        "farmer_id": "FMR-103",
        "name": "Jagraon Poplar-Wheat Alley Plot",
        "agroforestry_type": "Agri-Silviculture / Alley Cropping",
        "species": "Poplar (Populus deltoides) + Wheat",
        "planting_year": 2020,
        "polygon": _rect_polygon(30.7892, 75.4735, 0.00062, 0.00075),
        "baseline_biomass_t_ha": 4.1,
        "timeline": [
            ("2023-11-05", "Post-Monsoon 2023 (Baseline)", 0.41, 18.0),
            ("2024-07-19", "Monsoon 2024 (Radar Fallback)", 0.54, 78.0),
            ("2025-11-14", "Post-Monsoon 2025", 0.68, 14.0),
            ("2026-10-27", "Current Monitoring 2026", 0.76, 11.0),
        ],
    },
    {
        "id": "FARM-MHA-04",
        "farmer_id": "FMR-104",
        "name": "Ralegaon Cloud-Resilient Subabul",
        "agroforestry_type": "Agri-Silviculture",
        "species": "Subabul + Pigeon Pea",
        "planting_year": 2022,
        "polygon": _rect_polygon(20.4176, 78.5231, 0.00048, 0.00056),
        "baseline_biomass_t_ha": 3.0,
        "timeline": [
            ("2023-11-18", "Post-Monsoon 2023 (Baseline)", 0.32, 16.0),
            ("2025-11-09", "Post-Monsoon 2025", 0.54, 21.0),
            ("2026-11-02", "Current Monitoring 2026 (Cloudy SAR Fallback)", 0.61, 84.0),
        ],
    },
    {
        "id": "FARM-KRN-05",
        "farmer_id": "FMR-105",
        "name": "Kalghatgi Micro-Plot (0.28 ha)",
        "agroforestry_type": "Boundary / Bund Planting",
        "species": "Casuarina + Coconut",
        "planting_year": 2023,
        "polygon": _rect_polygon(15.1844, 74.9712, 0.00024, 0.00028),
        "baseline_biomass_t_ha": 2.5,
        "timeline": [
            ("2024-11-20", "Post-Monsoon 2024", 0.36, 12.0),
            ("2026-10-26", "Current Monitoring 2026", 0.52, 19.0),
        ],
    },
    {
        "id": "FARM-FRD-06",
        "farmer_id": "FMR-106",
        "name": "Siddipet Adjacent Claim (Overlap Case)",
        "agroforestry_type": "Boundary / Bund Planting",
        "species": "Eucalyptus",
        "planting_year": 2023,
        # Intentionally overlaps ~35-45% with FARM-TLG-01 for Fraud Radar demonstration
        "polygon": _rect_polygon(18.0989, 78.8947, 0.00048, 0.00054),
        "baseline_biomass_t_ha": 3.4,
        "timeline": [
            ("2025-11-15", "Post-Monsoon 2025", 0.47, 15.0),
            ("2026-10-29", "Current Monitoring 2026", 0.50, 14.0),
        ],
    },
]


def ensure_sample_photos() -> None:
    """Write 3 realistic sample JPEGs for judge testing (authentic EXIF, stripped EXIF, spoofed GPS)."""
    specs = [
        (
            SAMPLE_PHOTOS_DIR / "authentic_telangana_trees.jpg",
            dict(lat=18.0985, lon=78.8942, tree_density="high", label_text="TELANGANA TEAK BUND PLOT", seed=11, strip_exif=False),
        ),
        (
            SAMPLE_PHOTOS_DIR / "stripped_exif_whatsapp.jpg",
            dict(lat=None, lon=None, tree_density="high", label_text="RECOMPRESSED NO-EXIF PHOTO", seed=22, strip_exif=True),
        ),
        (
            SAMPLE_PHOTOS_DIR / "spoofed_remote_gps.jpg",
            dict(lat=17.3850, lon=78.4867, tree_density="barren", label_text="HYDERABAD FAR GPS SPOOF", seed=33, strip_exif=False),
        ),
    ]
    for path, kwargs in specs:
        if not path.exists():
            path.write_bytes(build_jpeg_with_exif(**kwargs))


def seed_database_if_empty() -> None:
    """Populate SQLite with realistic smallholder demonstration farms if empty."""
    init_db()
    ensure_sample_photos()

    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM farms").fetchone()["c"]
        if count > 0:
            return

        now = datetime.now(timezone.utc)
        model = get_carbon_model()

        for fmr in SAMPLE_FARMERS:
            conn.execute(
                """
                INSERT INTO farmers (id, name, phone, village, district, state, land_doc_ref, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fmr["id"], fmr["name"], fmr["phone"], fmr["village"],
                    fmr["district"], fmr["state"], fmr["land_doc_ref"], now.isoformat(),
                ),
            )

        sample_export: List[Dict[str, Any]] = []

        for idx, spec in enumerate(SAMPLE_FARMS_SPEC):
            farm_id = spec["id"]
            spatial = compute_plot_spatial_metrics(spec["polygon"])
            existing_farms = [dict(r) for r in conn.execute("SELECT * FROM farms").fetchall()]
            overlaps = check_polygon_overlaps(spec["polygon"], existing_farms)

            verification_status = "VERIFIED_PROTOTYPE" if not overlaps else "FLAGGED_REVIEW"
            created_ts = (now - timedelta(days=30 - idx * 2)).isoformat()

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
                    farm_id, spec["farmer_id"], spec["name"], spec["agroforestry_type"],
                    spec["species"], spec["planting_year"], json.dumps(spatial["polygon_geojson"]),
                    spatial["canonical_poly_hash"], spatial["centroid_lat"], spatial["centroid_lon"],
                    spatial["gross_area_ha"], spatial["core_area_ha"], spatial["core_pixels_10m"],
                    spec["baseline_biomass_t_ha"], 0.24, 5.0, 15.0, verification_status, created_ts,
                ),
            )

            append_audit_event(
                conn,
                farm_id,
                "FARM_REGISTERED",
                {
                    "farmer_id": spec["farmer_id"],
                    "gross_area_ha": spatial["gross_area_ha"],
                    "core_area_ha": spatial["core_area_ha"],
                    "canonical_poly_hash": spatial["canonical_poly_hash"],
                },
                timestamp=created_ts,
            )

            # Log overlap alerts if any
            for ov in overlaps:
                alert_id = f"ALT-OVL-{farm_id}-{ov['existing_farm_id']}"
                conn.execute(
                    """
                    INSERT INTO fraud_alerts (id, farm_id, evidence_id, alert_type, severity, risk_score, explanation, evidence_details_json, created_at, resolved)
                    VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        alert_id, farm_id,
                        "DUPLICATE_PLOT_HASH" if ov["exact_duplicate_hash"] else "POLYGON_OVERLAP_DOUBLE_COUNTING",
                        "CRITICAL", 92,
                        f"Polygon overlaps {ov['overlap_pct_of_new_plot']}% ({ov['intersection_ha']} ha, IoU={ov['iou']}) with registered farm {ov['existing_farm_name']} ({ov['existing_farm_id']}).",
                        json.dumps(ov),
                        created_ts,
                    ),
                )
                append_audit_event(conn, farm_id, "FRAUD_ALERT_TRIGGERED", {"alert_id": alert_id, **ov}, timestamp=created_ts)

            # Multi-date Sentinel-2 / Sentinel-1 observations & biomass estimates
            latest_est = None
            latest_obs = None
            for step_i, (obs_date, season, ndvi_target, cloud_pct) in enumerate(spec["timeline"]):
                obs = synthesize_satellite_observation(farm_id, obs_date, season, ndvi_target, cloud_pct)
                obs_id = f"OBS-{farm_id}-{step_i+1}"
                grid = generate_spatial_ndvi_grid(
                    spatial["polygon_geojson"],
                    obs["ndvi_mean"],
                    obs["s1_vv_db"],
                    seed_key=f"{farm_id}-{obs_date}",
                )
                obs_ts = f"{obs_date}T06:00:00+00:00"
                conn.execute(
                    """
                    INSERT INTO satellite_observations (
                        id, farm_id, obs_date, season, data_source, cloud_cover_pct,
                        optical_valid_pct, radar_fallback_used, b2_blue, b4_red, b5_re1, b8_nir,
                        ndvi_mean, ndre_mean, evi_mean, s1_vv_db, s1_vh_db, s1_vh_vv_ratio,
                        ndvi_grid_json, is_simulated_label, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        obs_id, farm_id, obs_date, season, obs["data_source"], obs["cloud_cover_pct"],
                        obs["optical_valid_pct"], int(obs["radar_fallback_used"]),
                        obs["b2_blue"], obs["b4_red"], obs["b5_re1"], obs["b8_nir"],
                        obs["ndvi_mean"], obs["ndre_mean"], obs["evi_mean"],
                        obs["s1_vv_db"], obs["s1_vh_db"], obs["s1_vh_vv_ratio"],
                        json.dumps(grid), obs["is_simulated_label"], obs_ts,
                    ),
                )

                est = model.estimate_biomass_and_carbon(
                    ndvi=obs["ndvi_mean"],
                    ndre=obs["ndre_mean"],
                    evi=obs["evi_mean"],
                    s1_vv_db=obs["s1_vv_db"],
                    s1_vh_db=obs["s1_vh_db"],
                    cloud_cover_pct=obs["cloud_cover_pct"],
                    gross_area_ha=spatial["gross_area_ha"],
                    core_area_ha=spatial["core_area_ha"],
                    core_pixels_10m=spatial["core_pixels_10m"],
                    baseline_biomass_t_ha=spec["baseline_biomass_t_ha"],
                )
                est_id = f"EST-{farm_id}-{step_i+1}"
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
                        json.dumps(est["assumptions"]), obs_ts,
                    ),
                )
                latest_est = est
                latest_obs = obs

            append_audit_event(
                conn,
                farm_id,
                "BIOMASS_ESTIMATED",
                {
                    "obs_date": latest_obs["obs_date"],
                    "sensor_mode": latest_est["sensor_mode"],
                    "agb_ci_lower_t_ha": latest_est["agb_ci_lower_t_ha"],
                    "co2e_conservatively_issuable_t": latest_est["co2e_conservatively_issuable_t"],
                },
                timestamp=(now - timedelta(days=5)).isoformat(),
            )

            # Seed realistic EXIF-tagged photo evidence for each farm
            is_fraud_plot = farm_id == "FARM-FRD-06"
            photo_bytes = build_jpeg_with_exif(
                lat=spatial["centroid_lat"] if not is_fraud_plot else None,
                lon=spatial["centroid_lon"] if not is_fraud_plot else None,
                capture_dt_str=(now - timedelta(days=3)).strftime("%Y:%m:%d %H:%M:%S"),
                tree_density="high",
                label_text=f"{farm_id} FIELD CHECK",
                seed=100 + idx,
                strip_exif=is_fraud_plot,
            )
            ev_filename = f"{farm_id}_field_evidence.jpg"
            ev_path = UPLOADS_DIR / ev_filename
            ev_path.write_bytes(photo_bytes)

            farm_row = dict(conn.execute("SELECT * FROM farms WHERE id = ?", (farm_id,)).fetchone())
            meta, ev_alerts = evaluate_evidence_fraud_signals(
                farm=farm_row,
                file_bytes=photo_bytes,
                capture_lat=spatial["centroid_lat"],
                capture_lon=spatial["centroid_lon"],
                claimed_tree_presence=True,
                offline_captured=True,
                upload_ts=now - timedelta(days=2),
                existing_evidence=[],
                latest_sat_obs=latest_obs,
            )
            ev_id = f"EVD-{farm_id}-01"
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
                    ev_id, farm_id, spec["farmer_id"], f"/uploads/{ev_filename}", ev_filename,
                    meta["file_sha256"], meta["perceptual_dhash"], 1,
                    spatial["centroid_lat"], spatial["centroid_lon"],
                    meta["exif_lat"], meta["exif_lon"], meta["exif_timestamp"],
                    meta["exif_camera"], int(meta["exif_present"]),
                    (now - timedelta(days=2)).isoformat(), 1,
                    "Field verification capture along eastern bund" if not is_fraud_plot else "Uploaded stripped photo without EXIF",
                    "FLAGGED" if ev_alerts else "VERIFIED",
                ),
            )
            append_audit_event(
                conn,
                farm_id,
                "EVIDENCE_UPLOADED",
                {"evidence_id": ev_id, "sha256": meta["file_sha256"], "dhash": meta["perceptual_dhash"]},
                timestamp=(now - timedelta(days=2)).isoformat(),
            )

            for a_i, al in enumerate(ev_alerts):
                al_id = f"ALT-{farm_id}-EV-{a_i+1}"
                conn.execute(
                    """
                    INSERT INTO fraud_alerts (id, farm_id, evidence_id, alert_type, severity, risk_score, explanation, evidence_details_json, created_at, resolved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        al_id, farm_id, ev_id, al["alert_type"], al["severity"],
                        al["risk_score"], al["explanation"], json.dumps(al["evidence_details"]),
                        (now - timedelta(days=2)).isoformat(),
                    ),
                )

            # Issue Carbon Passport for every farm
            chain = verify_farm_chain(conn, farm_id)
            passport_id = f"CK-PASS-2026-{1001 + idx}"
            conn.execute(
                """
                INSERT INTO carbon_passports (passport_id, farm_id, issued_at, model_version, head_hash, verification_status, summary_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    passport_id, farm_id, (now - timedelta(days=1)).isoformat(),
                    latest_est["model_version"], chain["head_hash"],
                    verification_status, json.dumps({"co2e_issuable_t": latest_est["co2e_conservatively_issuable_t"]}),
                ),
            )

            sample_export.append({
                "farm_id": farm_id,
                "name": spec["name"],
                "farmer": SAMPLE_FARMERS[idx]["name"],
                "district": SAMPLE_FARMERS[idx]["district"],
                "state": SAMPLE_FARMERS[idx]["state"],
                "gross_area_ha": spatial["gross_area_ha"],
                "core_area_ha": spatial["core_area_ha"],
                "polygon_geojson": spatial["polygon_geojson"],
                "latest_issuable_co2e_t": latest_est["co2e_conservatively_issuable_t"],
            })

        (DATA_DIR / "sample_farms.json").write_text(json.dumps(sample_export, indent=2), encoding="utf-8")

