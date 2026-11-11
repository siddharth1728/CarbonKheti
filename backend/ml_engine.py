"""
AI Carbon Intelligence Engine using Scikit-learn Bootstrap Random Forest + Conformal Calibration.

Scientific & Technical Integrity Notice:
- Trained on a clearly labeled Synthetic Reference Calibration Dataset modeled after
  Indian agroforestry allometric curves (e.g. Poplar/Wheat, Teak/Bund, Mango Horti-silviculture)
  and GEDI/Sentinel-2/Sentinel-1 proxy distributions.
- Not an audited registry calibration model; built to demonstrate full statistical uncertainty,
  bootstrap 95% confidence intervals, radar fallback under monsoon cloud cover, and IPCC-aligned
  conservative lower-bound carbon math.
"""

import hashlib
import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from backend.config import (
    CALIBRATION_LABEL,
    CLOUD_RADAR_FALLBACK_THRESHOLD_PCT,
    CO2_TO_C_RATIO,
    DEFAULT_LEAKAGE_DEDUCTION_PCT,
    DEFAULT_PERMANENCE_BUFFER_PCT,
    DEFAULT_ROOT_TO_SHOOT_RATIO,
    IPCC_CARBON_FRACTION,
    MODEL_VERSION,
)


OPTICAL_FEATURES = ["ndvi", "ndre", "evi", "s1_vv_db", "s1_vh_db", "s1_vh_vv_ratio", "core_area_ha"]
RADAR_ONLY_FEATURES = ["s1_vv_db", "s1_vh_db", "s1_vh_vv_ratio", "core_area_ha"]


