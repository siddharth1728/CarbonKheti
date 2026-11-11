import {
  AlertTriangle,
  CheckCircle2,
  CloudRain,
  Coins,
  Leaf,
  MapPin,
  ShieldCheck,
  Trees,
} from "lucide-react";
import LeafletMap from "./LeafletMap";

export default function DashboardTab({
  dashboard,
  selectedFarmId,
  onSelectFarm,
  onNavigateTab,
  t,
}) {
  if (!dashboard) return null;
  const { summary, cost_breakdown, historical_trend, farms, recent_alerts } = dashboard;

  const maxCo2e = Math.max(
    1,
    ...farms.map((f) => f.latest_estimate?.co2e_gross_t || 0)
  );

  return (
    <div className="space-y-6">
      {/* KPI Strip */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="ck-card p-5">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500">
            <span>{t("dash_portfolio")}</span>
            <Trees className="w-4 h-4 text-[#163A24]" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0D2818]">
              {summary.total_farms}
            </span>
            <span className="text-sm font-medium text-slate-500">
              ({summary.total_farmers}) {t("dash_farms_farmers")}
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-600">
            {t("dash_gross_core")}:{" "}
            <span className="font-mono font-semibold">{summary.total_gross_hectares} / {summary.total_core_hectares} ha</span>
          </div>
        </div>

        <div className="ck-card p-5">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500">
            <span>{t("dash_biomass_c")}</span>
            <Leaf className="w-4 h-4 text-emerald-700" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0D2818]">
              {summary.total_conservative_biomass_t}
            </span>
            <span className="text-sm font-medium text-slate-500">t</span>
          </div>
          <div className="mt-2 text-xs text-slate-600">
            {t("dash_carbon_stock")}:{" "}
            <span className="font-mono font-semibold text-[#0D2818]">
              {summary.total_carbon_tC} tC
            </span>
          </div>
        </div>

        <div className="ck-card p-5 border-l-4 border-l-emerald-600">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-emerald-800">
            <span>{t("dash_issuable_co2e")}</span>
            <ShieldCheck className="w-4 h-4 text-emerald-700" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-800">
              {summary.total_co2e_issuable_t}
            </span>
            <span className="text-sm font-medium text-emerald-700">tCO₂e</span>
          </div>
          <div className="mt-2 text-xs text-slate-600">
            Gross {summary.total_co2e_gross_t} tCO₂e · {t("dash_buffer_note")}
          </div>
        </div>

        <div className="ck-card p-5">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500">
            <span>{t("dash_fraud_integrity")}</span>
            <AlertTriangle className="w-4 h-4 text-amber-600" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-[#0D2818]">
              {summary.chains_verified}/{summary.total_farms}
            </span>
            <span className="text-sm font-medium text-emerald-700">{t("dash_sha_intact")}</span>
          </div>
          <div className="mt-2 text-xs">
            {summary.active_fraud_alerts > 0 ? (
              <button
                type="button"
                onClick={() => onNavigateTab("fraud")}
                className="text-amber-700 font-semibold hover:underline"
              >
                {summary.active_fraud_alerts} {t("dash_active_alerts_link")}
              </button>
            ) : (
              <span className="text-emerald-700 font-semibold">{t("dash_all_clear")}</span>
            )}
          </div>
        </div>
      </div>

      {/* Portfolio Map + Conservative Carbon Bar Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-7 ck-card p-5">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 className="text-base font-bold text-[#0D2818]">{t("dash_map_title")}</h3>
              <p className="text-xs text-slate-500">{t("dash_map_sub")}</p>
            </div>
            <button
              type="button"
              onClick={() => onNavigateTab("twin")}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-[#0D2818] text-white hover:bg-[#163A24] transition shrink-0"
            >
              {t("dash_open_twin")}
            </button>
          </div>
          <LeafletMap
            farms={farms}
            selectedFarmId={null}
            onSelectFarm={(id) => {
              onSelectFarm(id);
              onNavigateTab("twin");
            }}
            layerMode="boundary"
            showInnerBuffer={false}
            heightClass="h-[360px]"
          />
        </div>

        <div className="lg:col-span-5 ck-card p-5 flex flex-col justify-between">
          <div>
            <h3 className="text-base font-bold text-[#0D2818]">{t("dash_bar_title")}</h3>
            <p className="text-xs text-slate-500 mb-4">{t("dash_bar_sub")}</p>
            <div className="space-y-3">
              {farms.map((f) => {
                const est = f.latest_estimate;
                const gross = est?.co2e_gross_t || 0;
                const issuable = est?.co2e_conservatively_issuable_t || 0;
                const radar = f.latest_observation?.radar_fallback_used;
                return (
                  <div
                    key={f.id}
                    onClick={() => onSelectFarm(f.id)}
                    className={`p-2.5 rounded-lg border cursor-pointer transition ${
                      selectedFarmId === f.id
                        ? "border-[#0D2818] bg-[#FAF8F4]"
                        : "border-transparent hover:bg-[#FAF8F4]"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="font-bold text-[#0D2818] truncate max-w-[60%]">
                        {f.name}
                      </span>
                      <span className="font-mono text-slate-700">
                        <strong className="text-emerald-800">{issuable}</strong> / {gross} tCO₂e
                      </span>
                    </div>
                    <div className="w-full h-2.5 bg-[#F3EFE6] rounded-full overflow-hidden relative">
                      <div
                        className="h-full bg-amber-300/70 rounded-full"
                        style={{ width: `${Math.min(100, (gross / maxCo2e) * 100)}%` }}
                      />
                      <div
                        className="h-full bg-[#163A24] rounded-full absolute top-0 left-0"
                        style={{ width: `${Math.min(100, (issuable / maxCo2e) * 100)}%` }}
                      />
                    </div>
                    <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                      <span>{f.gross_area_ha} ha · {f.district}, {f.state}</span>
                      {radar && (
                        <span className="inline-flex items-center gap-1 text-blue-700 font-semibold">
                          <CloudRain className="w-3 h-3" /> SAR Fallback
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Historical NDVI Trend + Unit Economics Target */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-6 ck-card p-5">
          <h3 className="text-base font-bold text-[#0D2818]">{t("dash_ndvi_title")}</h3>
          <p className="text-xs text-slate-500 mb-4">{t("dash_ndvi_sub")}</p>
          <div className="flex items-end gap-4 h-40 pt-4 px-2 border-b border-[#E5DFD1]">
            {historical_trend.map((pt) => (
              <div key={pt.year} className="flex-1 flex flex-col items-center gap-1.5">
                <span className="font-mono text-xs font-bold text-[#0D2818]">
                  {pt.avg_ndvi}
                </span>
                <div
                  className="w-full max-w-[54px] rounded-t-lg bg-gradient-to-t from-[#0D2818] to-emerald-500 transition-all"
                  style={{ height: `${Math.max(18, pt.avg_ndvi * 130)}px` }}
                />
                <span className="text-xs font-semibold text-slate-600">{pt.year}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-6 ck-card p-5">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="text-base font-bold text-[#0D2818] flex items-center gap-2">
                <Coins className="w-4 h-4 text-amber-700" />
                {t("dash_cost_title")} (≤₹{summary.target_cost_inr_ha_yr}/ha/yr)
              </h3>
              <p className="text-xs text-slate-500">{t("dash_cost_sub")}</p>
            </div>
            <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 shrink-0">
              {t("dash_project_target")}
            </span>
          </div>
          <div className="space-y-2 mt-3">
            {cost_breakdown.map((row) => (
              <div
                key={row.component}
                className="flex items-center justify-between text-xs py-1.5 border-b border-dashed border-[#E5DFD1] last:border-0"
              >
                <div>
                  <div className="font-semibold text-[#0D2818]">{row.component}</div>
                  <div className="text-[11px] text-slate-500">{row.note}</div>
                </div>
                <div className="font-mono font-bold text-[#163A24]">
                  {row.max_inr === 0 ? "₹0 (Free)" : `₹${row.min_inr}–${row.max_inr}`}
                </div>
              </div>
            ))}
            <div className="pt-2 flex items-center justify-between text-xs font-extrabold text-[#0D2818]">
              <span>{t("dash_cost_total")}</span>
              <span className="font-mono text-emerald-800">₹55–₹110 / ha / yr</span>
            </div>
          </div>
        </div>
      </div>

      {/* Registered Farms Directory */}
      <div className="ck-card p-5 overflow-x-auto">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-bold text-[#0D2818]">{t("dash_registry_title")}</h3>
          <span className="text-xs text-slate-500">
            {recent_alerts.filter((a) => !a.resolved).length} open flags
          </span>
        </div>
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-[#E5DFD1] text-slate-500 uppercase tracking-wider text-[11px]">
              <th className="py-2.5 pr-3">{t("dash_th_farm")}</th>
              <th className="py-2.5 pr-3">{t("dash_th_loc")}</th>
              <th className="py-2.5 pr-3">{t("dash_th_area")}</th>
              <th className="py-2.5 pr-3">{t("dash_th_ci")}</th>
              <th className="py-2.5 pr-3">{t("dash_th_co2")}</th>
              <th className="py-2.5 pr-3">{t("dash_th_status")}</th>
              <th className="py-2.5">{t("dash_th_actions")}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#F3EFE6]">
            {farms.map((f) => {
              const est = f.latest_estimate;
              const isFlagged = f.verification_status === "FLAGGED_REVIEW";
              return (
                <tr key={f.id} className="hover:bg-[#FAF8F4]">
                  <td className="py-3 pr-3">
                    <div className="font-bold text-[#0D2818]">{f.name}</div>
                    <div className="text-slate-500">
                      {f.farmer_name} · <span className="font-mono">{f.id}</span>
                    </div>
                  </td>
                  <td className="py-3 pr-3 text-slate-600">
                    <div className="inline-flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      {f.district}, {f.state}
                    </div>
                  </td>
                  <td className="py-3 pr-3 font-mono">
                    {f.gross_area_ha} ha
                    <div className="text-[11px] text-slate-500">
                      {f.core_area_ha} ha ({f.core_pixels_10m} px)
                    </div>
                  </td>
                  <td className="py-3 pr-3 font-mono">
                    {est ? (
                      <>
                        <strong>{est.agb_point_t_ha}</strong>{" "}
                        <span className="text-slate-500">
                          [{est.agb_ci_lower_t_ha}–{est.agb_ci_upper_t_ha}]
                        </span>
                      </>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="py-3 pr-3 font-mono font-bold text-emerald-800">
                    {est ? `${est.co2e_conservatively_issuable_t} tCO₂e` : "—"}
                  </td>
                  <td className="py-3 pr-3">
                    {isFlagged ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-100 text-red-800 font-semibold">
                        <AlertTriangle className="w-3 h-3" /> {t("dash_flagged")} ({f.risk_summary.risk_score})
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-semibold">
                        <CheckCircle2 className="w-3 h-3" /> {t("dash_verified_demo")}
                      </span>
                    )}
                  </td>
                  <td className="py-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => {
                          onSelectFarm(f.id);
                          onNavigateTab("twin");
                        }}
                        className="px-2.5 py-1 rounded-md border border-[#E5DFD1] hover:bg-[#0D2818] hover:text-white font-semibold transition"
                      >
                        {t("dash_inspect")}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          onSelectFarm(f.id);
                          onNavigateTab("passport");
                        }}
                        className="px-2.5 py-1 rounded-md bg-[#F3EFE6] text-[#0D2818] hover:bg-[#E5DFD1] font-semibold transition"
                      >
                        {t("dash_passport")}
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
