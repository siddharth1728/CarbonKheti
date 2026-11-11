import { CheckCircle2, PlayCircle, X } from "lucide-react";

const DEMO_STEPS = [
  { step: 1, title_en: "Register a sample farmer", title_te: "కొత్త రైతును నమోదు చేయండి", tab: "farmer", hint: "Farmer App → Onboard New Smallholder Farmer" },
  { step: 2, title_en: "Add farm & draw geographical boundary", title_te: "పొలం సరిహద్దు గీసి నమోదు చేయండి", tab: "twin", hint: "Farm Digital Twin → Draw & Register Farm" },
  { step: 3, title_en: "Load satellite imagery (Esri + Sentinel proxy)", title_te: "ఉపగ్రహ చిత్రాలు & పిక్సెల్స్ చూడండి", tab: "twin", hint: "Toggle Satellite basemap & Sentinel-2 / SAR layer" },
  { step: 4, title_en: "Display NDVI & multi-date vegetation change", title_te: "పాత & కొత్త తేదీల పచ్చదనం పోల్చండి", tab: "twin", hint: "Compare Date A (2023) vs Date B (2026)" },
  { step: 5, title_en: "Run Scikit-learn biomass estimation pipeline", title_te: "AI జీవద్రవ్యం & వర్షాకాల రాడార్ లెక్క వేయండి", tab: "intelligence", hint: "Run Biomass Pipeline (try Monsoon 88%)" },
  { step: 6, title_en: "Show 95% confidence interval", title_te: "95% నమ్మకపు పరిధిని చూడండి", tab: "intelligence", hint: "Inspect bootstrap + conformal 95% CI bar" },
  { step: 7, title_en: "Calculate conservative carbon estimates (×0.47 ×44/12)", title_te: "IPCC కార్బన్ & CO₂e లెక్క చూడండి", tab: "intelligence", hint: "Walk through Step 1–8 IPCC calculation ledger" },
  { step: 8, title_en: "Upload farmer geotagged photo evidence", title_te: "రైతు పొలం GPS ఫోటో పంపండి (ఆఫ్‌లైన్ సహా)", tab: "farmer", hint: "Load sample EXIF photo or toggle Offline Mode → Sync" },
  { step: 9, title_en: "Trigger simulated duplicate plot / spoofed photo", title_te: "నకిలీ ఫోటో / అతివ్యాప్తి మోసం పరీక్షించండి", tab: "fraud", hint: "Click any 1-click simulation button in Fraud Radar" },
  { step: 10, title_en: "Generate Carbon Passport digital identity", title_te: "కార్బన్ పాస్‌పోర్ట్ రూపొందించండి", tab: "passport", hint: "Click 'Generate / Refresh Carbon Passport'" },
  { step: 11, title_en: "Verify SHA-256 integrity & simulate tamper", title_te: "SHA-256 గొలుసు భద్రతను తనిఖీ చేయండి", tab: "passport", hint: "Simulate Tamper Attack → Verify Integrity" },
  { step: 12, title_en: "Download final Verification Report (HTML/PDF)", title_te: "తుది ధృవీకరణ నివేదికను డౌన్‌లోడ్ చేయండి", tab: "passport", hint: "Download Report (English or తెలుగు) or JSON Bundle" },
];

export default function JudgeDemoDrawer({ open, onClose, onNavigateTab, completedSteps, onToggleStep, lang = "en" }) {
  if (!open) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-md bg-white border-l border-[#E5DFD1] shadow-2xl z-[1000] flex flex-col">
      <div className="p-4 bg-[#0D2818] text-white flex items-center justify-between">
        <div>
          <div className="text-[11px] uppercase tracking-wider text-emerald-300 font-bold">
            INNOVASIA 2K26 · PS-13
          </div>
          <h3 className="text-base font-extrabold">
            {lang === "te" ? "12-దశల లైవ్ డెమో మార్గదర్శి" : "12-Step Live Judge Demo Script"}
          </h3>
        </div>
        <button type="button" onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10">
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-4 bg-[#FAF8F4] border-b border-[#E5DFD1] text-xs text-slate-700">
        <strong>Core Thesis:</strong> &ldquo;Verification cost doesn&apos;t scale down with farm size, so smallholders get priced out. CarbonKheti inverts that — paying for uncertainty with conservative lower-bound credits, not with trust.&rdquo;
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
        {DEMO_STEPS.map((s) => {
          const done = completedSteps.includes(s.step);
          return (
            <div
              key={s.step}
              className={`p-3 rounded-xl border transition ${
                done ? "bg-emerald-50/70 border-emerald-200" : "bg-white border-[#E5DFD1]"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <button
                  type="button"
                  onClick={() => onToggleStep(s.step)}
                  className="flex items-start gap-2.5 text-left"
                >
                  <CheckCircle2
                    className={`w-4 h-4 mt-0.5 shrink-0 ${
                      done ? "text-emerald-700" : "text-slate-300"
                    }`}
                  />
                  <div>
                    <div className="text-xs font-bold text-[#0D2818]">
                      {s.step}. {lang === "te" ? s.title_te : s.title_en}
                    </div>
                    <div className="text-[11px] text-slate-500 mt-0.5">{s.hint}</div>
                  </div>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onNavigateTab(s.tab);
                    onClose();
                  }}
                  className="shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#0D2818] text-white text-[11px] font-semibold hover:bg-[#163A24]"
                >
                  <PlayCircle className="w-3 h-3" /> Go
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