class CarbonIntelligenceModel:
    """Bootstrap ensemble of Random Forest models for Optical-Primary & Radar-Fallback AGB estimation."""

    def __init__(self, n_bootstrap: int = 35, random_state: int = 42):
        self.n_bootstrap = n_bootstrap
        self.random_state = random_state
        self.optical_models: List[RandomForestRegressor] = []
        self.radar_models: List[RandomForestRegressor] = []
        self.optical_conformal_q: float = 1.5
        self.radar_conformal_q: float = 3.2
        self.metrics: Dict[str, Any] = {}
        self._train_and_calibrate()

    def _generate_synthetic_calibration_dataset(self, n_samples: int = 260) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Generate reproducible synthetic reference plots (clearly labeled demonstration data)
        capturing realistic optical saturation, C-band SAR backscatter response, and allometric noise.
        """
        rng = np.random.default_rng(self.random_state)

        # Latent true above-ground biomass (t dry biomass / ha), 2 to 65 t/ha across Indian agroforestry
        true_agb = rng.uniform(2.5, 62.0, size=n_samples)
        core_area_ha = rng.uniform(0.20, 4.50, size=n_samples)

        # Optical indices saturate smoothly with biomass + realistic phenology/soil noise
        ndvi = 0.20 + 0.64 * (1.0 - np.exp(-0.048 * true_agb)) + rng.normal(0, 0.032, n_samples)
        ndre = 0.14 + 0.48 * (1.0 - np.exp(-0.036 * true_agb)) + rng.normal(0, 0.028, n_samples)
        evi = 0.16 + 0.56 * (1.0 - np.exp(-0.040 * true_agb)) + rng.normal(0, 0.035, n_samples)

        ndvi = np.clip(ndvi, 0.12, 0.90)
        ndre = np.clip(ndre, 0.08, 0.72)
        evi = np.clip(evi, 0.10, 0.84)

        # Sentinel-1 C-band SAR (dB): VH responds more strongly to volume scattering, saturates around ~45 t/ha
        s1_vv_db = -13.2 + 4.4 * (1.0 - np.exp(-0.042 * true_agb)) + rng.normal(0, 0.65, n_samples)
        s1_vh_db = -20.5 + 6.8 * (1.0 - np.exp(-0.046 * true_agb)) + rng.normal(0, 0.75, n_samples)
        s1_vh_vv_ratio = s1_vh_db - s1_vv_db  # cross-polarization ratio in dB

        X_opt = np.column_stack([ndvi, ndre, evi, s1_vv_db, s1_vh_db, s1_vh_vv_ratio, core_area_ha])
        X_rad = np.column_stack([s1_vv_db, s1_vh_db, s1_vh_vv_ratio, core_area_ha])
        return X_opt, X_rad, true_agb

    def _fit_bootstrap_ensemble(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators_per_boot: int = 24,
    ) -> List[RandomForestRegressor]:
        rng = np.random.default_rng(self.random_state)
        n = len(y_train)
        models = []
        for b in range(self.n_bootstrap):
            idx = rng.integers(0, n, size=n)
            rf = RandomForestRegressor(
                n_estimators=n_estimators_per_boot,
                max_depth=8,
                min_samples_leaf=3,
                random_state=self.random_state + b,
                n_jobs=1,
            )
            rf.fit(X_train[idx], y_train[idx])
            models.append(rf)
        return models

    def _predict_raw_ci(self, models: List[RandomForestRegressor], X: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        preds = np.array([m.predict(X) for m in models])  # (B, N)
        point = np.median(preds, axis=0)
        low = np.percentile(preds, 2.5, axis=0)
        high = np.percentile(preds, 97.5, axis=0)
        return point, low, high

    def _train_and_calibrate(self) -> None:
        X_opt, X_rad, y = self._generate_synthetic_calibration_dataset()
        idx_all = np.arange(len(y))
        idx_train_cal, idx_test = train_test_split(idx_all, test_size=0.22, random_state=self.random_state)
        idx_train, idx_cal = train_test_split(idx_train_cal, test_size=0.25, random_state=self.random_state)

        self.optical_models = self._fit_bootstrap_ensemble(X_opt[idx_train], y[idx_train])
        self.radar_models = self._fit_bootstrap_ensemble(X_rad[idx_train], y[idx_train])

        # Split-conformal calibration factor so empirical 95% CI achieves >=90-95% coverage
        _, opt_cal_low, opt_cal_high = self._predict_raw_ci(self.optical_models, X_opt[idx_cal])
        opt_cal_scores = np.maximum(opt_cal_low - y[idx_cal], y[idx_cal] - opt_cal_high)
        self.optical_conformal_q = max(0.8, float(np.quantile(opt_cal_scores, 0.94)))

        _, rad_cal_low, rad_cal_high = self._predict_raw_ci(self.radar_models, X_rad[idx_cal])
        rad_cal_scores = np.maximum(rad_cal_low - y[idx_cal], y[idx_cal] - rad_cal_high)
        self.radar_conformal_q = max(2.2, float(np.quantile(rad_cal_scores, 0.96)))

        # Evaluate on held-out test plots
        opt_pt, opt_l, opt_h = self._predict_raw_ci(self.optical_models, X_opt[idx_test])
        opt_l_c = np.maximum(0.0, opt_l - self.optical_conformal_q)
        opt_h_c = opt_h + self.optical_conformal_q
        opt_cov = float(np.mean((y[idx_test] >= opt_l_c) & (y[idx_test] <= opt_h_c)))

        rad_pt, rad_l, rad_h = self._predict_raw_ci(self.radar_models, X_rad[idx_test])
        rad_l_c = np.maximum(0.0, rad_l - self.radar_conformal_q)
        rad_h_c = rad_h + self.radar_conformal_q
        rad_cov = float(np.mean((y[idx_test] >= rad_l_c) & (y[idx_test] <= rad_h_c)))

        # Feature importances averaged across bootstrap
        importances = np.mean([m.feature_importances_ for m in self.optical_models], axis=0)
        feat_imp = [
            {"feature": name, "importance": round(float(val), 4)}
            for name, val in sorted(zip(OPTICAL_FEATURES, importances), key=lambda x: -x[1])
        ]

        self.metrics = {
            "model_version": MODEL_VERSION,
            "calibration_dataset": CALIBRATION_LABEL,
            "n_total_plots": len(y),
            "n_train": len(idx_train),
            "n_calibration": len(idx_cal),
            "n_heldout_test": len(idx_test),
            "n_bootstrap_ensembles": self.n_bootstrap,
            "optical_r2_heldout": round(float(r2_score(y[idx_test], opt_pt)), 3),
            "optical_rmse_t_ha": round(float(math.sqrt(mean_squared_error(y[idx_test], opt_pt))), 2),
            "optical_95ci_empirical_coverage_pct": round(opt_cov * 100.0, 1),
            "radar_r2_heldout": round(float(r2_score(y[idx_test], rad_pt)), 3),
            "radar_rmse_t_ha": round(float(math.sqrt(mean_squared_error(y[idx_test], rad_pt))), 2),
            "radar_95ci_empirical_coverage_pct": round(rad_cov * 100.0, 1),
            "feature_importances": feat_imp,
        }

    def estimate_biomass_and_carbon(
        self,
        ndvi: float,
        ndre: float,
        evi: float,
        s1_vv_db: float,
        s1_vh_db: float,
        cloud_cover_pct: float,
        gross_area_ha: float,
        core_area_ha: float,
        core_pixels_10m: int,
        baseline_biomass_t_ha: float = 3.2,
        root_to_shoot_ratio: float = DEFAULT_ROOT_TO_SHOOT_RATIO,
        leakage_pct: float = DEFAULT_LEAKAGE_DEDUCTION_PCT,
        permanence_buffer_pct: float = DEFAULT_PERMANENCE_BUFFER_PCT,
    ) -> Dict[str, Any]:
        """
        Run full Scikit-learn biomass prediction + 95% confidence interval + conservative IPCC carbon math.
        """
        s1_vh_vv = s1_vh_db - s1_vv_db
        radar_fallback = cloud_cover_pct > CLOUD_RADAR_FALLBACK_THRESHOLD_PCT
        eff_ha = core_area_ha if core_area_ha > 0.05 else gross_area_ha

        if radar_fallback:
            sensor_mode = "Sentinel-1 SAR Radar Fallback (Monsoon Cloud Resilience)"
            X = np.array([[s1_vv_db, s1_vh_db, s1_vh_vv, eff_ha]])
            pt, low, high = self._predict_raw_ci(self.radar_models, X)
            conformal_pad = self.radar_conformal_q
        else:
            sensor_mode = "Sentinel-2 Optical Primary + Sentinel-1 SAR Fusion"
            X = np.array([[ndvi, ndre, evi, s1_vv_db, s1_vh_db, s1_vh_vv, eff_ha]])
            pt, low, high = self._predict_raw_ci(self.optical_models, X)
            conformal_pad = self.optical_conformal_q

        agb_point = float(pt[0])
        raw_half_width = max(0.5, (float(high[0]) - float(low[0])) / 2.0) + conformal_pad

        # Smallholder pixel-count penalty: plots with <64 core 10m pixels get wider uncertainty
        pixel_penalty = 1.0 + max(0.0, (64.0 - min(64.0, float(core_pixels_10m))) / 90.0)
        # Cloud-fraction penalty even when optical is usable
        cloud_penalty = 1.0 + (0.28 if radar_fallback else max(0.0, (cloud_cover_pct - 15.0) / 180.0))

        adj_half_width = raw_half_width * pixel_penalty * cloud_penalty
        agb_ci_lower = max(0.0, agb_point - adj_half_width)
        agb_ci_upper = agb_point + adj_half_width

        # Scale per-hectare conservative AGB lower bound to gross farm area
        # (Core pixels measure pure vegetation away from 10m edge; scaled transparently to gross parcel)
        agb_lower_total_t = agb_ci_lower * gross_area_ha
        bgb_lower_total_t = agb_lower_total_t * root_to_shoot_ratio
        total_biomass_lower_t = agb_lower_total_t + bgb_lower_total_t

        # Baseline standing biomass (also including root-to-shoot so comparison is apples-to-apples)
        baseline_total_t = baseline_biomass_t_ha * (1.0 + root_to_shoot_ratio) * gross_area_ha
        gross_additional_t = max(0.0, total_biomass_lower_t - baseline_total_t)
        net_additional_biomass_t = gross_additional_t * (1.0 - leakage_pct / 100.0)

        # IPCC 2006 exact chain: Biomass -> x 0.47 = tC -> x 44/12 = tCO2e -> - permanence buffer
        carbon_tC = net_additional_biomass_t * IPCC_CARBON_FRACTION
        co2e_gross_t = carbon_tC * CO2_TO_C_RATIO
        co2e_conservatively_issuable_t = co2e_gross_t * (1.0 - permanence_buffer_pct / 100.0)

        return {
            "model_version": MODEL_VERSION,
            "sensor_mode": sensor_mode,
            "radar_fallback_used": radar_fallback,
            "agb_point_t_ha": round(agb_point, 2),
            "agb_ci_lower_t_ha": round(agb_ci_lower, 2),
            "agb_ci_upper_t_ha": round(agb_ci_upper, 2),
            "ci_width_t_ha": round(agb_ci_upper - agb_ci_lower, 2),
            "agb_lower_total_t": round(agb_lower_total_t, 3),
            "bgb_lower_total_t": round(bgb_lower_total_t, 3),
            "total_biomass_lower_t": round(total_biomass_lower_t, 3),
            "baseline_total_t": round(baseline_total_t, 3),
            "net_additional_biomass_t": round(net_additional_biomass_t, 3),
            "carbon_tC": round(carbon_tC, 3),
            "co2e_gross_t": round(co2e_gross_t, 3),
            "co2e_conservatively_issuable_t": round(co2e_conservatively_issuable_t, 3),
            "assumptions": {
                "carbon_fraction_ipcc": IPCC_CARBON_FRACTION,
                "co2_to_c_ratio": round(CO2_TO_C_RATIO, 4),
                "root_to_shoot_ratio": root_to_shoot_ratio,
                "baseline_biomass_t_ha": baseline_biomass_t_ha,
                "leakage_deduction_pct": leakage_pct,
                "permanence_buffer_pct": permanence_buffer_pct,
                "pixel_uncertainty_multiplier": round(pixel_penalty, 3),
                "cloud_uncertainty_multiplier": round(cloud_penalty, 3),
                "excluded_pools": ["Soil Organic Carbon (SOC)", "Dead Wood", "Litter (conservatively excluded)"],
                "calibration_note": CALIBRATION_LABEL,
            },
        }


def synthesize_satellite_observation(
    farm_id: str,
    obs_date: str,
    season: str,
    ndvi_target: float,
    cloud_cover_pct: float,
    seed_salt: str = "",
) -> Dict[str, Any]:
    """
    Create a physically consistent, explicitly labeled [SIMULATED / PROXY] Sentinel-2 + Sentinel-1
    observation record for demonstration when live Copernicus/GEE credentials are not attached.
    """
    seed = int(hashlib.md5(f"{farm_id}|{obs_date}|{seed_salt}".encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)

    ndvi = float(np.clip(ndvi_target, 0.12, 0.89))
    # Derive physically plausible Sentinel-2 bands (L2A surface reflectance 0..1)
    red = float(np.clip(0.18 - 0.14 * ndvi + rng.normal(0, 0.005), 0.025, 0.25))
    nir = float(np.clip(red * (1.0 + ndvi) / max(0.08, 1.0 - ndvi), 0.12, 0.62))
    blue = float(np.clip(red * 0.68 + rng.normal(0, 0.004), 0.015, 0.15))
    re1 = float(np.clip(red + 0.42 * (nir - red), 0.05, 0.45))

    calc_ndvi = (nir - red) / (nir + red)
    calc_ndre = (nir - re1) / (nir + re1)
    calc_evi = 2.5 * (nir - red) / (nir + 6.0 * red - 7.5 * blue + 1.0)

    # Physically coupled Sentinel-1 C-band backscatter
    s1_vv_db = float(np.clip(-13.4 + 5.2 * (ndvi - 0.15) + rng.normal(0, 0.35), -15.5, -7.2))
    s1_vh_db = float(np.clip(-20.8 + 8.1 * (ndvi - 0.15) + rng.normal(0, 0.45), -23.0, -11.5))

    optical_valid_pct = max(0.0, round(100.0 - cloud_cover_pct, 1))
    radar_fallback = cloud_cover_pct > CLOUD_RADAR_FALLBACK_THRESHOLD_PCT

    return {
        "obs_date": obs_date,
        "season": season,
        "data_source": "Sentinel-1 GRD (Primary) + Sentinel-2 L2A (Cloud-Masked)" if radar_fallback else "Sentinel-2 L2A + Sentinel-1 GRD",
        "cloud_cover_pct": round(cloud_cover_pct, 1),
        "optical_valid_pct": optical_valid_pct,
        "radar_fallback_used": radar_fallback,
        "b2_blue": round(blue, 4),
        "b4_red": round(red, 4),
        "b5_re1": round(re1, 4),
        "b8_nir": round(nir, 4),
        "ndvi_mean": round(calc_ndvi, 4),
        "ndre_mean": round(calc_ndre, 4),
        "evi_mean": round(float(np.clip(calc_evi, 0.05, 0.90)), 4),
        "s1_vv_db": round(s1_vv_db, 2),
        "s1_vh_db": round(s1_vh_db, 2),
        "s1_vh_vv_ratio": round(s1_vh_db - s1_vv_db, 2),
        "is_simulated_label": "SIMULATED_SENTINEL_PROXY_DEMO",
    }


# Singleton initialized once at module load
_MODEL_INSTANCE: Optional[CarbonIntelligenceModel] = None


def get_carbon_model() -> CarbonIntelligenceModel:
    global _MODEL_INSTANCE
    if _MODEL_INSTANCE is None:
        _MODEL_INSTANCE = CarbonIntelligenceModel()
    return _MODEL_INSTANCE
