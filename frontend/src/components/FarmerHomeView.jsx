import {
  Camera,
  CheckCircle2,
  CloudRain,
  FileCheck2,
  MapPin,
  Map as MapIcon,
  Plus,
  ShieldAlert,
  ShieldCheck,
  Sprout,
  Trees,
} from "lucide-react";
import { formatAcresAndHa } from "../i18n";

export default function FarmerHomeView({
  dashboard,
  onSelectFarm,
  onNavigateTab,
  t,
  lang,
}) {
  if (!dashboard) return null;
  const { summary, farms } = dashboard;

  const clearCount = farms.filter((f) => f.verification_status !== "FLAGGED_REVIEW").length;
  const flaggedCount = farms.length - clearCount;

  return (
    <div className="space-y-6">
      {/* Warm Welcome Passbook Banner */}
      <div className="rounded-2xl bg-gradient-to-br from-[#0D2818] via-[#163A24] to-[#1F4E32] text-white p-4 sm:p-6 shadow-lg flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-300 bg-white/10 px-3 py-1 rounded-full mb-2">
            <Sprout className="w-3.5 h-3.5" />
            CarbonKheti · {lang === "te" ? "రైతు సులభ పోర్టల్" : "Farmer Easy Portal"}
          </div>
          <h1 className="text-lg sm:text-2xl font-extrabold tracking-tight leading-snug">
            {t("fh_welcome_title")}
          </h1>
          <p className="text-xs sm:text-sm text-emerald-100/85 mt-1 leading-relaxed">
            {t("fh_welcome_sub")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onNavigateTab("twin")}
          className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-3 min-h-[44px] rounded-xl bg-amber-400 text-[#0D2818] text-sm font-extrabold hover:bg-amber-300 transition shadow-md shrink-0"
        >
          <Plus className="w-4 h-4" />
          {t("fh_add_farm_btn")}
        </button>
      </div>

      {/* 3 Big Clear Farmer Numbers (Acres + Units + Trust) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="ck-card p-5">
          <div className="flex items-center justify-between text-xs font-bold text-slate-500">
            <span>{t("fh_kpi_land")}</span>
            <Trees className="w-5 h-5 text-[#163A24]" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-[#0D2818]">
            {formatAcresAndHa(summary.total_gross_hectares, lang)}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {summary.total_farms} {lang === "te" ? "పొలాలు" : "farm plots"} · {summary.total_farmers}{" "}
            {lang === "te" ? "రైతులు" : "farmers"}
          </div>
        </div>

        <div className="ck-card p-5 border-l-4 border-l-emerald-600">
          <div className="flex items-center justify-between text-xs font-bold text-emerald-800">
            <span>{t("fh_kpi_carbon")}</span>
            <FileCheck2 className="w-5 h-5 text-emerald-700" />
          </div>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-extrabold text-emerald-800">
              {summary.total_co2e_issuable_t}
            </span>
            <span className="text-sm font-bold text-emerald-700">
              {lang === "te" ? "యూనిట్లు" : "Units"}
            </span>
          </div>
          <div className="mt-1 text-xs text-slate-600">{t("fh_kpi_carbon_sub")}</div>
        </div>

        <div className="ck-card p-5">
          <div className="flex items-center justify-between text-xs font-bold text-slate-500">
            <span>{t("fh_kpi_trust")}</span>
            <ShieldCheck className="w-5 h-5 text-emerald-700" />
          </div>
          <div className="mt-2 flex items-center gap-3">
            <span className="text-2xl font-extrabold text-emerald-800">
              {clearCount} ✓
            </span>
            <span className="text-xs font-semibold text-slate-600">{t("fh_farms_clear")}</span>
            {flaggedCount > 0 && (
              <span className="text-xs font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-900">
                {flaggedCount} {t("fh_needs_check")}
              </span>
            )}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {lang === "te" ? "అన్ని రికార్డులకు డిజిటల్ తాళం ఉంది" : "Every record has a tamper-proof digital lock"}
          </div>
        </div>
      </div>

      {/* Farm Passbook Cards */}
      <div>
        <h2 className="text-base font-extrabold text-[#0D2818] mb-3">{t("fh_your_farms")}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {farms.map((f) => {
            const ndvi = f.latest_observation?.ndvi_mean ?? 0.5;
            const greeneryScore = Math.round(ndvi * 100);
            const radar = f.latest_observation?.radar_fallback_used;
            const units = f.latest_estimate?.co2e_conservatively_issuable_t ?? 0;
            const isWarn = f.verification_status === "FLAGGED_REVIEW";

            return (
              <div key={f.id} className="ck-card p-5 flex flex-col justify-between space-y-4">
                <div className="space-y-2.5">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-base font-extrabold text-[#0D2818] leading-snug">
                        {f.name}
                      </h3>
                      <div className="text-xs text-slate-600 mt-0.5 flex items-center gap-1">
                        <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>
                          {f.farmer_name} · {f.district}, {f.state}
                        </span>
                      </div>
                    </div>
                    {isWarn ? (
                      <span className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-amber-100 text-amber-900 text-[11px] font-bold">
                        <ShieldAlert className="w-3.5 h-3.5" />
                        {lang === "te" ? "తనిఖీ" : "Check"}
                      </span>
                    ) : (
                      <span className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        {lang === "te" ? "సురక్షితం" : "Verified"}
                      </span>
                    )}
                  </div>

                  <div className="bg-[#FAF8F4] rounded-xl p-3 border border-[#E5DFD1] space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-500">{t("cp_area_lbl")}</span>
                      <span className="font-bold text-[#0D2818]">
                        {formatAcresAndHa(f.gross_area_ha, lang)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">{t("fh_safe_units")}</span>
                      <span className="font-extrabold text-emerald-800">
                        {units} {lang === "te" ? "యూనిట్లు" : "Units"}
                      </span>
                    </div>
                    <div>
                      <div className="flex justify-between mb-1">
                        <span className="text-slate-500">{t("fh_tree_health")}</span>
                        <span className="font-bold text-[#0D2818]">{greeneryScore} / 100</span>
                      </div>
                      <div className="w-full h-2.5 bg-[#E5DFD1] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-600 rounded-full"
                          style={{ width: `${Math.min(100, greeneryScore)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {radar && (
                    <div className="flex items-center gap-1.5 text-[11px] font-semibold text-blue-800 bg-blue-50 px-2.5 py-1.5 rounded-lg border border-blue-200">
                      <CloudRain className="w-3.5 h-3.5 shrink-0" />
                      {t("fh_cloud_note")}
                    </div>
                  )}

                  <div
                    className={`text-[11px] font-semibold ${
                      isWarn ? "text-amber-800" : "text-emerald-800"
                    }`}
                  >
                    {isWarn ? `⚠ ${t("fh_status_warn")}` : `✓ ${t("fh_status_ok")}`}
                  </div>
                </div>

                {/* Big Thumb-Friendly Farmer Buttons */}
                <div className="grid grid-cols-3 gap-1.5 sm:gap-2 pt-2 border-t border-[#F3EFE6]">
                  <button
                    type="button"
                    onClick={() => {
                      onSelectFarm(f.id);
                      onNavigateTab("farmer");
                    }}
                    className="flex flex-col sm:flex-row items-center justify-center gap-1 py-2.5 px-1.5 min-h-[46px] rounded-xl bg-[#0D2818] text-white text-[11px] sm:text-xs font-bold leading-tight text-center hover:bg-[#163A24] transition"
                  >
                    <Camera className="w-4 h-4 sm:w-3.5 sm:h-3.5 shrink-0" />
                    <span>{t("fh_btn_photo")}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onSelectFarm(f.id);
                      onNavigateTab("twin");
                    }}
                    className="flex flex-col sm:flex-row items-center justify-center gap-1 py-2.5 px-1.5 min-h-[46px] rounded-xl bg-[#F3EFE6] text-[#0D2818] text-[11px] sm:text-xs font-bold leading-tight text-center hover:bg-[#E5DFD1] transition"
                  >
                    <MapIcon className="w-4 h-4 sm:w-3.5 sm:h-3.5 shrink-0" />
                    <span>{t("fh_btn_map")}</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      onSelectFarm(f.id);
                      onNavigateTab("passport");
                    }}
                    className="flex flex-col sm:flex-row items-center justify-center gap-1 py-2.5 px-1.5 min-h-[46px] rounded-xl bg-emerald-700 text-white text-[11px] sm:text-xs font-bold leading-tight text-center hover:bg-emerald-800 transition"
                  >
                    <FileCheck2 className="w-4 h-4 sm:w-3.5 sm:h-3.5 shrink-0" />
                    <span>{t("fh_btn_cert")}</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3 Simple Steps Visual Guide */}
      <div className="ck-card p-5 bg-[#FAF8F4]">
        <h3 className="text-sm font-extrabold text-[#0D2818] mb-3">{t("fh_how_title")}</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-white p-4 rounded-xl border border-[#E5DFD1]">
            <div className="font-extrabold text-[#0D2818] mb-1">{t("fh_how_1_t")}</div>
            <p className="text-slate-600 leading-relaxed">{t("fh_how_1_d")}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-[#E5DFD1]">
            <div className="font-extrabold text-[#0D2818] mb-1">{t("fh_how_2_t")}</div>
            <p className="text-slate-600 leading-relaxed">{t("fh_how_2_d")}</p>
          </div>
          <div className="bg-white p-4 rounded-xl border border-[#E5DFD1]">
            <div className="font-extrabold text-[#0D2818] mb-1">{t("fh_how_3_t")}</div>
            <p className="text-slate-600 leading-relaxed">{t("fh_how_3_d")}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

