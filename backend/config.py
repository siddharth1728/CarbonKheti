"""Central scientific, economic, and system constants for CarbonKheti PS-13."""

import os
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if os.environ.get("VERCEL") or not os.access(BASE_DIR, os.W_OK):
    DATA_DIR = Path(tempfile.gettempdir()) / "carbonkheti_data"
else:
    DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
SAMPLE_PHOTOS_DIR = DATA_DIR / "sample_photos"
DB_PATH = DATA_DIR / "carbonkheti.db"

for _d in (DATA_DIR, UPLOADS_DIR, SAMPLE_PHOTOS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Scientific & IPCC 2006 Defaults (explicitly transparent)
IPCC_CARBON_FRACTION = 0.47  # Dry woody biomass carbon fraction (IPCC 2006 Vol 4)
CO2_TO_C_RATIO = 44.0 / 12.0  # Molecular weight ratio CO2 / C (~3.6667)
DEFAULT_ROOT_TO_SHOOT_RATIO = 0.24  # Conservative IPCC tropical/subtropical agroforestry BGB/AGB
DEFAULT_PERMANENCE_BUFFER_PCT = 15.0  # 15% buffer pool held back for reversal risk
DEFAULT_LEAKAGE_DEDUCTION_PCT = 5.0  # 5% conservative leakage deduction

# Remote sensing & smallholder spatial parameters
SENTINEL2_PIXEL_SIZE_M = 10.0  # 10m spatial resolution for B2, B4, B8
INNER_NEGATIVE_BUFFER_M = 10.0  # 10m inner buffer to exclude mixed border pixels
CLOUD_RADAR_FALLBACK_THRESHOLD_PCT = 50.0  # Switch to Sentinel-1 SAR primary when clouds > 50%

# Fraud detection thresholds
OVERLAP_IOU_ALERT_THRESHOLD = 0.05  # Flag any >5% IoU polygon overlap
DHASH_SIMILARITY_MAX_BITS = 8  # Hamming distance <= 8/64 bits flags near-duplicate photo
EXIF_TIME_MISMATCH_HOURS = 48.0  # Flag if EXIF capture differs from upload >48h (unless offline)
IMPOSSIBLE_TRAVEL_KMH = 120.0  # Flag impossible physical movement between geotagged uploads
MAX_EXIF_GPS_OUTSIDE_METERS = 50.0  # Tolerance around boundary before flagging off-plot GPS

# Model metadata
MODEL_VERSION = "CK-AGB-BootstrapRF-v1.2-Demo"
CALIBRATION_LABEL = "SYNTHETIC_DEMO_CALIBRATION (Proxy for GEDI/Allometry)"

# Target Unit Economics (Explicitly labeled as project target, not audited commercial cost)
TARGET_COST_INR_PER_HA_YR = 100.0
TARGET_COST_BREAKDOWN_INR = [
    {"component": "Sentinel-1 & Sentinel-2 Open Imagery", "min_inr": 0, "max_inr": 0, "note": "Free Copernicus / GEE research access"},
    {"component": "Batch Cloud Compute & Audit Storage", "min_inr": 10, "max_inr": 25, "note": "Amortized polygon-level inference"},
    {"component": "Amortized Calibration Reference Plots", "min_inr": 20, "max_inr": 40, "note": "Regional allometric plot calibration"},
    {"component": "Farmer Mobile App / FPO Onboarding", "min_inr": 15, "max_inr": 30, "note": "Self-serve GPS & offline photo capture"},
    {"component": "Targeted QA & Audit Spot Checks", "min_inr": 10, "max_inr": 15, "note": "Risk-triggered by Fraud Radar"},
]

