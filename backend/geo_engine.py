"""Geospatial engine using Shapely for polygon validation, 10m inner buffer, overlap IoU, and pixel grids."""

import hashlib
import json
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.ops import transform

from backend.config import INNER_NEGATIVE_BUFFER_M, SENTINEL2_PIXEL_SIZE_M


METERS_PER_DEG_LAT = 111_132.92


def _meters_per_deg_lon(lat_deg: float) -> float:
    return 111_412.84 * math.cos(math.radians(lat_deg))


def project_to_local_meters(geom: Polygon, ref_lat: float, ref_lon: float) -> Polygon:
    """Project WGS84 (lon, lat) polygon into local tangent-plane meters for accurate area & buffering."""
    m_lon = _meters_per_deg_lon(ref_lat)
    return transform(
        lambda x, y: ((x - ref_lon) * m_lon, (y - ref_lat) * METERS_PER_DEG_LAT),
        geom,
    )


def project_from_local_meters(geom: Polygon, ref_lat: float, ref_lon: float) -> Polygon:
    """Inverse transform from local meters back to WGS84 (lon, lat)."""
    m_lon = _meters_per_deg_lon(ref_lat)
    return transform(
        lambda x, y: (ref_lon + x / m_lon, ref_lat + y / METERS_PER_DEG_LAT),
        geom,
    )


def parse_and_validate_polygon(geojson_input: Any) -> Polygon:
    """Parse GeoJSON (Feature, Geometry, or coordinate list) into a valid Shapely Polygon."""
    if isinstance(geojson_input, str):
        geojson_input = json.loads(geojson_input)

    if isinstance(geojson_input, dict):
        if geojson_input.get("type") == "Feature":
            geom = shape(geojson_input["geometry"])
        elif geojson_input.get("type") == "FeatureCollection":
            geom = shape(geojson_input["features"][0]["geometry"])
        else:
            geom = shape(geojson_input)
    elif isinstance(geojson_input, list):
        geom = Polygon(geojson_input)
    else:
        raise ValueError("Unsupported GeoJSON polygon format")

    if not geom.is_valid:
        geom = geom.buffer(0)
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    if geom.geom_type != "Polygon" or geom.is_empty:
        raise ValueError("Geometry must be a non-empty Polygon")
    return geom


