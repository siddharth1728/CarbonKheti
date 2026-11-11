import { useCallback, useEffect, useState } from "react";
import {
  Award,
  BarChart3,
  Camera,
  Cpu,
  Globe2,
  Home,
  Info,
  Languages,
  ListChecks,
  Microscope,
  Radar,
  Smartphone,
  Sprout,
  UserCheck,
} from "lucide-react";
import { api } from "./api";
import { createTranslator } from "./i18n";
import FarmerHomeView from "./components/FarmerHomeView";
import DashboardTab from "./components/DashboardTab";
import DigitalTwinTab from "./components/DigitalTwinTab";
import IntelligenceTab from "./components/IntelligenceTab";
import FraudRadarTab from "./components/FraudRadarTab";
import FarmerAppTab from "./components/FarmerAppTab";
import PassportTab from "./components/PassportTab";
import JudgeDemoDrawer from "./components/JudgeDemoDrawer";

const FARMER_TABS = [
  { id: "farmer_home", labelKey: "ftab_home", icon: Home },
  { id: "twin", labelKey: "ftab_map", icon: Globe2 },
  { id: "farmer", labelKey: "ftab_photo", icon: Camera },
  { id: "passport", labelKey: "ftab_passport", icon: Award },
];

const AUDITOR_TABS = [
  { id: "dashboard", labelKey: "tab_dashboard", icon: BarChart3 },
  { id: "twin", labelKey: "tab_twin", icon: Globe2 },
  { id: "intelligence", labelKey: "tab_intelligence", icon: Cpu },
  { id: "fraud", labelKey: "tab_fraud", icon: Radar },
  { id: "farmer", labelKey: "tab_farmer", icon: Smartphone },
  { id: "passport", labelKey: "tab_passport", icon: Award },
];

