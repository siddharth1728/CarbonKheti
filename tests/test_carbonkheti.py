"""Comprehensive automated tests for CarbonKheti PS-13 backend & E2E workflows."""

import io
import pytest
from fastapi.testclient import TestClient

from backend import config, db, seed_data
from backend.fraud_engine import build_jpeg_with_exif, compute_perceptual_dhash, extract_exif_metadata
from backend.geo_engine import check_polygon_overlaps, compute_plot_spatial_metrics
from backend.main import app
from backend.ml_engine import get_carbon_model


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_carbonkheti.db"
    test_uploads = tmp_path / "uploads"
    test_uploads.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(config, "DB_PATH", test_db)
    monkeypatch.setattr(db, "DB_PATH", test_db)
    monkeypatch.setattr(config, "UPLOADS_DIR", test_uploads)
    monkeypatch.setattr(seed_data, "UPLOADS_DIR", test_uploads)
    from backend import main as main_mod
    monkeypatch.setattr(main_mod, "UPLOADS_DIR", test_uploads)
    return test_db


def test_ml_bootstrap_intervals_and_radar_fallback():
    model = get_carbon_model()
    assert model.metrics["optical_95ci_empirical_coverage_pct"] >= 88.0
    assert model.metrics["radar_95ci_empirical_coverage_pct"] >= 88.0

    clear_res = model.estimate_biomass_and_carbon(
        ndvi=0.66, ndre=0.45, evi=0.52,
        s1_vv_db=-10.2, s1_vh_db=-16.0,
        cloud_cover_pct=10.0,
        gross_area_ha=1.2, core_area_ha=0.82, core_pixels_10m=82,
    )
    monsoon_res = model.estimate_biomass_and_carbon(
        ndvi=0.66, ndre=0.45, evi=0.52,
        s1_vv_db=-10.2, s1_vh_db=-16.0,
        cloud_cover_pct=88.0,
        gross_area_ha=1.2, core_area_ha=0.82, core_pixels_10m=82,
    )
    assert clear_res["radar_fallback_used"] is False
    assert monsoon_res["radar_fallback_used"] is True
    # Radar fallback under cloud cover must widen uncertainty interval
    assert monsoon_res["ci_width_t_ha"] > clear_res["ci_width_t_ha"]
    # Exact IPCC 0.47 & 44/12 relationship check
    expected_tc = round(clear_res["net_additional_biomass_t"] * 0.47, 3)
    assert abs(clear_res["carbon_tC"] - expected_tc) <= 0.01
    assert clear_res["co2e_conservatively_issuable_t"] < clear_res["co2e_gross_t"]


def test_shapely_10m_inner_buffer_and_overlap_iou():
    # ~100m x 100m square near Siddipet -> ~1 ha gross, ~0.64 ha core
    poly = {
        "type": "Polygon",
        "coordinates": [[
            [78.8900, 18.1000],
            [78.89095, 18.1000],
            [78.89095, 18.1009],
            [78.8900, 18.1009],
            [78.8900, 18.1000],
        ]],
    }
    m = compute_plot_spatial_metrics(poly)
    assert 0.85 <= m["gross_area_ha"] <= 1.15
    assert m["core_area_ha"] < m["gross_area_ha"]
    assert m["core_pixels_10m"] > 0

    shifted = {
        "type": "Polygon",
        "coordinates": [[
            [78.8903, 18.1002],
            [78.89125, 18.1002],
            [78.89125, 18.1011],
            [78.8903, 18.1011],
            [78.8903, 18.1002],
        ]],
    }
    overlaps = check_polygon_overlaps(shifted, [{"id": "F1", "name": "Farm 1", "polygon_geojson": poly, "canonical_poly_hash": m["canonical_poly_hash"]}])
    assert len(overlaps) == 1
    assert overlaps[0]["iou"] > 0.25