def canonical_polygon_hash(geom: Polygon) -> str:
    """Canonical coordinate rounding (6 decimals ~11cm) + SHA-256 to catch exact plot re-registrations."""
    coords = [(round(x, 6), round(y, 6)) for x, y in geom.exterior.coords]
    canon = json.dumps(coords, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def compute_plot_spatial_metrics(geojson_input: Any) -> Dict[str, Any]:
    """
    Compute gross area (ha), 10m inner negative buffer core area (ha),
    10m x 10m Sentinel-2 core pixel count, and core GeoJSON geometry.
    """
    poly = parse_and_validate_polygon(geojson_input)
    centroid = poly.centroid
    ref_lat, ref_lon = centroid.y, centroid.x

    local_poly = project_to_local_meters(poly, ref_lat, ref_lon)
    gross_area_m2 = float(local_poly.area)
    gross_area_ha = gross_area_m2 / 10_000.0

    # 10m inner negative buffer to exclude mixed border pixels (e.g. roads/bunds/neighbors)
    core_local = local_poly.buffer(-INNER_NEGATIVE_BUFFER_M)
    if core_local.is_empty or core_local.area <= 0:
        core_area_m2 = 0.0
        core_geojson = None
        core_pixels = max(1, int(round(gross_area_m2 / (SENTINEL2_PIXEL_SIZE_M ** 2) * 0.25)))
    else:
        if core_local.geom_type == "MultiPolygon":
            core_local = max(core_local.geoms, key=lambda g: g.area)
        core_area_m2 = float(core_local.area)
        core_wgs84 = project_from_local_meters(core_local, ref_lat, ref_lon)
        core_geojson = mapping(core_wgs84)
        core_pixels = max(1, int(round(core_area_m2 / (SENTINEL2_PIXEL_SIZE_M ** 2))))

    core_area_ha = core_area_m2 / 10_000.0
    edge_loss_pct = (1.0 - (core_area_ha / gross_area_ha)) * 100.0 if gross_area_ha > 0 else 100.0

    return {
        "polygon_geojson": mapping(poly),
        "core_polygon_geojson": core_geojson,
        "canonical_poly_hash": canonical_polygon_hash(poly),
        "centroid_lat": round(ref_lat, 6),
        "centroid_lon": round(ref_lon, 6),
        "gross_area_ha": round(gross_area_ha, 4),
        "core_area_ha": round(core_area_ha, 4),
        "core_pixels_10m": core_pixels,
        "gross_pixels_10m": max(1, int(round(gross_area_m2 / 100.0))),
        "edge_loss_pct": round(edge_loss_pct, 1),
    }


def check_polygon_overlaps(
    candidate_geojson: Any,
    existing_farms: List[Dict[str, Any]],
    exclude_farm_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Compute exact Shapely Intersection-over-Union (IoU) and overlap % against existing farms."""
    cand_poly = parse_and_validate_polygon(candidate_geojson)
    c_lat, c_lon = cand_poly.centroid.y, cand_poly.centroid.x
    cand_local = project_to_local_meters(cand_poly, c_lat, c_lon)
    cand_hash = canonical_polygon_hash(cand_poly)

    overlaps = []
    for farm in existing_farms:
        if exclude_farm_id and farm["id"] == exclude_farm_id:
            continue
        other_poly = parse_and_validate_polygon(farm["polygon_geojson"])
        # Quick bounding-box reject
        if not cand_poly.intersects(other_poly):
            continue
        other_local = project_to_local_meters(other_poly, c_lat, c_lon)
        inter_area = cand_local.intersection(other_local).area
        if inter_area <= 1.0:  # ignore < 1 m2 rounding touch
            continue
        union_area = cand_local.union(other_local).area
        iou = inter_area / union_area if union_area > 0 else 0.0
        pct_of_candidate = (inter_area / cand_local.area) * 100.0 if cand_local.area > 0 else 0.0

        overlaps.append({
            "existing_farm_id": farm["id"],
            "existing_farm_name": farm["name"],
            "existing_farmer_id": farm.get("farmer_id"),
            "exact_duplicate_hash": cand_hash == farm.get("canonical_poly_hash"),
            "intersection_ha": round(inter_area / 10_000.0, 4),
            "iou": round(iou, 4),
            "overlap_pct_of_new_plot": round(pct_of_candidate, 2),
        })

    return overlaps


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in meters between two WGS84 points."""
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def point_distance_to_polygon_meters(lat: float, lon: float, polygon_geojson: Any) -> Tuple[bool, float]:
    """Return (is_inside, distance_outside_meters) using Shapely local metric projection."""
    poly = parse_and_validate_polygon(polygon_geojson)
    c_lat, c_lon = poly.centroid.y, poly.centroid.x
    local_poly = project_to_local_meters(poly, c_lat, c_lon)
    m_lon = _meters_per_deg_lon(c_lat)
    pt_local = Point((lon - c_lon) * m_lon, (lat - c_lat) * METERS_PER_DEG_LAT)
    if local_poly.contains(pt_local):
        return True, 0.0
    return False, round(float(local_poly.distance(pt_local)), 2)


def generate_spatial_ndvi_grid(
    polygon_geojson: Any,
    mean_ndvi: float,
    mean_vv_db: float,
    seed_key: str,
    grid_dim: int = 8,
) -> List[Dict[str, Any]]:
    """
    Generate a deterministic spatial 10m-like cell grid clipped inside the farm polygon
    for Living Farm Digital Twin visualization (NDVI & SAR backscatter heatmap cells).
    """
    poly = parse_and_validate_polygon(polygon_geojson)
    minx, miny, maxx, maxy = poly.bounds
    rng = np.random.default_rng(int(hashlib.md5(seed_key.encode()).hexdigest()[:8], 16))

    dx = (maxx - minx) / grid_dim
    dy = (maxy - miny) / grid_dim
    cells = []

    for i in range(grid_dim):
        for j in range(grid_dim):
            x0, x1 = minx + i * dx, minx + (i + 1) * dx
            y0, y1 = miny + j * dy, miny + (j + 1) * dy
            cell_poly = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
            if not poly.intersects(cell_poly):
                continue
            clipped = poly.intersection(cell_poly)
            if clipped.is_empty or clipped.area <= 0:
                continue
            # Slight spatial gradient: bund/border cells slightly higher or lower depending on agroforestry
            dist_center = math.hypot((i + 0.5) / grid_dim - 0.5, (j + 0.5) / grid_dim - 0.5)
            spatial_var = float(rng.normal(0, 0.045)) + (0.03 * (0.5 - dist_center))
            cell_ndvi = float(np.clip(mean_ndvi + spatial_var, 0.08, 0.92))
            cell_vv = float(np.clip(mean_vv_db + rng.normal(0, 0.7), -18.0, -5.0))
            cells.append({
                "bounds": [[round(y0, 6), round(x0, 6)], [round(y1, 6), round(x1, 6)]],
                "geojson": mapping(clipped),
                "ndvi": round(cell_ndvi, 3),
                "vv_db": round(cell_vv, 2),
            })

    return cells