export default function App() {
  const [lang, setLang] = useState(() => localStorage.getItem("ck_lang") || "en");
  const [viewMode, setViewMode] = useState(() => localStorage.getItem("ck_view_mode") || "farmer");
  const [activeTab, setActiveTab] = useState(() =>
    (localStorage.getItem("ck_view_mode") || "farmer") === "farmer" ? "farmer_home" : "dashboard"
  );
  const [dashboard, setDashboard] = useState(null);
  const [selectedFarmId, setSelectedFarmId] = useState("FARM-TLG-01");
  const [dossier, setDossier] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [demoOpen, setDemoOpen] = useState(false);
  const [completedSteps, setCompletedSteps] = useState([]);

  const t = createTranslator(lang);
  const tabs = viewMode === "farmer" ? FARMER_TABS : AUDITOR_TABS;

  const toggleLanguage = (nextLang) => {
    setLang(nextLang);
    localStorage.setItem("ck_lang", nextLang);
  };

  const switchViewMode = (nextMode) => {
    setViewMode(nextMode);
    localStorage.setItem("ck_view_mode", nextMode);
    if (nextMode === "farmer" && (activeTab === "dashboard" || activeTab === "intelligence" || activeTab === "fraud")) {
      setActiveTab("farmer_home");
    } else if (nextMode === "auditor" && activeTab === "farmer_home") {
      setActiveTab("dashboard");
    }
  };

  const loadData = useCallback(async (focusFarmId = null) => {
    try {
      const dash = await api.getDashboard();
      setDashboard(dash);
      const targetId = focusFarmId || selectedFarmId || dash.farms?.[0]?.id;
      if (targetId) {
        setSelectedFarmId(targetId);
        const dos = await api.getFarm(targetId);
        setDossier(dos);
      }
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [selectedFarmId]);

  useEffect(() => {
    loadData("FARM-TLG-01");
  }, []); // initial load

  const handleSelectFarm = async (farmId) => {
    setSelectedFarmId(farmId);
    try {
      const dos = await api.getFarm(farmId);
      setDossier(dos);
    } catch (err) {
      setError(err.message);
    }
  };

  const toggleDemoStep = (stepNum) => {
    setCompletedSteps((prev) =>
      prev.includes(stepNum) ? prev.filter((x) => x !== stepNum) : [...prev, stepNum]
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FAF8F4] text-[#111C15]">
      <header className="bg-[#0D2818] text-white border-b border-[#1F4E32] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/20 border border-emerald-400/40 flex items-center justify-center">
              <Sprout className="w-5 h-5 text-emerald-300" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold tracking-tight">CarbonKheti</span>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-200 border border-emerald-400/30">
                  PS-13 · Team DoSA
                </span>
              </div>
              <p className="text-[11px] text-emerald-100/80">
                {viewMode === "farmer" ? t("brandSubtitle") : t("brandSubtitleAuditor")}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Farmer View vs Auditor/Judge View Switcher */}
            <div className="inline-flex items-center bg-[#163A24] border border-[#245A39] rounded-lg p-0.5 text-xs font-bold">
              <button
                type="button"
                onClick={() => switchViewMode("farmer")}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md transition ${
                  viewMode === "farmer" ? "bg-emerald-400 text-[#0D2818]" : "text-emerald-100/80 hover:text-white"
                }`}
              >
                <UserCheck className="w-3.5 h-3.5" />
                {t("modeFarmer")}
              </button>
              <button
                type="button"
                onClick={() => switchViewMode("auditor")}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-md transition ${
                  viewMode === "auditor" ? "bg-white text-[#0D2818]" : "text-emerald-100/80 hover:text-white"
                }`}
              >
                <Microscope className="w-3.5 h-3.5" />
                {t("modeAuditor")}
              </button>
            </div>

            {/* Instant English / Telugu Language Switcher */}
            <div className="inline-flex items-center bg-[#163A24] border border-[#245A39] rounded-lg p-0.5 text-xs font-bold">
              <Languages className="w-3.5 h-3.5 text-emerald-300 mx-1.5" />
              <button
                type="button"
                onClick={() => toggleLanguage("en")}
                className={`px-2.5 py-1.5 rounded-md transition ${
                  lang === "en" ? "bg-white text-[#0D2818]" : "text-emerald-100/80 hover:text-white"
                }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => toggleLanguage("te")}
                className={`px-2.5 py-1.5 rounded-md transition ${
                  lang === "te" ? "bg-emerald-400 text-[#0D2818]" : "text-emerald-100/80 hover:text-white"
                }`}
              >
                తెలుగు
              </button>
            </div>

            {viewMode === "auditor" && (
              <button
                type="button"
                onClick={() => setDemoOpen(true)}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-amber-400 text-[#0D2818] text-xs font-extrabold hover:bg-amber-300 transition shadow"
              >
                <ListChecks className="w-4 h-4" />
                {t("judgeDemo")} ({completedSteps.length}/12)
              </button>
            )}
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 flex gap-1 overflow-x-auto pb-0">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            const alertBadge =
              tab.id === "fraud" && dashboard?.summary?.active_fraud_alerts > 0
                ? dashboard.summary.active_fraud_alerts
                : null;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`inline-flex items-center gap-1.5 px-4 py-2.5 text-xs sm:text-sm font-bold border-b-2 whitespace-nowrap transition ${
                  active
                    ? "border-emerald-400 text-white bg-[#163A24]/90 rounded-t-lg"
                    : "border-transparent text-emerald-100/75 hover:text-white hover:bg-white/5 rounded-t-lg"
                }`}
              >
                <Icon className="w-4 h-4" />
                {t(tab.labelKey)}
                {alertBadge && (
                  <span className="ml-1 px-1.5 py-0.2 rounded-full bg-red-500 text-white text-[10px] font-mono">
                    {alertBadge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </header>

      {/* Plain Farmer Guidance Strip OR Auditor Technical Disclosure Strip */}
      <div className="bg-[#F3EFE6] border-b border-[#E5DFD1]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#374151]">
          <div className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-amber-700 shrink-0" />
            <span>
              <strong>
                {viewMode === "farmer" ? t("farmerNoticePrefix") : t("integrityBannerPrefix")}
              </strong>{" "}
              {viewMode === "farmer" ? t("farmerNoticeBody") : t("integrityBannerBody")}
            </span>
          </div>
          <span className="font-mono text-[10px] text-slate-600">
            {viewMode === "farmer" ? t("farmerNoticeRight") : t("integrityBannerRight")}
          </span>
        </div>
      </div>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6">
        {loading ? (
          <div className="ck-card p-12 text-center text-sm font-semibold text-slate-600">
            {t("loadingText")}
          </div>
        ) : error ? (
          <div className="p-5 rounded-xl bg-red-50 border border-red-200 text-sm text-red-800 font-semibold">
            API Error: {error}
          </div>
        ) : (
          <>
            {activeTab === "farmer_home" && (
              <FarmerHomeView
                dashboard={dashboard}
                onSelectFarm={handleSelectFarm}
                onNavigateTab={setActiveTab}
                t={t}
                lang={lang}
              />
            )}
            {activeTab === "dashboard" && (
              <DashboardTab
                dashboard={dashboard}
                selectedFarmId={selectedFarmId}
                onSelectFarm={handleSelectFarm}
                onNavigateTab={setActiveTab}
                t={t}
              />
            )}
            {activeTab === "twin" && (
              <DigitalTwinTab
                farms={dashboard?.farms || []}
                farmers={dashboard?.farmers || []}
                selectedFarmId={selectedFarmId}
                onSelectFarm={handleSelectFarm}
                dossier={dossier}
                onRefreshAll={loadData}
                t={t}
                viewMode={viewMode}
                lang={lang}
              />
            )}
            {activeTab === "intelligence" && (
              <IntelligenceTab
                farms={dashboard?.farms || []}
                selectedFarmId={selectedFarmId}
                onSelectFarm={handleSelectFarm}
                dossier={dossier}
                modelMetrics={dashboard?.model_metrics}
                onRefreshAll={loadData}
                t={t}
              />
            )}
            {activeTab === "fraud" && (
              <FraudRadarTab
                farms={dashboard?.farms || []}
                selectedFarmId={selectedFarmId}
                onSelectFarm={handleSelectFarm}
                dossier={dossier}
                recentAlerts={dashboard?.recent_alerts || []}
                onRefreshAll={loadData}
                t={t}
              />
            )}
            {activeTab === "farmer" && (
              <FarmerAppTab
                farmers={dashboard?.farmers || []}
                farms={dashboard?.farms || []}
                selectedFarmId={selectedFarmId}
                onSelectFarm={handleSelectFarm}
                dossier={dossier}
                onRefreshAll={loadData}
                t={t}
                viewMode={viewMode}
              />
            )}
            {activeTab === "passport" && (
              <PassportTab
                farms={dashboard?.farms || []}
                selectedFarmId={selectedFarmId}
                onSelectFarm={handleSelectFarm}
                dossier={dossier}
                onRefreshAll={loadData}
                t={t}
                lang={lang}
                viewMode={viewMode}
              />
            )}
          </>
        )}
      </main>

      <JudgeDemoDrawer
        open={demoOpen}
        onClose={() => setDemoOpen(false)}
        onNavigateTab={(tab) => {
          if (viewMode === "farmer" && (tab === "intelligence" || tab === "fraud")) {
            switchViewMode("auditor");
          }
          setActiveTab(tab);
        }}
        completedSteps={completedSteps}
        onToggleStep={toggleDemoStep}
        lang={lang}
      />
    </div>
  );
}
