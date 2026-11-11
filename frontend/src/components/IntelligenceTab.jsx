import { useState } from "react";
import { CloudRain, Cpu, Info, Play, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { api } from "../api";

export default function IntelligenceTab({
  farms,
  selectedFarmId,
  onSelectFarm,
  dossier,
  modelMetrics,
  onRefreshAll,
  t,
}) {
  const [cloudPct, setCloudPct] = useState(14);
  const [ndviOverride, setNdviOverride] = useState(0.66);
  const [seasonLabel, setSeasonLabel] = useState("Live Sensitivity Check");
  const [running, setRunning] = useState(false);

  const est = dossier?.latest_estimate;
  const farm = dossier?.farm;
  const obs = dossier?.latest_observation;

  const handleRunPipeline = async (e) => {
    e.preventDefault();
    if (!selectedFarmId) return;
    setRunning(true);
    try {
      await api.runEstimation(selectedFarmId, {
        season: cloudPct > 50 ? "Monsoon Cloud Scenario (Radar Fallback)" : seasonLabel,
        cloud_cover_pct: Number(cloudPct),
        ndvi_override: Number(ndviOverride),
      });
      await onRefreshAll(selectedFarmId);
    } finally {
      setRunning(false);
    }
  };

  const maxAxis = est ? Math.max(45, est.agb_ci_upper_t_ha * 1.15) : 50;
  const lowPct = est ? (est.agb_ci_lower_t_ha / maxAxis) * 100 : 20;
  const ptPct = est ? (est.agb_point_t_ha / maxAxis) * 100 : 40;
  const highPct = est ? (est.agb_ci_upper_t_ha / maxAxis) * 100 : 60;

  return (
    <div className="space-y-6">
      <div className="ck-card p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
          <div>
            <h3 className="text-base font-bold text-[#0D2818] flex items-center gap-2">
              <Cpu className="w-5 h-5 text-emerald-700" />
              {t("ai_title")}
            </h3>
            <p className="text-xs text-slate-500">{t("ai_sub")}</p>
          </div>
          <select
            value={selectedFarmId || ""}
            onChange={(e) => onSelectFarm(e.target.value)}
            className="text-sm font-semibold bg-[#FAF8F4] border border-[#E5DFD1] rounded-lg px-3 py-2 text-[#0D2818]"
          >
            {farms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.gross_area_ha} ha)
              </option>
            ))}
          </select>
        </div>

        <form onSubmit={handleRunPipeline} className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end bg-[#FAF8F4] p-4 rounded-xl border border-[#E5DFD1]">
          <div>
            <label className="block text-xs font-bold text-[#0D2818] mb-1">
              {t("ai_cloud_lbl")}: <span className="font-mono">{cloudPct}%</span>
            </label>
            <input
              type="range"
              min="0"
              max="95"
              value={cloudPct}
              onChange={(e) => setCloudPct(Number(e.target.value))}
              className="w-full accent-[#0D2818]"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0% Clear</span>
              <span className="text-blue-700 font-bold">&gt;50% SAR Fallback</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-[#0D2818] mb-1">
              {t("ai_ndvi_lbl")}: <span className="font-mono">{ndviOverride}</span>
            </label>
            <input
              type="range"
              min="0.20"
              max="0.85"
              step="0.01"
              value={ndviOverride}
              onChange={(e) => setNdviOverride(Number(e.target.value))}
              className="w-full accent-emerald-700"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>0.20 Sparse</span>
              <span>0.85 Dense</span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-[#0D2818] mb-1">{t("ai_preset")}</label>
            <div className="flex gap-1.5">
              <button
                type="button"
                onClick={() => {
                  setCloudPct(10);
                  setNdviOverride(0.69);
                  setSeasonLabel("Clear Post-Monsoon Run");
                }}
                className="flex-1 text-[11px] font-semibold py-2 px-2 rounded-lg bg-white border border-[#E5DFD1] hover:bg-[#F3EFE6]"
              >
                {t("ai_clear_optical")}
              </button>
              <button
                type="button"
                onClick={() => {
                  setCloudPct(88);
                  setNdviOverride(0.65);
                  setSeasonLabel("Monsoon Cloud-Blocked");
                }}
                className="flex-1 text-[11px] font-semibold py-2 px-2 rounded-lg bg-blue-50 text-blue-800 border border-blue-200 hover:bg-blue-100"
              >
                {t("ai_monsoon_preset")}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={running}
            className="inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-[#0D2818] text-white text-xs font-bold hover:bg-[#163A24] disabled:opacity-60"
          >
            <Play className="w-4 h-4" />
            {running ? t("ai_running") : t("ai_run_btn")}
          </button>
        </form>
      </div>

      {est && farm && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6 ck-card p-5 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-bold text-[#0D2818]">{t("ai_ci_title")}</h4>
              {obs?.radar_fallback_used ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-blue-100 text-blue-800 text-[11px] font-bold shrink-0">
                  <CloudRain className="w-3.5 h-3.5" /> {t("ai_radar_active")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold shrink-0">
                  <ShieldCheck className="w-3.5 h-3.5" /> {t("ai_optical_fusion")}
                </span>
              )}
            </div>

            <div className="bg-[#FAF8F4] p-4 rounded-xl border border-[#E5DFD1]">
              <div className="text-xs text-slate-600 mb-3">
                Above-Ground Biomass (AGB) Density (t dry matter / ha)
              </div>

              <div className="relative h-14 mt-4 mb-2">
                <div className="absolute top-6 left-0 right-0 h-2 bg-slate-200 rounded-full" />
                <div
                  className="absolute top-5 h-4 bg-emerald-200 border border-emerald-500 rounded-full"
                  style={{ left: `${lowPct}%`, width: `${Math.max(2, highPct - lowPct)}%` }}
                />
                <div
                  className="absolute top-1 flex flex-col items-center -translate-x-1/2"
                  style={{ left: `${lowPct}%` }}
                >
                  <span className="font-mono text-[11px] font-extrabold text-emerald-900 bg-emerald-100 px-1.5 rounded">
                    {est.agb_ci_lower_t_ha}
                  </span>
                  <div className="w-0.5 h-7 bg-emerald-800" />
                </div>
                <div
                  className="absolute top-4 w-3 h-6 bg-[#0D2818] rounded -translate-x-1/2"
                  style={{ left: `${ptPct}%` }}
                />
                <div
                  className="absolute top-1 flex flex-col items-center -translate-x-1/2"
                  style={{ left: `${highPct}%` }}
                >
                  <span className="font-mono text-[11px] font-semibold text-slate-600">
                    {est.agb_ci_upper_t_ha}
                  </span>
                  <div className="w-0.5 h-7 bg-slate-400" />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[#E5DFD1] text-xs">
                <div>
                  <div className="text-slate-500">{t("ai_lower_used")}</div>
                  <div className="font-mono font-extrabold text-base text-emerald-800">
                    {est.agb_ci_lower_t_ha} t/ha
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">{t("ai_median")}</div>
                  <div className="font-mono font-bold text-base text-[#0D2818]">
                    {est.agb_point_t_ha} t/ha
                  </div>
                </div>
                <div>
                  <div className="text-slate-500">{t("ai_ci_width")}</div>
                  <div className="font-mono font-bold text-base text-amber-800">
                    ±{(est.ci_width_t_ha / 2).toFixed(2)} t/ha
                  </div>
                </div>
              </div>
            </div>

            <div className="text-xs text-slate-600 space-y-1 bg-white border border-[#E5DFD1] p-3.5 rounded-xl">
              <div className="font-bold text-[#0D2818]">{t("ai_why_lower")}</div>
              <p>{t("ai_why_lower_body")} ({farm.core_pixels_10m} core 10m px)</p>
            </div>
          </div>

          <div className="lg:col-span-6 ck-card p-5">
            <h4 className="text-sm font-bold text-[#0D2818] mb-3">
              {t("ai_ipcc_title")} ({farm.gross_area_ha} ha)
            </h4>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-2 border-b border-[#F3EFE6]">
                <span className="text-slate-700">{t("ai_step1")}</span>
                <span className="font-mono font-bold">{est.agb_lower_total_t} t</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#F3EFE6]">
                <span className="text-slate-700">{t("ai_step2")} ({est.assumptions?.root_to_shoot_ratio})</span>
                <span className="font-mono font-bold">+{est.bgb_lower_total_t} t</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#F3EFE6]">
                <span className="text-slate-700">{t("ai_step3")}</span>
                <span className="font-mono font-bold">{est.total_biomass_lower_t} t</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#F3EFE6] text-amber-800">
                <span>{t("ai_step4")} ({est.assumptions?.leakage_deduction_pct}%)</span>
                <span className="font-mono">−{est.baseline_total_t} t</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#F3EFE6] bg-[#FAF8F4] px-2 rounded">
                <span className="font-bold text-[#0D2818]">{t("ai_step5")}</span>
                <span className="font-mono font-extrabold text-[#0D2818]">{est.net_additional_biomass_t} t</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#F3EFE6]">
                <span className="text-slate-700">{t("ai_step6")}</span>
                <span className="font-mono font-bold text-[#0D2818]">{est.carbon_tC} tC</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#F3EFE6]">
                <span className="text-slate-700">{t("ai_step7")}</span>
                <span className="font-mono font-bold">{est.co2e_gross_t} tCO₂e</span>
              </div>
              <div className="flex justify-between py-2.5 bg-emerald-50 border border-emerald-200 px-3 rounded-lg text-emerald-900">
                <span className="font-extrabold">
                  {t("ai_step8")} ({est.assumptions?.permanence_buffer_pct}%)
                </span>
                <span className="font-mono font-extrabold text-base">{est.co2e_conservatively_issuable_t} tCO₂e</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {modelMetrics && (
        <div className="ck-card p-5 grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 space-y-3">
            <h4 className="text-sm font-bold text-[#0D2818] flex items-center gap-2">
              <SlidersHorizontal className="w-4 h-4 text-[#163A24]" />
              {t("ai_val_title")}
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
              <div className="bg-[#FAF8F4] p-3 rounded-lg border border-[#E5DFD1]">
                <div className="text-slate-500">Optical Held-Out R²</div>
                <div className="font-mono font-extrabold text-lg text-[#0D2818]">
                  {modelMetrics.optical_r2_heldout}
                </div>
                <div className="text-[11px] text-slate-500">RMSE: {modelMetrics.optical_rmse_t_ha} t/ha</div>
              </div>
              <div className="bg-[#FAF8F4] p-3 rounded-lg border border-[#E5DFD1]">
                <div className="text-slate-500">Optical 95% CI Coverage</div>
                <div className="font-mono font-extrabold text-lg text-emerald-800">
                  {modelMetrics.optical_95ci_empirical_coverage_pct}%
                </div>
                <div className="text-[11px] text-slate-500">Target ≥90% held-out</div>
              </div>
              <div className="bg-[#FAF8F4] p-3 rounded-lg border border-[#E5DFD1]">
                <div className="text-slate-500">SAR Radar 95% Coverage</div>
                <div className="font-mono font-extrabold text-lg text-blue-800">
                  {modelMetrics.radar_95ci_empirical_coverage_pct}%
                </div>
                <div className="text-[11px] text-slate-500">RMSE: {modelMetrics.radar_rmse_t_ha} t/ha</div>
              </div>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3 text-xs text-amber-950 flex gap-2">
              <Info className="w-4 h-4 shrink-0 mt-0.5 text-amber-700" />
              <div>
                <span className="font-mono">{modelMetrics.model_version}</span> · {modelMetrics.n_total_plots} synthetic calibration plots ({modelMetrics.calibration_dataset}). SOC, dead wood &amp; litter excluded conservatively.
              </div>
            </div>
          </div>

          <div className="lg:col-span-5 space-y-2">
            <h4 className="text-sm font-bold text-[#0D2818]">{t("ai_feat_title")}</h4>
            <div className="space-y-2 pt-1">
              {modelMetrics.feature_importances.map((fi) => (
                <div key={fi.feature} className="text-xs">
                  <div className="flex justify-between font-mono mb-0.5">
                    <span>{fi.feature}</span>
                    <span>{(fi.importance * 100).toFixed(1)}%</span>
                  </div>
                  <div className="w-full h-2 bg-[#F3EFE6] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#163A24] rounded-full"
                      style={{ width: `${Math.min(100, fi.importance * 220)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
