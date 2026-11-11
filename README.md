# CarbonKheti (PS-13) — Smallholder Agroforestry Carbon Intelligence Platform

**INNOVASIA 2K26 | Team DoSA** *(Harini Konduru, Sabareesh Kovvuri, Nishita Chintalapati, Siddharth G)*

CarbonKheti is an open, conservative, tamper-evident digital **MRV (Measurement, Reporting, and Verification)** prototype engineered for smallholder agroforestry plots. It combines geospatial boundary validation, optical + SAR satellite processing, bootstrap ML uncertainty estimation, automated fraud screening, offline-capable farmer field evidence, and a SHA-256 hash-chained **Carbon Passport**.

---

## Core Capabilities

1. **Living Farm Digital Twin** (`Leaflet` + `Shapely`)
   - Interactive satellite map (`Esri World Imagery` & `OpenStreetMap`) with live polygon drawing.
   - **10m Inner Negative Buffer** to strip mixed boundary pixels on tiny 0.25–2 ha plots and compute exact 10m core pixel counts.
   - Spatial 10m Sentinel-2 NDVI & Sentinel-1 SAR backscatter grids with **Multi-Date Comparison**.
2. **AI Carbon Intelligence Engine** (`Scikit-learn` Bootstrap Random Forest + Conformal Calibration)
   - Optical-Primary (NDVI, NDRE, EVI + SAR) with automatic **Sentinel-1 SAR Radar Fallback** when cloud cover > 50%.
   - **95% Confidence Intervals** that widen automatically under monsoon cloud cover or small core pixel counts.
   - Exact **IPCC 2006 Accounting Chain**: `(AGB_lower + BGB) − Baseline − Leakage → × 0.47 (tC) → × 44/12 (tCO₂e) → − 15% Permanence Buffer`.
3. **Carbon Fraud Radar** (`Pillow` EXIF + `dHash` + `Shapely`)
   - Detects duplicate canonical plot hashes, overlapping polygons (IoU), off-plot GPS, impossible travel velocity, reused photos (SHA-256 + 64-bit Perceptual dHash), stripped/inconsistent EXIF, and photo-vs-NDVI conflicts.
4. **Farmer Evidence Mobile App**
   - Mobile-first capture UI with farmer onboarding, GPS capture, EXIF extraction, and an **Offline-First `localStorage` Sync Queue**.
5. **Carbon Passport & SHA-256 Hash-Chain Audit Trail**
   - Tamper-evident block chain (`GENESIS → FARM_REGISTERED → BIOMASS_ESTIMATED → EVIDENCE_UPLOADED → CARBON_PASSPORT_ISSUED`), live **Tamper Attack Simulation**, and downloadable **HTML/Print-PDF Verification Dossier** + **JSON Audit Proof Bundle**.

---

## Scientific & Technical Integrity Disclosures

- **Demonstration Data**: Satellite time series (`SIMULATED_SENTINEL_PROXY_DEMO`) and the biomass ML calibration dataset (`SYNTHETIC_DEMO_CALIBRATION`) are simulated proxy datasets created for reproducible live demonstration when live GEE/Copernicus credentials and destructive field allometry plots are not attached.
- **Carbon Pools Scope**: Phase 1 estimates **Above-Ground Biomass (AGB)** and **Below-Ground Biomass (BGB via IPCC root-to-shoot 0.24)**; Soil Organic Carbon (SOC), dead wood, and litter are conservatively excluded.
- **Certification**: CarbonKheti generates VVB-ready evidence dossiers and **does not** claim official carbon-credit registry certification (Verra/CCTS VVB audit required).
- **Cost Target**: The `≤ ₹100/ha/year` figure is a project engineering target for automated dMRV at FPO scale and excludes third-party VVB and registry fees.

---

## Quick Start (Local Execution)

### Prerequisites
- Python 3.11+ (`fastapi`, `uvicorn`, `scikit-learn`, `shapely`, `pillow`, `pandas`, `numpy`, `pytest`)
- Node.js 20+ (only needed if rebuilding the React frontend; `frontend/dist` is pre-built)

### 1. Run Backend & Pre-Built Web App (Single Command)
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Then open **http://127.0.0.1:8000** in your browser.

### 2. Development Mode (Hot-Reload Frontend + Backend)
Terminal 1 (Backend):
```powershell
python -m uvicorn backend.main:app --reload --port 8000
```
Terminal 2 (Frontend):
```powershell
cd frontend
npm run dev
```
Open **http://localhost:5173** (proxied automatically to port 8000).

### 3. Run Automated Tests
```powershell
python -m pytest tests/test_carbonkheti.py -v
```

---

## Project Structure

- `backend/` — FastAPI server (`main.py`), SQLite schema (`db.py`), Shapely geospatial engine (`geo_engine.py`), Scikit-learn bootstrap ML & IPCC math (`ml_engine.py`), Fraud Radar (`fraud_engine.py`), SHA-256 hash chain (`hash_chain.py`), HTML dossier generator (`report_generator.py`), and seeded Indian agroforestry dataset (`seed_data.py`).
- `frontend/` — React + Vite + Tailwind CSS + Leaflet geospatial UI.
- `data/` — SQLite database (`carbonkheti.db`), sample farm export (`sample_farms.json`), and EXIF-tagged sample JPEGs (`sample_photos/`).
- `docs/` — [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`JUDGE_DEMO_SCRIPT.md`](docs/JUDGE_DEMO_SCRIPT.md).
- `tests/` — Automated pytest verification suite.

