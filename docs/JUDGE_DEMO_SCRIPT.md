# CarbonKheti PS-13 — Live Judge Demonstration Script

**Team DoSA | INNOVASIA 2K26**

> **Opening Thesis (Memorize):**  
> *"Verification cost doesn't scale down with farm size, so smallholder farmers get priced out of carbon markets. CarbonKheti inverts that: we use free Sentinel optical and radar data, issue credits strictly from the 95% conservative lower bound, and bind every photo, polygon, and calculation in a SHA-256 hash chain."*

---

## 12-Step Live Demonstration Flow (~4 Minutes)

You can also click the **"Judge Demo (0/12)"** button in the top-right header of the web app to jump directly between steps.

1. **Register a Sample Farmer** (`Farmer App` tab)
   - Fill out *Onboard New Smallholder Farmer* (e.g., *Srinivasulu*, Village *Kondapaka*, District *Siddipet*, State *Telangana*) and click **Register Farmer**.
2. **Add a Farm & Draw Geographical Boundary** (`Farm Digital Twin` tab)
   - Click **Draw & Register Farm**, select the new farmer, click vertices on the satellite map (or click **Load Sample 1.2 ha Polygon**), and click **Save & Run Satellite MRV**.
   - Point out the **10m Inner Negative Buffer** (dashed yellow line) and exact 10m Sentinel-2 core pixel arithmetic.
3. **Load Satellite Imagery** (`Farm Digital Twin` tab)
   - Show the **Esri World Satellite Imagery** basemap toggled alongside the **Sentinel-2 NDVI** and **Sentinel-1 SAR** 10m spatial grids.
4. **Display NDVI & Multi-Date Vegetation Change** (`Farm Digital Twin` tab)
   - On the right panel, compare **Date A (2023 Baseline)** vs **Date B (2026 Current)** to show canopy NDVI progression (`+0.35`) and switch to `FARM-MHA-04` to show live monsoon radar fallback.
5. **Run Biomass Estimation Pipeline** (`AI Carbon Engine` tab)
   - Keep **Clear Optical (10% cloud)** and click **Run Biomass Pipeline**. Then slide **Cloud Cover to 88% (Monsoon Preset)** and click **Run Biomass Pipeline** again.
   - Highlight how **Sentinel-1 SAR Radar Fallback** engages automatically and the **95% Confidence Interval widens**.
6. **Inspect 95% Confidence Interval** (`AI Carbon Engine` tab)
   - Show the visual CI bar (`Lower Bound` vs `Median` vs `Upper Bound`) plus held-out empirical coverage (~93% Optical, ~92% SAR) and synthetic calibration disclosure.
7. **Walk Through Conservative Carbon Estimates** (`AI Carbon Engine` tab)
   - Show Steps 1–8: `AGB Lower` + `BGB (×0.24)` − `Baseline` − `Leakage (5%)` → `× 0.47 (tC)` → `× 44/12 (tCO₂e)` − `15% Permanence Buffer` = **Conservatively Issuable CO₂e**.
8. **Upload Farmer Evidence (Online + Offline-First)** (`Farmer App` tab)
   - Toggle **OFFLINE MODE**, load `authentic_telangana_trees.jpg`, click **Save to Offline Queue**, toggle back to **ONLINE**, and click **Sync Now**.
   - Show extracted EXIF camera, GPS coordinates, SHA-256, and Perceptual dHash.
9. **Trigger Fraud Detection Live** (`Fraud Radar` tab)
   - Click **Simulate Reused Photo Attack (SHA/dHash)** or **Simulate Duplicate / Overlapping Plot** (also inspect pre-seeded `FARM-FRD-06`).
   - Show the Risk Score spike, itemized evidence JSON, and clear explanation.
10. **Generate Carbon Passport** (`Carbon Passport` tab)
    - Click **Generate / Refresh Carbon Passport** to mint a digital identity (`CK-PASS-2026-XXXX`) anchored to the latest SHA-256 head hash.
11. **Verify SHA-256 Integrity & Tamper Simulation** (`Carbon Passport` tab)
    - Click **Simulate Tamper Attack** to show Block #2 turning crimson (`❌ TAMPER DETECTED`), then click **Verify Integrity** to prove the stored chain is intact (`✅ ALL BLOCKS VERIFIED`).
12. **Download Verification Report** (`Carbon Passport` tab)
    - Click **Download Verification Report (HTML/PDF)** and **JSON Proof Bundle** to show a VVB-ready tamper-evident dossier.

---

## Rapid-Fire Judge Q&A Reminders
- **Why ×0.47 and ×44/12?** `0.47` is the IPCC 2006 carbon fraction of dry biomass (giving tonnes C); `44/12` converts atomic carbon to molecular `CO₂e` in which credits are traded.
- **Do you measure Soil Organic Carbon (SOC)?** No. NDVI tracks canopy biomass, not soil carbon. SOC, dead wood, and litter are conservatively excluded in Phase 1.
- **Is the ₹100/ha/yr figure proven?** It is an automated dMRV cost target at FPO scale using free Copernicus Sentinel data and open-source Python; it excludes third-party VVB audit and registry issuance fees.
- **Can EXIF be spoofed?** Yes — that is why EXIF is treated as a weighted risk signal alongside Perceptual dHash, impossible travel checks, Shapely polygon overlap, and Sentinel NDVI cross-verification.

