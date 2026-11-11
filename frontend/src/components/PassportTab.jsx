import { useState } from "react";
import {
  Award,
  Camera,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Download,
  FileJson,
  Link2,
  Lock,
  MapPin,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { api } from "../api";
import { formatAcresAndHa } from "../i18n";

export default function PassportTab({
  farms,
  selectedFarmId,
  onSelectFarm,
  dossier,
  onRefreshAll,
  t,
  lang,
  viewMode = "farmer",
}) {
  const [issuing, setIssuing] = useState(false);
  const [tamperSeq, setTamperSeq] = useState(null);
  const [chainOverride, setChainOverride] = useState(null);
  const [showAuditorDetails, setShowAuditorDetails] = useState(false);

  const passport = dossier?.passport;
  const farm = dossier?.farm;
  const farmer = dossier?.farmer;
  const est = dossier?.latest_estimate;
  const chain = chainOverride || dossier?.chain_verification;
  const alerts = dossier?.fraud_alerts || [];
  const evidence = dossier?.evidence_records || [];

  const overlapFlag = alerts.some((a) => !a.resolved && a.alert_type.includes("OVERLAP"));
  const photoOk = evidence.length > 0 && evidence.some((e) => e.status === "VERIFIED");
  const lockOk = chain?.verified;

  const handleIssuePassport = async () => {
    if (!selectedFarmId) return;
    setIssuing(true);
    setChainOverride(null);
    setTamperSeq(null);
    try {
      await api.issuePassport(selectedFarmId);
      await onRefreshAll(selectedFarmId);
    } finally {
      setIssuing(false);
    }
  };

  const handleVerifyClean = async () => {
    if (!selectedFarmId) return;
    setTamperSeq(null);
    const res = await api.verifyPassport(selectedFarmId);
    setChainOverride(res);
  };

  const handleSimulateTamper = async () => {
    if (!selectedFarmId) return;
    const targetBlock = Math.min(2, chain?.block_count || 1);
    setTamperSeq(targetBlock);
    const res = await api.verifyPassport(selectedFarmId, targetBlock);
    setChainOverride(res);
  };

  const showTechnical = viewMode === "auditor" || showAuditorDetails;

  return (
    <div className="space-y-6">
      <div className="ck-card p-3.5 sm:p-4 flex flex-col sm:flex-row sm:flex-wrap sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-2.5 w-full sm:w-auto min-w-0">
          <Award className="w-5 h-5 text-emerald-700 shrink-0" />
          <select
            value={selectedFarmId || ""}
            onChange={(e) => {
              setChainOverride(null);
              setTamperSeq(null);
              onSelectFarm(e.target.value);
            }}
            className="w-full sm:w-auto max-w-full min-w-0 text-sm font-semibold bg-[#FAF8F4] border border-[#E5DFD1] rounded-lg px-3 py-2 text-[#0D2818]"
          >
            {farms.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-1 sm:flex sm:flex-wrap gap-2 w-full sm:w-auto">
          <button
            type="button"
            onClick={handleIssuePassport}
            disabled={issuing}
            className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2.5 sm:py-2 min-h-[42px] rounded-lg bg-[#0D2818] text-white text-xs font-bold hover:bg-[#163A24]"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            {issuing ? "…" : t("cp_issue_btn")}
          </button>
          {selectedFarmId && (
            <>
              <a
                href={`/api/passports/${selectedFarmId}/report.html?lang=${lang}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2.5 sm:py-2 min-h-[42px] rounded-lg bg-emerald-700 text-white text-xs font-bold hover:bg-emerald-800"
              >
                <Download className="w-3.5 h-3.5" />
                {t("cp_download_html")}
              </a>
              {viewMode === "auditor" && (
                <a
                  href={`/api/passports/${selectedFarmId}/bundle.json`}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 sm:py-2 min-h-[42px] rounded-lg border border-[#E5DFD1] bg-white text-[#0D2818] text-xs font-bold hover:bg-[#FAF8F4]"
                >
                  <FileJson className="w-3.5 h-3.5" />
                  {t("cp_download_json")}
                </a>
              )}
            </>
          )}
        </div>
      </div>

      {/* Passbook-Style Certificate Card */}
      {passport && farm && farmer && (
        <div className="rounded-2xl bg-gradient-to-br from-[#091D11] via-[#0D2818] to-[#163A24] text-white p-4 sm:p-6 shadow-xl border border-[#245A39]">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4 border-b border-white/15 pb-4">
            <div>
              <div className="text-[11px] uppercase tracking-widest text-emerald-300 font-bold">
                {viewMode === "farmer" ? t("fcp_title") : t("cp_card_kicker")}
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold mt-1 leading-snug">{farm.name}</h2>
              <div className="text-xs text-emerald-100/85 mt-0.5 leading-relaxed">
                {t("cp_landholder")}: <strong>{farmer.name}</strong> · {farmer.village}, {farmer.district}, {farmer.state} ·{" "}
                <span className="font-mono">{farmer.land_doc_ref}</span>
              </div>
            </div>
            <div className="sm:text-right">
              <div className="font-mono text-sm font-bold text-amber-300">{passport.passport_id}</div>
              <span
                className={`inline-block mt-1.5 px-3 py-1 rounded-full text-xs font-bold ${
                  passport.verification_status === "VERIFIED_PROTOTYPE"
                    ? "bg-emerald-500 text-emerald-950"
                    : "bg-amber-400 text-amber-950"
                }`}
              >
                {passport.verification_status === "VERIFIED_PROTOTYPE" ? t("fh_status_ok") : t("fh_status_warn")}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 py-4 text-xs">
            <div className="bg-white/10 rounded-xl p-3.5">
              <div className="text-emerald-200/80">{t("cp_area_lbl")}</div>
              <div className="text-lg font-extrabold mt-0.5">
                {formatAcresAndHa(farm.gross_area_ha, lang)}
              </div>
              <div className="text-[11px] text-emerald-100/75">
                {lang === "te" ? "శుభ్రమైన లోపలి పొలం" : "Clean inner zone"}: {formatAcresAndHa(farm.core_area_ha, lang)}
              </div>
            </div>
            <div className="bg-white/10 rounded-xl p-3.5">
              <div className="text-emerald-200/80">{t("cp_carbon_lbl")}</div>
              <div className="text-lg font-extrabold mt-0.5">
                {est ? est.carbon_tC : 0}{" "}
                <span className="text-xs font-bold">
                  {viewMode === "farmer" ? t("fcp_tonnes_unit") : "tC"}
                </span>
              </div>
              <div className="text-[11px] text-emerald-100/75">
                {lang === "te" ? "చెట్ల కర్ర & వేర్ల నుండి" : "From wood & root growth"}
              </div>
            </div>
            <div className="bg-white/10 rounded-xl p-3.5 border border-emerald-400/40">
              <div className="text-emerald-300 font-semibold">{t("cp_issuable_lbl")}</div>
              <div className="text-2xl font-extrabold text-emerald-300 mt-0.5">
                {est ? est.co2e_conservatively_issuable_t : 0}{" "}
                <span className="text-xs font-bold">{lang === "te" ? "యూనిట్లు" : "Units (tCO₂e)"}</span>
              </div>
              <div className="text-[11px] text-emerald-100/75">
                {lang === "te" ? "15% భద్రతా నిల్వ తీసివేసిన తర్వాత" : "After 15% safety reserve"}
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-white/15 flex flex-wrap items-center justify-between gap-2 text-[11px] text-emerald-200/90">
            <span>{t("cp_disclaimer")}</span>
            {viewMode === "auditor" && (
              <span className="font-mono">HEAD SHA-256: {(chain?.head_hash || passport.head_hash).slice(0, 24)}…</span>
            )}
          </div>
        </div>
      )}

      {/* Farmer-Friendly 3-Line Accounting + 3 Big Green Trust Shields */}
      {est && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-6 ck-card p-5 space-y-3">
            <h3 className="text-sm font-extrabold text-[#0D2818]">{t("fcp_how_counted")}</h3>
            <div className="space-y-2.5 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF8F4] border border-[#E5DFD1]">
                <span className="font-semibold text-slate-700">{t("fcp_line1")}</span>
                <span className="font-bold text-[#0D2818]">{est.net_additional_biomass_t} t</span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-xl bg-[#FAF8F4] border border-[#E5DFD1]">
                <span className="font-semibold text-slate-700">{t("fcp_line2")}</span>
                <span className="font-bold text-amber-800">
                  −{(est.co2e_gross_t - est.co2e_conservatively_issuable_t).toFixed(2)} {lang === "te" ? "యూనిట్లు" : "Units"}
                </span>
              </div>
              <div className="flex items-center justify-between p-3.5 rounded-xl bg-emerald-50 border border-emerald-200">
                <span className="font-extrabold text-emerald-950">{t("fcp_line3")}</span>
                <span className="font-extrabold text-lg text-emerald-800">
                  {est.co2e_conservatively_issuable_t} {lang === "te" ? "యూనిట్లు" : "Units"}
                </span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-6 ck-card p-5 space-y-3">
            <h3 className="text-sm font-extrabold text-[#0D2818]">{t("fcp_shields_title")}</h3>
            {farm?.verification_status === "FLAGGED_REVIEW" && (
              <div className="p-3 rounded-xl bg-amber-50 border border-amber-300 text-xs text-amber-950 space-y-1">
                <div className="font-extrabold flex items-center gap-1.5">
                  <ShieldAlert className="w-4 h-4 text-amber-700 shrink-0" />
                  {t("fcp_attention_title")}
                </div>
                <p className="text-[11px] leading-relaxed opacity-90">
                  {overlapFlag ? t("fcp_shield1_d_warn") : t("fcp_shield2_d_warn")}
                </p>
              </div>
            )}
            <div className="space-y-2.5 text-xs">
              <div className={`flex items-start gap-3 p-3 rounded-xl border ${!overlapFlag ? "bg-emerald-50/70 border-emerald-200" : "bg-amber-50 border-amber-200"}`}>
                <MapPin className={`w-5 h-5 shrink-0 ${!overlapFlag ? "text-emerald-700" : "text-amber-700"}`} />
                <div>
                  <div className="font-bold text-[#0D2818]">{t("fcp_shield1_t")}</div>
                  <div className="text-slate-600">{!overlapFlag ? t("fcp_shield1_d_ok") : t("fcp_shield1_d_warn")}</div>
                </div>
              </div>
              <div className={`flex items-start gap-3 p-3 rounded-xl border ${photoOk ? "bg-emerald-50/70 border-emerald-200" : "bg-amber-50 border-amber-200"}`}>
                <Camera className={`w-5 h-5 shrink-0 ${photoOk ? "text-emerald-700" : "text-amber-700"}`} />
                <div>
                  <div className="font-bold text-[#0D2818]">{t("fcp_shield2_t")}</div>
                  <div className="text-slate-600">{photoOk ? t("fcp_shield2_d_ok") : t("fcp_shield2_d_warn")}</div>
                </div>
              </div>
              <div className={`flex items-start gap-3 p-3 rounded-xl border ${lockOk ? "bg-emerald-50/70 border-emerald-200" : "bg-red-50 border-red-200"}`}>
                <Lock className={`w-5 h-5 shrink-0 ${lockOk ? "text-emerald-700" : "text-red-700"}`} />
                <div>
                  <div className="font-bold text-[#0D2818]">{t("fcp_shield3_t")}</div>
                  <div className="text-slate-600">{lockOk ? t("fcp_shield3_d_ok") : t("fcp_shield3_d_warn")}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Collapsible Auditor Proof Toggle in Farmer View */}
      {viewMode === "farmer" && (
        <div className="text-center">
          <button
            type="button"
            onClick={() => setShowAuditorDetails(!showAuditorDetails)}
            className="inline-flex items-center gap-1.5 text-xs font-bold text-[#0D2818] px-4 py-2 rounded-full bg-white border border-[#E5DFD1] hover:bg-[#F3EFE6] transition"
          >
            {showAuditorDetails ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {showAuditorDetails ? t("fcp_hide_tech") : t("fcp_show_tech")}
          </button>
        </div>
      )}

      {/* Technical SHA-256 Hash-Chain Audit Trail */}
      {showTechnical && chain && (
        <div className="ck-card p-5 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-[#0D2818] flex items-center gap-2">
                <Link2 className="w-5 h-5 text-[#163A24]" />
                {t("cp_chain_title")} ({chain.block_count})
              </h3>
              <p className="text-xs text-slate-500">{t("cp_chain_sub")}</p>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleVerifyClean}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-emerald-700 text-white text-xs font-bold hover:bg-emerald-800"
              >
                <ShieldCheck className="w-4 h-4" />
                {t("cp_verify_btn")}
              </button>
              <button
                type="button"
                onClick={handleSimulateTamper}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg bg-red-600 text-white text-xs font-bold hover:bg-red-700"
              >
                <ShieldAlert className="w-4 h-4" />
                {t("cp_tamper_btn")}
              </button>
            </div>
          </div>

          <div
            className={`p-3.5 rounded-xl border text-xs font-semibold flex items-center gap-2 ${
              chain.verified
                ? "bg-emerald-50 border-emerald-200 text-emerald-900"
                : "bg-red-50 border-red-300 text-red-900"
            }`}
          >
            {chain.verified ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-700 shrink-0" />
            ) : (
              <ShieldAlert className="w-5 h-5 text-red-600 shrink-0" />
            )}
            <div>
              <div>{chain.message}</div>
              {tamperSeq && (
                <div className="text-[11px] font-normal mt-0.5">
                  Non-destructive demo: Block #{tamperSeq} mutated in-memory (+50.0 tCO₂e). Click &ldquo;{t("cp_verify_btn")}&rdquo; to restore clean ledger verification.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {chain.blocks.map((blk) => (
              <div
                key={blk.seq_id}
                className={`p-3 rounded-xl border text-xs ${
                  blk.valid ? "bg-[#FAF8F4] border-[#E5DFD1]" : "bg-red-50 border-red-300"
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold px-2 py-0.5 rounded bg-[#0D2818] text-white">
                      Block #{blk.index}
                    </span>
                    <span className="font-mono font-bold text-[#0D2818]">{blk.event_type}</span>
                    <span className="text-slate-500 text-[11px]">{blk.timestamp.slice(0, 19)} UTC</span>
                  </div>
                  <span className={`font-bold ${blk.valid ? "text-emerald-700" : "text-red-700"}`}>
                    {blk.valid ? `✅ ${t("cp_valid_badge")}` : `❌ ${t("cp_broken_badge")}`}
                  </span>
                </div>
                <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-2 font-mono text-[11px] text-slate-600">
                  <div className="truncate">prev: {blk.prev_hash}</div>
                  <div className="truncate">curr: {blk.stored_hash}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
