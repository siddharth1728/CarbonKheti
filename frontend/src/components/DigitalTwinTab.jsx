import { useEffect, useState } from "react";
import {
  Calendar,
  CloudRain,
  Layers,
  PenTool,
  Plus,
  RotateCcw,
  Save,
  Sun,
  TrendingUp,
} from "lucide-react";
import { api } from "../api";
import { formatAcresAndHa } from "../i18n";
import LeafletMap from "./LeafletMap";

export default function DigitalTwinTab({
  farms,
  farmers,
  selectedFarmId,
  onSelectFarm,
  dossier,
  onRefreshAll,
  t,
  viewMode = "farmer",
  lang = "en",
}) {
  const [layerMode, setLayerMode] = useState("ndvi");
  const [showBuffer, setShowBuffer] = useState(true);
  const [compareIdxA, setCompareIdxA] = useState(0);
  const [compareIdxB, setCompareIdxB] = useState(0);

  const [showRegister, setShowRegister] = useState(false);
  const [drawingMode, setDrawingMode] = useState(false);
  const [drawnPoints, setDrawnPoints] = useState([]);
  const [form, setForm] = useState({
    farmer_id: farmers?.[0]?.id || "",
    name: lang === "te" ? "కొత్త చెట్ల పొలం" : "New Agroforestry Plot",
    agroforestry_type: "Boundary / Bund Planting",
    species: "Teak + Subabul",
    planting_year: 2023,
    baseline_biomass_t_ha: 3.0,
    initial_ndvi: 0.64,
    initial_cloud_cover_pct: 12.0,
  });
  const [submitting, setSubmitting] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    if (farmers?.length && !form.farmer_id) {
      setForm((prev) => ({ ...prev, farmer_id: farmers[0].id }));
    }
  }, [farmers, form.farmer_id]);

  const observations = dossier?.observations || [];
  useEffect(() => {
    if (observations.length > 0) {
      setCompareIdxA(0);
      setCompareIdxB(observations.length - 1);
    }
  }, [selectedFarmId, observations.length]);

  const obsA = observations[compareIdxA] || null;
  const obsB = observations[compareIdxB] || null;
  const activeObs = obsB || dossier?.latest_observation;

  const handleLoadSampleBoundary = () => {
    setDrawnPoints([
      [78.9021, 18.1032],
      [78.9032, 18.1033],
      [78.9031, 18.1042],
      [78.9020, 18.1041],
    ]);
    setDrawingMode(false);
  };

  const handleRegisterFarm = async (e) => {
    e.preventDefault();
    if (drawnPoints.length < 3) {
      setMsg({ type: "error", text: "Tap at least 3 corners on the map (or load sample polygon)." });
      return;
    }
    setSubmitting(true);
    setMsg(null);
    try {
      const closed = [...drawnPoints, drawnPoints[0]];
      const res = await api.registerFarm({
        ...form,
        planting_year: Number(form.planting_year),
        baseline_biomass_t_ha: Number(form.baseline_biomass_t_ha),
        initial_ndvi: Number(form.initial_ndvi),
        initial_cloud_cover_pct: Number(form.initial_cloud_cover_pct),
        polygon_geojson: { type: "Polygon", coordinates: [closed] },
      });
      setDrawnPoints([]);
      setDrawingMode(false);
      setShowRegister(false);
      setMsg({ type: "success", text: `${res.farm.name} registered & checked successfully!` });
      await onRefreshAll(res.farm.id);
    } catch (err) {
      setMsg({ type: "error", text: err.message });
    } finally {
      setSubmitting(false);
    }
  };

  const scoreA = obsA ? Math.round(obsA.ndvi_mean * 100) : 0;
  const scoreB = obsB ? Math.round(obsB.ndvi_mean * 100) : 0;
  const scoreDiff = scoreB - scoreA;

  return (
    <div className="space-y-6">
      <div className="ck-card p-3.5 sm:p-4 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
        <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2.5 sm:gap-3 w-full lg:w-auto">
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 shrink-0">
              {t("twin_active_farm")}
            </label>
            <select
              value={selectedFarmId || ""}
              onChange={(e) => onSelectFarm(e.target.value)}
              className="w-full sm:w-auto max-w-full min-w-0 text-sm font-semibold bg-[#FAF8F4] border border-[#E5DFD1] rounded-lg px-3 py-2 text-[#0D2818]"
            >
              {farms.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name} ({formatAcresAndHa(f.gross_area_ha, lang)})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-3 sm:inline-flex items-center gap-1 bg-[#FAF8F4] p-1 rounded-lg border border-[#E5DFD1] text-[11px] sm:text-xs font-semibold w-full sm:w-auto">
            <button
              type="button"
              onClick={() => setLayerMode("ndvi")}
              className={`px-2 sm:px-2.5 py-1.5 sm:py-1 rounded-md text-center leading-tight ${layerMode === "ndvi" ? "bg-[#0D2818] text-white" : "text-slate-600"}`}
            >
              {viewMode === "farmer" ? t("ftwin_greenery") : t("twin_s2_ndvi")}
            </button>
            <button
              type="button"
              onClick={() => setLayerMode("sar")}
              className={`px-2 sm:px-2.5 py-1.5 sm:py-1 rounded-md text-center leading-tight ${layerMode === "sar" ? "bg-blue-700 text-white" : "text-slate-600"}`}
            >
              {viewMode === "farmer" ? t("ftwin_radar") : t("twin_s1_sar")}
            </button>
            <button
              type="button"
              onClick={() => setLayerMode("boundary")}
              className={`px-2 sm:px-2.5 py-1.5 sm:py-1 rounded-md text-center leading-tight ${layerMode === "boundary" ? "bg-[#0D2818] text-white" : "text-slate-600"}`}
            >
              {viewMode === "farmer" ? t("ftwin_outline") : t("twin_boundary_only")}
            </button>
          </div>

          <label className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 cursor-pointer py-1">
            <input
              type="checkbox"
              checked={showBuffer}
              onChange={(e) => setShowBuffer(e.target.checked)}
              className="accent-[#0D2818] w-4 h-4"
            />
            {viewMode === "farmer" ? t("ftwin_inner_zone") : t("twin_show_buffer")}
          </label>
        </div>

        <button
          type="button"
          onClick={() => {
            setShowRegister(!showRegister);
            setDrawingMode(!showRegister);
          }}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-1.5 px-3.5 py-2.5 sm:py-2 min-h-[42px] rounded-lg bg-[#0D2818] text-white text-xs font-bold hover:bg-[#163A24] transition shrink-0"
        >
          <Plus className="w-4 h-4" />
          {showRegister ? t("twin_close_drawer") : t("twin_draw_btn")}
        </button>
      </div>

      {msg && (
        <div
          className={`px-4 py-3 rounded-xl text-xs font-semibold border ${
            msg.type === "error"
              ? "bg-red-50 border-red-200 text-red-800"
              : "bg-emerald-50 border-emerald-200 text-emerald-800"
          }`}
        >
          {msg.text}
        </div>
      )}

      {showRegister && (
        <form onSubmit={handleRegisterFarm} className="ck-card p-5 border-l-4 border-l-amber-500 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-[#0D2818] flex items-center gap-2">
                <PenTool className="w-4 h-4 text-amber-600" />
                {t("twin_draw_title")}
              </h3>
              <p className="text-xs text-slate-500">
                {t("twin_vertices")}: <strong className="font-mono">{drawnPoints.length}</strong> · {t("twin_draw_sub")}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleLoadSampleBoundary}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-[#F3EFE6] text-[#0D2818] hover:bg-[#E5DFD1]"
              >
                {t("twin_load_sample")}
              </button>
              <button
                type="button"
                onClick={() => setDrawnPoints([])}
                className="px-2.5 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 inline-flex items-center gap-1"
              >
                <RotateCcw className="w-3.5 h-3.5" /> {t("twin_clear")}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">{t("twin_farmer")}</label>
              <select
                value={form.farmer_id}
                onChange={(e) => setForm({ ...form, farmer_id: e.target.value })}
                className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2.5 py-2 bg-[#FAF8F4]"
              >
                {farmers.map((fm) => (
                  <option key={fm.id} value={fm.id}>
                    {fm.name} ({fm.district})
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">{t("twin_farm_name")}</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2.5 py-2"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">{t("twin_type")}</label>
              <select
                value={form.agroforestry_type}
                onChange={(e) => setForm({ ...form, agroforestry_type: e.target.value })}
                className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2.5 py-2 bg-[#FAF8F4]"
              >
                <option>Boundary / Bund Planting</option>
                <option>Agri-Silviculture / Alley Cropping</option>
                <option>Horti-Silviculture</option>
                <option>Silvopasture</option>
                <option>Windbreaks &amp; Shelterbelts</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">{t("twin_species")}</label>
              <input
                type="text"
                value={form.species}
                onChange={(e) => setForm({ ...form, species: e.target.value })}
                className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2.5 py-2"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">{t("twin_year")}</label>
              <input
                type="number"
                value={form.planting_year}
                onChange={(e) => setForm({ ...form, planting_year: e.target.value })}
                className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2.5 py-2"
              />
            </div>
            {viewMode === "auditor" && (
              <>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">{t("twin_baseline")}</label>
                  <input
                    type="number"
                    step="0.1"
                    value={form.baseline_biomass_t_ha}
                    onChange={(e) => setForm({ ...form, baseline_biomass_t_ha: e.target.value })}
                    className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2.5 py-2"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-600 mb-1">{t("twin_demo_ndvi")}</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.15"
                    max="0.88"
                    value={form.initial_ndvi}
                    onChange={(e) => setForm({ ...form, initial_ndvi: e.target.value })}
                    className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2.5 py-2"
                  />
                </div>
              </>
            )}
            <div className="flex items-end">
              <button
                type="submit"
                disabled={submitting}
                className="w-full inline-flex items-center justify-center gap-1.5 px-4 py-2 rounded-lg bg-emerald-700 text-white text-xs font-bold hover:bg-emerald-800 disabled:opacity-60"
              >
                <Save className="w-4 h-4" />
                {submitting ? "…" : t("twin_save_run")}
              </button>
            </div>
          </div>
        </form>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-8 ck-card p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs font-bold text-[#0D2818] flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-emerald-700" />
              {dossier?.farm?.name}
            </div>
            {activeObs && viewMode === "auditor" && (
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-50 text-amber-900 border border-amber-200">
                {activeObs.is_simulated_label} · {activeObs.obs_date}
              </span>
            )}
            {activeObs && viewMode === "farmer" && (
              <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200">
                {activeObs.obs_date}
              </span>
            )}
          </div>
          <LeafletMap
            farms={farms}
            selectedFarmId={selectedFarmId}
            onSelectFarm={onSelectFarm}
            ndviGrid={activeObs?.ndvi_grid || []}
            layerMode={layerMode}
            showInnerBuffer={showBuffer}
            corePolygonGeojson={dossier?.farm?.core_polygon_geojson}
            drawingMode={drawingMode}
            drawnPoints={drawnPoints}
            onAddDrawPoint={(pt) => setDrawnPoints((prev) => [...prev, pt])}
            heightClass="h-[300px] sm:h-[420px] lg:h-[460px]"
            viewMode={viewMode}
            lang={lang}
          />
        </div>

        <div className="lg:col-span-4 space-y-4">
          {dossier?.farm && (
            <div className="ck-card p-4 space-y-3">
              <h4 className="text-sm font-bold text-[#0D2818]">
                {viewMode === "farmer" ? t("ftwin_area_card") : t("twin_pixel_title")}
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-[#FAF8F4] p-2.5 rounded-lg border border-[#E5DFD1]">
                  <div className="text-slate-500 text-[11px]">{t("twin_gross_parcel")}</div>
                  <div className="font-bold text-sm text-[#0D2818]">
                    {formatAcresAndHa(dossier.farm.gross_area_ha, lang)}
                  </div>
                  {viewMode === "auditor" && (
                    <div className="text-[11px] text-slate-500 font-mono">
                      ~{dossier.farm.gross_pixels_10m} total 10m px
                    </div>
                  )}
                </div>
                <div className="bg-[#FAF8F4] p-2.5 rounded-lg border border-[#E5DFD1]">
                  <div className="text-slate-500 text-[11px]">{t("twin_after_buffer")}</div>
                  <div className="font-bold text-sm text-emerald-800">
                    {formatAcresAndHa(dossier.farm.core_area_ha, lang)}
                  </div>
                  {viewMode === "auditor" && (
                    <div className="text-[11px] text-slate-500 font-mono">
                      {dossier.farm.core_pixels_10m} pure core px
                    </div>
                  )}
                </div>
              </div>
              <p className="text-[11px] text-slate-600 leading-relaxed">
                {viewMode === "farmer"
                  ? t("ftwin_area_explain")
                  : `${t("twin_pixel_explain")} (−${dossier.farm.edge_loss_pct}% edge area)`}
              </p>
            </div>
          )}

          {observations.length > 0 && (
            <div className="ck-card p-4 space-y-3">
              <h4 className="text-sm font-bold text-[#0D2818] flex items-center gap-1.5">
                {viewMode === "farmer" ? (
                  <TrendingUp className="w-4 h-4 text-emerald-700" />
                ) : (
                  <Calendar className="w-4 h-4 text-[#163A24]" />
                )}
                {viewMode === "farmer" ? t("ftwin_growth_title") : t("twin_compare_title")}
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                    {t("twin_date_a")}
                  </label>
                  <select
                    value={compareIdxA}
                    onChange={(e) => setCompareIdxA(Number(e.target.value))}
                    className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2 py-1.5 bg-[#FAF8F4]"
                  >
                    {observations.map((o, i) => (
                      <option key={o.id} value={i}>
                        {o.obs_date}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[10px] font-bold uppercase text-slate-500 mb-1">
                    {t("twin_date_b")}
                  </label>
                  <select
                    value={compareIdxB}
                    onChange={(e) => setCompareIdxB(Number(e.target.value))}
                    className="w-full text-xs border border-[#E5DFD1] rounded-lg px-2 py-1.5 bg-[#FAF8F4]"
                  >
                    {observations.map((o, i) => (
                      <option key={o.id} value={i}>
                        {o.obs_date}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {obsA && obsB && viewMode === "farmer" && (
                <div className="space-y-3 pt-1">
                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="p-3 rounded-xl bg-[#FAF8F4] border border-[#E5DFD1]">
                      <div className="text-[11px] text-slate-500">{obsA.obs_date}</div>
                      <div className="text-2xl font-extrabold text-[#0D2818] mt-0.5">
                        {scoreA} <span className="text-xs font-normal text-slate-500">/ 100</span>
                      </div>
                      <div className="text-[10px] text-slate-500">{t("ftwin_score_lbl")}</div>
                    </div>
                    <div className="p-3 rounded-xl bg-emerald-50 border border-emerald-200">
                      <div className="text-[11px] text-emerald-800">{obsB.obs_date}</div>
                      <div className="text-2xl font-extrabold text-emerald-800 mt-0.5">
                        {scoreB} <span className="text-xs font-normal text-emerald-700">/ 100</span>
                      </div>
                      <div className="text-[11px] font-bold text-emerald-700">
                        {scoreDiff >= 0 ? `+${scoreDiff}` : scoreDiff} {t("ftwin_growth_gain")} 🌱
                      </div>
                    </div>
                  </div>
                  {obsB.radar_fallback_used ? (
                    <div className="flex items-center gap-1.5 text-xs text-blue-800 bg-blue-50 p-2.5 rounded-lg border border-blue-200">
                      <CloudRain className="w-4 h-4 shrink-0" />
                      {t("ftwin_monsoon_plain")}
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-xs text-emerald-800 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
                      <Sun className="w-4 h-4 shrink-0" />
                      {t("ftwin_clear_plain")}
                    </div>
                  )}
                </div>
              )}

              {obsA && obsB && viewMode === "auditor" && (
                <div className="space-y-2 text-xs pt-1">
                  <div className="grid grid-cols-3 text-[11px] font-bold text-slate-500 border-b border-[#E5DFD1] pb-1">
                    <span>Metric</span>
                    <span className="font-mono">{obsA.obs_date}</span>
                    <span className="font-mono">{obsB.obs_date}</span>
                  </div>
                  <div className="grid grid-cols-3 font-mono">
                    <span className="font-sans text-slate-700">NDVI</span>
                    <span>{obsA.ndvi_mean}</span>
                    <span className="font-bold text-emerald-700">
                      {obsB.ndvi_mean} ({obsB.ndvi_mean - obsA.ndvi_mean >= 0 ? "+" : ""}
                      {(obsB.ndvi_mean - obsA.ndvi_mean).toFixed(3)})
                    </span>
                  </div>
                  <div className="grid grid-cols-3 font-mono">
                    <span className="font-sans text-slate-700">NDRE / EVI</span>
                    <span>{obsA.ndre_mean} / {obsA.evi_mean}</span>
                    <span>{obsB.ndre_mean} / {obsB.evi_mean}</span>
                  </div>
                  <div className="grid grid-cols-3 font-mono">
                    <span className="font-sans text-slate-700">S1 VH (dB)</span>
                    <span>{obsA.s1_vh_db}</span>
                    <span>{obsB.s1_vh_db}</span>
                  </div>
                  <div className="grid grid-cols-3 font-mono">
                    <span className="font-sans text-slate-700">Cloud %</span>
                    <span>{obsA.cloud_cover_pct}%</span>
                    <span className={obsB.radar_fallback_used ? "text-blue-700 font-bold" : ""}>
                      {obsB.cloud_cover_pct}%
                    </span>
                  </div>
                  <div className="pt-1 text-[11px]">
                    {obsB.radar_fallback_used ? (
                      <div className="flex items-center gap-1.5 text-blue-800 bg-blue-50 p-2 rounded-lg border border-blue-200">
                        <CloudRain className="w-4 h-4 shrink-0" />
                        {t("twin_monsoon_msg")}
                      </div>
                    ) : (
                      <div className="flex items-center gap-1.5 text-emerald-800 bg-emerald-50 p-2 rounded-lg border border-emerald-200">
                        <Sun className="w-4 h-4 shrink-0" />
                        {t("twin_clear_msg")}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
