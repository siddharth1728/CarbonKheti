import { useState } from "react";
import {
  AlertOctagon,
  Camera,
  CheckCircle2,
  CopyCheck,
  MapPinOff,
  Radar,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { api } from "../api";

const CHECK_CATALOG = [
  { key: "DUPLICATE_PLOT_HASH", title: "Duplicate Farm Registrations", desc: "Canonical polygon SHA-256 coordinate match" },
  { key: "POLYGON_OVERLAP_DOUBLE_COUNTING", title: "Overlapping Polygons (Double Counting)", desc: "Shapely Intersection-over-Union (IoU > 5%)" },
  { key: "GPS_OUTSIDE_FARM_BOUNDARY", title: "Suspicious / Off-Plot GPS & Travel", desc: "EXIF & App GPS distance + impossible velocity" },
  { key: "REUSED_PHOTO", title: "Reused Farmer Photographs", desc: "Exact SHA-256 + Perceptual dHash Hamming distance" },
  { key: "EXIF_METADATA", title: "EXIF Metadata Inconsistencies", desc: "Stripped headers, future/stale timestamps" },
  { key: "UNUSUAL_VEGETATION_DROP", title: "Unusual Vegetation Change", desc: "Abrupt NDVI drop or photo-vs-NDVI conflict" },
  { key: "SUSPICIOUS_CARBON_JUMP", title: "Suspicious Carbon Patterns", desc: "Physically implausible single-period AGB jump" },
];

export default function FraudRadarTab({
  farms,
  selectedFarmId,
  onSelectFarm,
  dossier,
  recentAlerts = [],
  onRefreshAll,
  t,
}) {
  const [simulating, setSimulating] = useState(null);
  const [resolving, setResolving] = useState(null);
  const [notice, setNotice] = useState(null);

  const farmAlerts = dossier?.fraud_alerts || [];
  const risk = dossier?.risk_summary || { risk_score: 0, risk_level: "LOW", active_alert_count: 0 };

  const handleSimulate = async (scenario) => {
    if (!selectedFarmId) return;
    setSimulating(scenario);
    setNotice(null);
    try {
      const updated = await api.simulateFraud(selectedFarmId, scenario);
      setNotice(`Triggered live Fraud Radar check: ${scenario} — Risk Score is now ${updated.risk_summary.risk_score}/100.`);
      await onRefreshAll(selectedFarmId);
    } finally {
      setSimulating(null);
    }
  };

  const handleResolve = async (alertId) => {
    setResolving(alertId);
    try {
      await api.resolveAlert(alertId);
      await onRefreshAll(selectedFarmId);
    } finally {
      setResolving(null);
    }
  };

  const riskColor =
    risk.risk_score >= 75
      ? "text-red-700 bg-red-50 border-red-200"
      : risk.risk_score >= 45
      ? "text-amber-800 bg-amber-50 border-amber-200"
      : "text-emerald-800 bg-emerald-50 border-emerald-200";

  return (
    <div className="space-y-6">
      <div className="ck-card p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-[#0D2818] flex items-center gap-2">
              <Radar className="w-5 h-5 text-amber-700" />
              {t("fr_title")}
            </h3>
            <p className="text-xs text-slate-500">{t("fr_sub")}</p>
          </div>
          <select
            value={selectedFarmId || ""}
            onChange={(e) => onSelectFarm(e.target.value)}
            className="w-full sm:w-auto max-w-full text-sm font-semibold bg-[#FAF8F4] border border-[#E5DFD1] rounded-lg px-3 py-2 text-[#0D2818]"
          >
            {farms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name} ({f.verification_status})
              </option>
            ))}
          </select>
        </div>

        <div className="bg-[#FAF8F4] border border-[#E5DFD1] rounded-xl p-4">
          <div className="text-xs font-bold text-[#0D2818] mb-2 flex items-center gap-1.5">
            <Sparkles className="w-4 h-4 text-amber-600" />
            {t("fr_sim_title")}
          </div>
          <div className="flex flex-wrap gap-2">
            {[
              { id: "duplicate_plot", label: "Simulate Duplicate / Overlapping Plot", icon: CopyCheck },
              { id: "reused_photo", label: "Simulate Reused Photo Attack (SHA/dHash)", icon: Camera },
              { id: "spoofed_gps_exif", label: "Simulate Spoofed EXIF GPS (42km away)", icon: MapPinOff },
              { id: "stripped_exif", label: "Simulate Stripped EXIF Photo", icon: ShieldAlert },
              { id: "ndvi_mismatch", label: "Simulate Photo vs. Bare-Soil NDVI Conflict", icon: AlertOctagon },
            ].map((btn) => {
              const Icon = btn.icon;
              return (
                <button
                  key={btn.id}
                  type="button"
                  disabled={!!simulating}
                  onClick={() => handleSimulate(btn.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white border border-[#E5DFD1] hover:border-red-400 hover:bg-red-50/50 text-xs font-semibold text-[#0D2818] transition disabled:opacity-50"
                >
                  <Icon className="w-3.5 h-3.5 text-red-600" />
                  {simulating === btn.id ? "…" : btn.label}
                </button>
              );
            })}
          </div>
          {notice && (
            <div className="mt-3 text-xs font-semibold text-red-800 bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
              {notice}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 ck-card p-5 space-y-4">
          <h4 className="text-sm font-bold text-[#0D2818]">{t("fr_risk_title")}</h4>
          <div className={`p-5 rounded-xl border text-center ${riskColor}`}>
            <div className="text-xs font-bold uppercase tracking-wider">{t("fr_score_lbl")}</div>
            <div className="text-5xl font-black font-mono mt-1">{risk.risk_score}</div>
            <div className="text-xs font-bold mt-1">
              {risk.risk_level} RISK · {risk.active_alert_count} active flag(s)
            </div>
          </div>

          <div className="space-y-2 pt-1">
            <div className="text-xs font-bold text-slate-500 uppercase">{t("fr_vectors_title")}</div>
            {CHECK_CATALOG.map((chk) => {
              const hit = farmAlerts.some((a) => !a.resolved && a.alert_type.includes(chk.key.split("_")[0]));
              return (
                <div key={chk.key} className="flex items-start justify-between gap-2 text-xs py-1.5 border-b border-[#F3EFE6] last:border-0">
                  <div>
                    <div className="font-semibold text-[#0D2818]">{chk.title}</div>
                    <div className="text-[11px] text-slate-500">{chk.desc}</div>
                  </div>
                  {hit ? (
                    <span className="shrink-0 px-2 py-0.5 rounded bg-red-100 text-red-800 font-bold text-[10px]">
                      FLAGGED
                    </span>
                  ) : (
                    <span className="shrink-0 px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-bold text-[10px]">
                      PASS
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        <div className="lg:col-span-8 ck-card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-[#0D2818]">
              {t("fr_alerts_title")} ({dossier?.farm?.name})
            </h4>
            <span className="text-xs text-slate-500">{farmAlerts.length} records</span>
          </div>

          {farmAlerts.length === 0 ? (
            <div className="p-8 text-center bg-[#FAF8F4] rounded-xl border border-[#E5DFD1]">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
              <div className="text-sm font-bold text-[#0D2818]">{t("fr_no_alerts")}</div>
            </div>
          ) : (
            <div className="space-y-3">
              {farmAlerts.map((al) => (
                <div
                  key={al.id}
                  className={`p-4 rounded-xl border ${
                    al.resolved ? "bg-slate-50 border-slate-200 opacity-70" : "bg-red-50/40 border-red-200"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                          al.severity === "CRITICAL"
                            ? "bg-red-600 text-white"
                            : al.severity === "HIGH"
                            ? "bg-orange-500 text-white"
                            : "bg-amber-400 text-amber-950"
                        }`}
                      >
                        {al.severity} · {al.risk_score}/100
                      </span>
                      <span className="font-mono text-xs font-bold text-[#0D2818]">{al.alert_type}</span>
                    </div>
                    {!al.resolved ? (
                      <button
                        type="button"
                        disabled={resolving === al.id}
                        onClick={() => handleResolve(al.id)}
                        className="text-xs font-semibold px-2.5 py-1 rounded-md bg-white border border-[#E5DFD1] hover:bg-emerald-700 hover:text-white transition"
                      >
                        {resolving === al.id ? "…" : t("fr_resolve")}
                      </button>
                    ) : (
                      <span className="text-xs font-semibold text-emerald-700">{t("fr_resolved")}</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-800">{al.explanation}</p>
                  <pre className="mt-2 text-[11px] font-mono bg-white/80 p-2 rounded border border-[#E5DFD1] overflow-x-auto text-slate-600">
                    {JSON.stringify(al.evidence_details)}
                  </pre>
                </div>
              ))}
            </div>
          )}

          <div className="pt-4 border-t border-[#E5DFD1]">
            <h5 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              {t("fr_feed_title")}
            </h5>
            <div className="space-y-1.5 max-h-48 overflow-y-auto">
              {recentAlerts.map((a) => (
                <div
                  key={a.id}
                  onClick={() => onSelectFarm(a.farm_id)}
                  className="flex items-center justify-between text-xs p-2 rounded-lg hover:bg-[#FAF8F4] cursor-pointer border border-transparent hover:border-[#E5DFD1]"
                >
                  <div className="truncate max-w-[75%]">
                    <span className="font-mono font-bold text-[#0D2818] mr-2">{a.farm_id}</span>
                    <span className="text-slate-700">{a.alert_type}</span>
                  </div>
                  <span className="font-mono text-[11px] font-bold text-red-700">
                    {a.resolved ? "RESOLVED" : `RISK ${a.risk_score}`}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
