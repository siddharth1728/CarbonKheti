"""
Carbon Fraud Radar: automated multi-signal integrity verification engine.

Note on Integrity: Fraud checks act as risk-weighted audit triggers (not foolproof truth);
EXIF metadata can be forged on commodity devices, so CarbonKheti cross-validates photo
evidence against satellite trajectories, perceptual hashes, and Shapely spatial geometry.
"""

import hashlib
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from PIL import ExifTags, Image

from backend.config import (
    DHASH_SIMILARITY_MAX_BITS,
    EXIF_TIME_MISMATCH_HOURS,
    IMPOSSIBLE_TRAVEL_KMH,
    MAX_EXIF_GPS_OUTSIDE_METERS,
    OVERLAP_IOU_ALERT_THRESHOLD,
)
from backend.geo_engine import haversine_distance_meters, point_distance_to_polygon_meters


def compute_sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compute_perceptual_dhash(image_bytes: bytes, hash_size: int = 8) -> str:
    """
    Compute a 64-bit Difference Hash (dHash) using Pillow + NumPy so visually identical
    or re-compressed/cropped photos are detected even when SHA-256 differs.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        gray = img.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        arr = np.asarray(gray, dtype=np.int16)
        diff = arr[:, 1:] > arr[:, :-1]
        bits = "".join("1" if b else "0" for b in diff.flatten())
        return f"{int(bits, 2):016x}"


def dhash_hamming_distance(h1: str, h2: str) -> int:
    if not h1 or not h2 or len(h1) != len(h2):
        return 64
    x = int(h1, 16) ^ int(h2, 16)
    return bin(x).count("1")


def _rational_to_float(val: Any) -> float:
    if isinstance(val, tuple) and len(val) == 2 and val[1] != 0:
        return float(val[0]) / float(val[1])
    return float(val)


def _dms_to_decimal(dms: Any, ref: str) -> Optional[float]:
    try:
        d = _rational_to_float(dms[0])
        m = _rational_to_float(dms[1])
        s = _rational_to_float(dms[2])
        dec = d + m / 60.0 + s / 3600.0
        if ref in ("S", "W"):
            dec = -dec
        return round(dec, 6)
    except Exception:
        return None


def extract_exif_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """Extract camera, capture timestamp, and GPS coordinates from JPEG EXIF headers."""
    result: Dict[str, Any] = {
        "exif_present": False,
        "exif_lat": None,
        "exif_lon": None,
        "exif_timestamp": None,
        "exif_camera": None,
    }
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            exif = img.getexif()
            if not exif or len(exif) == 0:
                return result
            result["exif_present"] = True

            tag_map = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
            make = str(tag_map.get("Make", "")).strip()
            model = str(tag_map.get("Model", "")).strip()
            if make or model:
                result["exif_camera"] = f"{make} {model}".strip()

            dt_orig = tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")
            if not dt_orig:
                exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
                if exif_ifd:
                    dt_orig = exif_ifd.get(36867) or exif_ifd.get(36868)
            if dt_orig:
                result["exif_timestamp"] = str(dt_orig).strip()

            gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
            if gps_ifd:
                gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
                lat_dms = gps_tags.get("GPSLatitude")
                lat_ref = gps_tags.get("GPSLatitudeRef", "N")
                lon_dms = gps_tags.get("GPSLongitude")
                lon_ref = gps_tags.get("GPSLongitudeRef", "E")
                if lat_dms and lon_dms:
                    result["exif_lat"] = _dms_to_decimal(lat_dms, str(lat_ref))
                    result["exif_lon"] = _dms_to_decimal(lon_dms, str(lon_ref))
    except Exception:
        pass
    return result


def build_jpeg_with_exif(
    width: int = 480,
    height: int = 320,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    capture_dt_str: Optional[str] = None,
    camera_make: str = "CarbonKheti-FieldCam",
    tree_density: str = "high",
    label_text: str = "AGROFORESTRY FIELD EVIDENCE",
    seed: int = 1,
    strip_exif: bool = False,
) -> bytes:
    """Create a realistic synthetic field photograph JPEG with optional genuine EXIF GPS & timestamp."""
    from PIL import ImageDraw

    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (width, height), (218, 228, 210))
    draw = ImageDraw.Draw(img)

    # Sky & horizon gradient
    for y in range(int(height * 0.42)):
        c = int(175 + 60 * (1 - y / (height * 0.42)))
        draw.line([(0, y), (width, y)], fill=(int(c * 0.78), int(c * 0.90), c))
    # Soil & crop ground
    for y in range(int(height * 0.42), height):
        g_tone = 92 if tree_density == "high" else 68
        r_tone = 74 if tree_density == "high" else 112
        draw.line([(0, y), (width, y)], fill=(r_tone, g_tone + (y % 7), 45))

    # Draw stylized agroforestry trees or barren land depending on tree_density
    if tree_density == "high":
        for i in range(7):
            tx = int(45 + i * 64 + rng.integers(-10, 10))
            ty = int(height * 0.48 + rng.integers(-12, 18))
            draw.rectangle([tx - 5, ty, tx + 5, ty + 62], fill=(92, 64, 42))
            draw.ellipse([tx - 30, ty - 45, tx + 30, ty + 18], fill=(28 + i * 3, 105 + (i % 3) * 14, 44))
            draw.ellipse([tx - 20, ty - 58, tx + 22, ty - 5], fill=(42, 130, 56))
    elif tree_density == "barren":
        for i in range(18):
            rx = int(rng.integers(20, width - 20))
            ry = int(rng.integers(int(height * 0.48), height - 20))
            draw.ellipse([rx - 14, ry - 4, rx + 14, ry + 4], fill=(138, 118, 86))

    draw.rectangle([8, height - 30, width - 8, height - 8], fill=(13, 40, 24))
    draw.text((14, height - 24), f"{label_text} | {camera_make}", fill=(245, 240, 228))

    buf = io.BytesIO()
    if strip_exif:
        img.save(buf, format="JPEG", quality=88)
        return buf.getvalue()

    exif = img.getexif()
    exif[0x010F] = camera_make
    exif[0x0110] = "CK-Android-Field-v2"
    dt_val = capture_dt_str or datetime.now(timezone.utc).strftime("%Y:%m:%d %H:%M:%S")
    exif[0x0132] = dt_val
    exif[0x9003] = dt_val

    if lat is not None and lon is not None:
        from PIL.TiffImagePlugin import IFDRational

        def _to_dms(deg: float):
            ad = abs(deg)
            d = int(ad)
            m_float = (ad - d) * 60.0
            m = int(m_float)
            s = round((m_float - m) * 60.0 * 100.0)
            return (IFDRational(d, 1), IFDRational(m, 1), IFDRational(s, 100))

        exif[0x8825] = {
            1: "N" if lat >= 0 else "S",
            2: _to_dms(lat),
            3: "E" if lon >= 0 else "W",
            4: _to_dms(lon),
        }

    img.save(buf, format="JPEG", quality=88, exif=exif)
    return buf.getvalue()


def _parse_exif_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(dt_str[:19], fmt).replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def evaluate_evidence_fraud_signals(
    farm: Dict[str, Any],
    file_bytes: bytes,
    capture_lat: Optional[float],
    capture_lon: Optional[float],
    claimed_tree_presence: bool,
    offline_captured: bool,
    upload_ts: datetime,
    existing_evidence: List[Dict[str, Any]],
    latest_sat_obs: Optional[Dict[str, Any]],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Run automated Fraud Radar checks on an incoming farmer photo + GPS evidence submission.
    Returns (extracted_metadata, list_of_triggered_alerts).
    """
    sha256 = compute_sha256_bytes(file_bytes)
    dhash = compute_perceptual_dhash(file_bytes)
    exif = extract_exif_metadata(file_bytes)

    alerts: List[Dict[str, Any]] = []
    poly_geojson = json.loads(farm["polygon_geojson"]) if isinstance(farm["polygon_geojson"], str) else farm["polygon_geojson"]

    # 1. Missing EXIF metadata check
    if not exif["exif_present"]:
        alerts.append({
            "alert_type": "EXIF_METADATA_MISSING",
            "severity": "MEDIUM",
            "risk_score": 45,
            "explanation": "Uploaded photograph has no EXIF metadata (stripped or downloaded from messaging app/web).",
            "evidence_details": {"sha256": sha256[:16], "exif_present": False},
        })
    elif exif["exif_lat"] is None or exif["exif_lon"] is None:
        alerts.append({
            "alert_type": "EXIF_GPS_MISSING",
            "severity": "MEDIUM",
            "risk_score": 38,
            "explanation": "EXIF header present but geotag GPS coordinates are missing.",
            "evidence_details": {"camera": exif["exif_camera"], "exif_timestamp": exif["exif_timestamp"]},
        })

    # 2. GPS-in-Polygon check (both EXIF GPS and app-captured GPS)
    for label, lat, lon in [
        ("EXIF_GPS", exif["exif_lat"], exif["exif_lon"]),
        ("APP_GPS", capture_lat, capture_lon),
    ]:
        if lat is None or lon is None:
            continue
        if abs(lat) < 0.001 and abs(lon) < 0.001:
            alerts.append({
                "alert_type": "SUSPICIOUS_NULL_ISLAND_GPS",
                "severity": "HIGH",
                "risk_score": 85,
                "explanation": f"{label} reported (0, 0) coordinates (Null Island / mock GPS fault).",
                "evidence_details": {"source": label, "lat": lat, "lon": lon},
            })
            continue
        inside, dist_m = point_distance_to_polygon_meters(lat, lon, poly_geojson)
        if not inside and dist_m > MAX_EXIF_GPS_OUTSIDE_METERS:
            sev = "CRITICAL" if dist_m > 500 else "HIGH"
            score = 88 if dist_m > 500 else 72
            alerts.append({
                "alert_type": "GPS_OUTSIDE_FARM_BOUNDARY",
                "severity": sev,
                "risk_score": score,
                "explanation": (
                    f"{label} location ({lat:.5f}, {lon:.5f}) falls {dist_m:.1f} m outside the registered farm polygon "
                    f"(tolerance {MAX_EXIF_GPS_OUTSIDE_METERS:.0f} m)."
                ),
                "evidence_details": {"source": label, "lat": lat, "lon": lon, "distance_outside_m": dist_m},
            })

    # 3. EXIF Timestamp vs Upload Time inconsistency (unless flagged offline capture)
    exif_dt = _parse_exif_dt(exif["exif_timestamp"])
    if exif_dt is not None:
        hours_diff = (upload_ts - exif_dt).total_seconds() / 3600.0
        if hours_diff < -2.0:
            alerts.append({
                "alert_type": "EXIF_FUTURE_TIMESTAMP",
                "severity": "HIGH",
                "risk_score": 78,
                "explanation": f"EXIF capture timestamp ({exif['exif_timestamp']}) is in the future relative to server UTC.",
                "evidence_details": {"exif_timestamp": exif["exif_timestamp"], "hours_diff": round(hours_diff, 1)},
            })
        elif hours_diff > EXIF_TIME_MISMATCH_HOURS and not offline_captured:
            alerts.append({
                "alert_type": "EXIF_STALE_TIMESTAMP",
                "severity": "MEDIUM",
                "risk_score": 52,
                "explanation": (
                    f"Photo was captured {hours_diff:.1f} hours before upload without offline-queue provenance."
                ),
                "evidence_details": {"exif_timestamp": exif["exif_timestamp"], "hours_stale": round(hours_diff, 1)},
            })

    # 4. Reused Farmer Photograph (Exact SHA-256 + Perceptual dHash)
    for prev in existing_evidence:
        if prev["file_sha256"] == sha256:
            alerts.append({
                "alert_type": "REUSED_PHOTO_EXACT_SHA256",
                "severity": "CRITICAL",
                "risk_score": 95,
                "explanation": (
                    f"Exact file byte match (SHA-256) with prior evidence {prev['id']} on farm {prev['farm_id']}."
                ),
                "evidence_details": {"matched_evidence_id": prev["id"], "matched_farm_id": prev["farm_id"], "sha256": sha256[:16]},
            })
            break
        hamming = dhash_hamming_distance(dhash, prev["perceptual_dhash"])
        if hamming <= DHASH_SIMILARITY_MAX_BITS:
            alerts.append({
                "alert_type": "REUSED_PHOTO_PERCEPTUAL_DHASH",
                "severity": "HIGH",
                "risk_score": 84,
                "explanation": (
                    f"Visually identical/re-compressed photo detected via Perceptual dHash "
                    f"(Hamming distance {hamming}/64 bits vs evidence {prev['id']} on farm {prev['farm_id']})."
                ),
                "evidence_details": {
                    "matched_evidence_id": prev["id"],
                    "matched_farm_id": prev["farm_id"],
                    "hamming_bits": hamming,
                    "dhash": dhash,
                },
            })
            break

    # 5. Impossible travel check against same farmer's recent geotagged uploads
    ref_lat = exif["exif_lat"] if exif["exif_lat"] is not None else capture_lat
    ref_lon = exif["exif_lon"] if exif["exif_lon"] is not None else capture_lon
    if ref_lat is not None and ref_lon is not None:
        for prev in existing_evidence:
            if prev["farmer_id"] != farm["farmer_id"]:
                continue
            p_lat = prev["exif_lat"] if prev["exif_lat"] is not None else prev["capture_lat"]
            p_lon = prev["exif_lon"] if prev["exif_lon"] is not None else prev["capture_lon"]
            if p_lat is None or p_lon is None:
                continue
            try:
                prev_dt = datetime.fromisoformat(prev["upload_timestamp"])
                if prev_dt.tzinfo is None:
                    prev_dt = prev_dt.replace(tzinfo=timezone.utc)
                dt_h = abs((upload_ts - prev_dt).total_seconds()) / 3600.0
                if 0.01 < dt_h < 12.0:
                    dist_km = haversine_distance_meters(ref_lat, ref_lon, p_lat, p_lon) / 1000.0
                    speed_kmh = dist_km / dt_h
                    if speed_kmh > IMPOSSIBLE_TRAVEL_KMH and dist_km > 20.0:
                        alerts.append({
                            "alert_type": "IMPOSSIBLE_TRAVEL_VELOCITY",
                            "severity": "CRITICAL",
                            "risk_score": 90,
                            "explanation": (
                                f"Farmer submitted geotagged photos {dist_km:.1f} km apart within {dt_h:.2f} hours "
                                f"({speed_kmh:.0f} km/h > {IMPOSSIBLE_TRAVEL_KMH:.0f} km/h limit)."
                            ),
                            "evidence_details": {"distance_km": round(dist_km, 2), "speed_kmh": round(speed_kmh, 1)},
                        })
                        break
            except Exception:
                continue

    # 6. Cross-modal Satellite NDVI vs. Photo Claim check
    if claimed_tree_presence and latest_sat_obs is not None:
        ndvi = float(latest_sat_obs["ndvi_mean"])
        if ndvi < 0.24 and float(latest_sat_obs["cloud_cover_pct"]) <= 50.0:
            alerts.append({
                "alert_type": "PHOTO_VS_SATELLITE_DISCREPANCY",
                "severity": "HIGH",
                "risk_score": 76,
                "explanation": (
                    f"Photo claims active tree cover, but latest cloud-free Sentinel-2 NDVI is {ndvi:.2f} "
                    f"(consistent with bare soil or fallow land)."
                ),
                "evidence_details": {"ndvi_mean": ndvi, "obs_date": latest_sat_obs["obs_date"]},
            })

    meta = {
        "file_sha256": sha256,
        "perceptual_dhash": dhash,
        **exif,
    }
    return meta, alerts