def test_exif_and_perceptual_dhash():
    jpg = build_jpeg_with_exif(lat=18.0985, lon=78.8942, tree_density="high", seed=5)
    exif = extract_exif_metadata(jpg)
    assert exif["exif_present"] is True
    assert abs(exif["exif_lat"] - 18.0985) < 0.001
    assert abs(exif["exif_lon"] - 78.8942) < 0.001
    dh = compute_perceptual_dhash(jpg)
    assert len(dh) == 16


def test_fastapi_e2e_workflow_and_tamper_detection(isolated_db):
    with TestClient(app) as client:
        # 1. Dashboard loads seeded portfolio
        dash = client.get("/api/dashboard")
        assert dash.status_code == 200
        data = dash.json()
        assert data["summary"]["total_farms"] >= 6

        # 2. Register farmer
        fmr_res = client.post("/api/farmers", json={
            "name": "Test Judge Farmer",
            "village": "Gajwel",
            "district": "Siddipet",
            "state": "Telangana",
            "land_doc_ref": "TS-DEMO-001",
        })
        assert fmr_res.status_code == 200
        farmer_id = fmr_res.json()["farmer"]["id"]

        # 3. Register new non-overlapping farm
        farm_res = client.post("/api/farms", json={
            "farmer_id": farmer_id,
            "name": "Judge Demo Teak Plot",
            "agroforestry_type": "Boundary / Bund Planting",
            "species": "Teak",
            "planting_year": 2022,
            "polygon_geojson": {
                "type": "Polygon",
                "coordinates": [[[78.9500, 18.1500], [78.9511, 18.1500], [78.9511, 18.1510], [78.9500, 18.1510], [78.9500, 18.1500]]],
            },
            "initial_ndvi": 0.65,
        })
        assert farm_res.status_code == 200
        farm_id = farm_res.json()["farm"]["id"]

        # 4. Run monsoon radar fallback estimation
        est_res = client.post(f"/api/farms/{farm_id}/estimate", json={
            "season": "Monsoon Test",
            "cloud_cover_pct": 85.0,
            "ndvi_override": 0.65,
        })
        assert est_res.status_code == 200
        assert est_res.json()["latest_observation"]["radar_fallback_used"] is True

        # 5. Upload authentic EXIF photo evidence
        jpg = build_jpeg_with_exif(lat=18.1505, lon=78.9505, seed=42)
        ev_res = client.post(
            "/api/evidence/upload",
            data={"farm_id": farm_id, "claimed_tree_presence": "true", "capture_lat": "18.1505", "capture_lon": "78.9505"},
            files={"photo": ("field_ok.jpg", io.BytesIO(jpg), "image/jpeg")},
        )
        assert ev_res.status_code == 200
        assert ev_res.json()["status"] == "VERIFIED"

        # 6. Simulate spoofed GPS fraud
        sim_res = client.post("/api/fraud/simulate", json={"farm_id": farm_id, "scenario": "spoofed_gps_exif"})
        assert sim_res.status_code == 200
        assert sim_res.json()["risk_summary"]["active_alert_count"] >= 1

        # 7. Issue Carbon Passport & verify SHA-256 chain intact vs tamper simulation
        pass_res = client.post(f"/api/passports/{farm_id}/issue")
        assert pass_res.status_code == 200
        assert pass_res.json()["chain_verification"]["verified"] is True

        tamper_res = client.get(f"/api/passports/{farm_id}/verify?simulate_tamper_seq=2")
        assert tamper_res.status_code == 200
        assert tamper_res.json()["verified"] is False
        assert tamper_res.json()["broken_at_seq"] == 2

        # 8. Download HTML (English + Telugu) & JSON verification reports
        html_res = client.get(f"/api/passports/{farm_id}/report.html")
        assert html_res.status_code == 200
        assert "CarbonKheti" in html_res.text

        html_te_res = client.get(f"/api/passports/{farm_id}/report.html?lang=te")
        assert html_te_res.status_code == 200
        assert "డిజిటల్ కార్బన్ పాస్‌పోర్ట్" in html_te_res.text

        bundle_res = client.get(f"/api/passports/{farm_id}/bundle.json")
        assert bundle_res.status_code == 200
        assert bundle_res.json()["farm"]["id"] == farm_id