def evaluate_vegetation_and_carbon_anomalies(
    farm_id: str,
    observations: List[Dict[str, Any]],
    estimates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Detect abrupt NDVI drops (possible reversal/clearing) or physically implausible carbon spikes."""
    alerts: List[Dict[str, Any]] = []
    if len(observations) >= 2:
        sorted_obs = sorted(observations, key=lambda o: o["obs_date"])
        prev, curr = sorted_obs[-2], sorted_obs[-1]
        ndvi_delta = float(curr["ndvi_mean"]) - float(prev["ndvi_mean"])
        if ndvi_delta <= -0.22 and float(curr["cloud_cover_pct"]) <= 50.0:
            alerts.append({
                "alert_type": "UNUSUAL_VEGETATION_DROP",
                "severity": "HIGH",
                "risk_score": 79,
                "explanation": (
                    f"Sharp NDVI decline of {ndvi_delta:.2f} ({prev['ndvi_mean']:.2f} → {curr['ndvi_mean']:.2f}) "
                    f"between {prev['obs_date']} and {curr['obs_date']}; possible tree harvesting or fire reversal."
                ),
                "evidence_details": {"prev_ndvi": prev["ndvi_mean"], "curr_ndvi": curr["ndvi_mean"], "delta": round(ndvi_delta, 3)},
            })

    if len(estimates) >= 2:
        sorted_est = sorted(estimates, key=lambda e: e["obs_date"])
        prev_e, curr_e = sorted_est[-2], sorted_est[-1]
        agb_jump = float(curr_e["agb_point_t_ha"]) - float(prev_e["agb_point_t_ha"])
        if agb_jump > 26.0:
            alerts.append({
                "alert_type": "SUSPICIOUS_CARBON_JUMP",
                "severity": "HIGH",
                "risk_score": 74,
                "explanation": (
                    f"Estimated AGB jumped +{agb_jump:.1f} t/ha in one monitoring step; exceeds plausible annual "
                    f"agroforestry increment and requires VVB review."
                ),
                "evidence_details": {"prev_agb_t_ha": prev_e["agb_point_t_ha"], "curr_agb_t_ha": curr_e["agb_point_t_ha"]},
            })

    return alerts


def compute_farm_risk_summary(alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate active fraud alerts into a bounded 0-100 Risk Score and status label."""
    active = [a for a in alerts if not a.get("resolved")]
    if not active:
        return {"risk_score": 4, "risk_level": "LOW", "active_alert_count": 0}
    max_s = max(a["risk_score"] for a in active)
    # Compound slightly for multiple independent flags
    compounded = min(100, int(round(max_s + 6 * (len(active) - 1))))
    if compounded >= 75:
        level = "CRITICAL"
    elif compounded >= 45:
        level = "ELEVATED"
    else:
        level = "MODERATE"
    return {"risk_score": compounded, "risk_level": level, "active_alert_count": len(active)}
