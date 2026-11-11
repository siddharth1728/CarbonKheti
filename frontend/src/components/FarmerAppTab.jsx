import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  CloudOff,
  Compass,
  RefreshCw,
  Smartphone,
  Upload,
  UserPlus,
  Wifi,
} from "lucide-react";
import { api } from "../api";

const OFFLINE_QUEUE_KEY = "carbonkheti_offline_evidence_v1";

export default function FarmerAppTab({
  farmers,
  farms,
  selectedFarmId,
  onSelectFarm,
  dossier,
  onRefreshAll,
  t,
  viewMode = "farmer",
}) {
  const [farmerForm, setFarmerForm] = useState({
    name: "",
    phone: "+91-98490-",
    village: "",
    district: "Siddipet",
    state: "Telangana",
    land_doc_ref: "TS-PATTA-",
  });
  const [farmerMsg, setFarmerMsg] = useState(null);

  const [offlineMode, setOfflineMode] = useState(false);
  const [gpsLat, setGpsLat] = useState("");
  const [gpsLon, setGpsLon] = useState("");
  const [claimedTrees, setClaimedTrees] = useState(true);
  const [notes, setNotes] = useState("గట్టుపై టేకు & వేప మొక్కలు / Bund teak & neem trees");
  const [photoFile, setPhotoFile] = useState(null);
  const [samplePhotos, setSamplePhotos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [offlineQueue, setOfflineQueue] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || "[]");
    } catch {
      return [];
    }
  });

  useEffect(() => {
    api.getSamplePhotos().then((d) => setSamplePhotos(d.sample_photos || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (dossier?.farm && !gpsLat) {
      setGpsLat(String(dossier.farm.centroid_lat));
      setGpsLon(String(dossier.farm.centroid_lon));
    }
  }, [dossier?.farm, gpsLat]);

  const saveQueue = (q) => {
    setOfflineQueue(q);
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(q));
  };

  const handleRegisterFarmer = async (e) => {
    e.preventDefault();
    setFarmerMsg(null);
    try {
      const res = await api.createFarmer(farmerForm);
      setFarmerMsg(`✓ ${res.farmer.name} (${res.farmer.village})`);
      setFarmerForm({ ...farmerForm, name: "", village: "" });
      await onRefreshAll(selectedFarmId);
    } catch (err) {
      setFarmerMsg(`Error: ${err.message}`);
    }
  };

  const handleCaptureGps = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setGpsLat(pos.coords.latitude.toFixed(6));
          setGpsLon(pos.coords.longitude.toFixed(6));
        },
        () => {
          if (dossier?.farm) {
            setGpsLat(String(dossier.farm.centroid_lat));
            setGpsLon(String(dossier.farm.centroid_lon));
          }
        },
        { timeout: 3000 }
      );
    } else if (dossier?.farm) {
      setGpsLat(String(dossier.farm.centroid_lat));
      setGpsLon(String(dossier.farm.centroid_lon));
    }
  };

  const handleUseSamplePhoto = async (url, filename) => {
    const res = await fetch(url);
    const blob = await res.blob();
    const f = new File([blob], filename, { type: "image/jpeg" });
    setPhotoFile(f);
    setUploadResult({ info: `Photo ready: ${filename}` });
  };

  const fileToDataUrl = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });

  const handleSubmitEvidence = async (e) => {
    e.preventDefault();
    if (!selectedFarmId || !photoFile) {
      setUploadResult({ error: "Select a farm and attach/load a field photo first." });
      return;
    }

    if (offlineMode) {
      const dataUrl = await fileToDataUrl(photoFile);
      const item = {
        local_id: `OFF-${Date.now()}`,
        farm_id: selectedFarmId,
        filename: photoFile.name,
        dataUrl,
        capture_lat: gpsLat ? Number(gpsLat) : null,
        capture_lon: gpsLon ? Number(gpsLon) : null,
        claimed_tree_presence: claimedTrees,
        notes,
        captured_at: new Date().toISOString(),
      };
      saveQueue([...offlineQueue, item]);
      setUploadResult({
        info: t("ffa_offline_banner"),
      });
      return;
    }

    setUploading(true);
    setUploadResult(null);
    try {
      const fd = new FormData();
      fd.append("farm_id", selectedFarmId);
      fd.append("claimed_tree_presence", String(claimedTrees));
      if (gpsLat) fd.append("capture_lat", gpsLat);
      if (gpsLon) fd.append("capture_lon", gpsLon);
      fd.append("offline_captured", "false");
      fd.append("notes", notes);
      fd.append("photo", photoFile);

      const res = await api.uploadEvidence(fd);
      const clean = res.alerts_triggered.length === 0;
      setUploadResult({
        success:
          viewMode === "farmer"
            ? clean
              ? t("ffa_plain_ok")
              : t("ffa_plain_warn")
            : `Evidence ${res.evidence_id} (${res.status}). Alerts: ${res.alerts_triggered.length}`,
        isWarn: !clean,
      });
      await onRefreshAll(selectedFarmId);
    } catch (err) {
      setUploadResult({ error: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleSyncOfflineQueue = async () => {
    if (offlineMode || offlineQueue.length === 0) return;
    setUploading(true);
    let synced = 0;
    try {
      for (const item of offlineQueue) {
        const res = await fetch(item.dataUrl);
        const blob = await res.blob();
        const file = new File([blob], item.filename, { type: "image/jpeg" });
        const fd = new FormData();
        fd.append("farm_id", item.farm_id);
        fd.append("claimed_tree_presence", String(item.claimed_tree_presence));
        if (item.capture_lat != null) fd.append("capture_lat", String(item.capture_lat));
        if (item.capture_lon != null) fd.append("capture_lon", String(item.capture_lon));
        fd.append("offline_captured", "true");
        fd.append("notes", `[Offline sync] ${item.notes}`);
        fd.append("photo", file);
        await api.uploadEvidence(fd);
        synced += 1;
      }
      saveQueue([]);
      setUploadResult({ success: `✓ ${synced} photo(s) sent & saved!` });
      await onRefreshAll(selectedFarmId);
    } catch (err) {
      setUploadResult({ error: `Sync error: ${err.message}` });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      <div className="lg:col-span-5 flex justify-center">
        <div className="w-full max-w-[420px] bg-[#0D2818] rounded-[32px] p-3 shadow-2xl border-4 border-[#1F4E32]">
          <div className="bg-[#FAF8F4] rounded-[24px] overflow-hidden">
            <div className="bg-[#0D2818] text-white px-4 py-3.5 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-emerald-400 shrink-0" />
                <span className="text-sm font-bold truncate">{t("fa_app_title")}</span>
              </div>
              <button
                type="button"
                onClick={() => setOfflineMode(!offlineMode)}
                className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold transition shrink-0 ${
                  offlineMode ? "bg-amber-400 text-amber-950" : "bg-emerald-500 text-emerald-950"
                }`}
              >
                {offlineMode ? <CloudOff className="w-3.5 h-3.5" /> : <Wifi className="w-3.5 h-3.5" />}
                {offlineMode ? t("fa_offline") : t("fa_online")}
              </button>
            </div>

            <form onSubmit={handleSubmitEvidence} className="p-4 space-y-4 text-xs">
              {/* Step 1 */}
              <div className="bg-white p-3 rounded-xl border border-[#E5DFD1]">
                <label className="block font-extrabold text-[#0D2818] mb-1.5">
                  {viewMode === "farmer" ? t("ffa_step1") : t("fa_target_farm")}
                </label>
                <select
                  value={selectedFarmId || ""}
                  onChange={(e) => {
                    onSelectFarm(e.target.value);
                    const f = farms.find((x) => x.id === e.target.value);
                    if (f) {
                      setGpsLat(String(f.centroid_lat));
                      setGpsLon(String(f.centroid_lon));
                    }
                  }}
                  className="w-full border border-[#E5DFD1] rounded-lg px-2.5 py-2.5 bg-[#FAF8F4] font-semibold"
                >
                  {farms.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Step 2 */}
              <div className="bg-white p-3 rounded-xl border border-[#E5DFD1] space-y-2">
                <div className="font-extrabold text-[#0D2818]">
                  {viewMode === "farmer" ? t("ffa_step2") : "GPS"}
                </div>
                {viewMode === "farmer" && (
                  <p className="text-[11px] text-slate-500">{t("ffa_gps_hint")}</p>
                )}
                <button
                  type="button"
                  onClick={handleCaptureGps}
                  className="w-full inline-flex items-center justify-center gap-2 py-2.5 rounded-xl bg-[#F3EFE6] text-[#0D2818] font-extrabold hover:bg-[#E5DFD1]"
                >
                  <Compass className="w-4 h-4 text-emerald-700" /> {t("fa_capture_gps")}
                </button>
                {viewMode === "auditor" ? (
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="text"
                      value={gpsLat}
                      onChange={(e) => setGpsLat(e.target.value)}
                      placeholder={t("fa_gps_lat")}
                      className="w-full font-mono border border-[#E5DFD1] rounded-lg px-2 py-1.5 bg-[#FAF8F4]"
                    />
                    <input
                      type="text"
                      value={gpsLon}
                      onChange={(e) => setGpsLon(e.target.value)}
                      placeholder={t("fa_gps_lon")}
                      className="w-full font-mono border border-[#E5DFD1] rounded-lg px-2 py-1.5 bg-[#FAF8F4]"
                    />
                  </div>
                ) : (
                  gpsLat && (
                    <div className="text-[11px] font-semibold text-emerald-800 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Location captured ({gpsLat}, {gpsLon})
                    </div>
                  )
                )}
              </div>

              {/* Step 3 */}
              <div className="bg-white p-3 rounded-xl border border-[#E5DFD1] space-y-2.5">
                <label className="block font-extrabold text-[#0D2818]">
                  {viewMode === "farmer" ? t("ffa_step3") : t("fa_photo_lbl")}
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setPhotoFile(e.target.files?.[0] || null)}
                  className="w-full text-[11px] file:mr-2 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-[#0D2818] file:text-white file:font-semibold"
                />
                {samplePhotos.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {samplePhotos.map((sp) => (
                      <button
                        key={sp.filename}
                        type="button"
                        onClick={() => handleUseSamplePhoto(sp.url, sp.filename)}
                        className="text-[10px] px-2.5 py-1 rounded-md bg-[#FAF8F4] border border-[#E5DFD1] hover:bg-[#F3EFE6] font-semibold"
                      >
                        Demo: {sp.filename.split("_")[0]}
                      </button>
                    ))}
                  </div>
                )}

                <label className="flex items-center gap-2 font-semibold text-slate-700 pt-1">
                  <input
                    type="checkbox"
                    checked={claimedTrees}
                    onChange={(e) => setClaimedTrees(e.target.checked)}
                    className="accent-[#0D2818]"
                  />
                  {t("fa_attest_trees")}
                </label>

                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t("fa_notes_lbl")}
                  className="w-full border border-[#E5DFD1] rounded-lg px-2.5 py-2 bg-[#FAF8F4]"
                />
              </div>

              <button
                type="submit"
                disabled={uploading}
                className="w-full inline-flex items-center justify-center gap-2 py-3 rounded-xl bg-emerald-700 text-white text-sm font-extrabold hover:bg-emerald-800 disabled:opacity-50 shadow"
              >
                {offlineMode ? <CloudOff className="w-4 h-4" /> : <Upload className="w-4 h-4" />}
                {offlineMode ? t("fa_save_offline") : uploading ? t("fa_submitting") : t("fa_submit_online")}
              </button>

              {offlineQueue.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 space-y-1.5">
                  <div className="flex items-center justify-between font-bold text-amber-900">
                    <span>{t("fa_queue_pending")}: {offlineQueue.length}</span>
                    <button
                      type="button"
                      disabled={offlineMode || uploading}
                      onClick={handleSyncOfflineQueue}
                      className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-600 text-white disabled:opacity-40"
                    >
                      <RefreshCw className="w-3 h-3" /> {t("fa_sync_now")}
                    </button>
                  </div>
                </div>
              )}

              {uploadResult && (
                <div
                  className={`p-3 rounded-xl text-xs font-semibold border ${
                    uploadResult.error || uploadResult.isWarn
                      ? "bg-amber-50 border-amber-300 text-amber-900"
                      : uploadResult.info
                      ? "bg-blue-50 border-blue-200 text-blue-800"
                      : "bg-emerald-50 border-emerald-200 text-emerald-800"
                  }`}
                >
                  {uploadResult.error || uploadResult.info || uploadResult.success}
                </div>
              )}
            </form>
          </div>
        </div>
      </div>

      <div className="lg:col-span-7 space-y-6">
        <form onSubmit={handleRegisterFarmer} className="ck-card p-5 space-y-3">
          <h3 className="text-sm font-bold text-[#0D2818] flex items-center gap-2">
            <UserPlus className="w-4 h-4 text-emerald-700" />
            {t("fa_onboard_title")}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <input
              type="text"
              required
              placeholder={t("fa_name_ph")}
              value={farmerForm.name}
              onChange={(e) => setFarmerForm({ ...farmerForm, name: e.target.value })}
              className="border border-[#E5DFD1] rounded-lg px-3 py-2.5"
            />
            <input
              type="text"
              required
              placeholder={t("fa_village_ph")}
              value={farmerForm.village}
              onChange={(e) => setFarmerForm({ ...farmerForm, village: e.target.value })}
              className="border border-[#E5DFD1] rounded-lg px-3 py-2.5"
            />
            <input
              type="text"
              required
              placeholder={t("fa_district_ph")}
              value={farmerForm.district}
              onChange={(e) => setFarmerForm({ ...farmerForm, district: e.target.value })}
              className="border border-[#E5DFD1] rounded-lg px-3 py-2.5"
            />
            <input
              type="text"
              required
              placeholder={t("fa_state_ph")}
              value={farmerForm.state}
              onChange={(e) => setFarmerForm({ ...farmerForm, state: e.target.value })}
              className="border border-[#E5DFD1] rounded-lg px-3 py-2.5"
            />
            <input
              type="text"
              placeholder={t("fa_doc_ph")}
              value={farmerForm.land_doc_ref}
              onChange={(e) => setFarmerForm({ ...farmerForm, land_doc_ref: e.target.value })}
              className="border border-[#E5DFD1] rounded-lg px-3 py-2.5"
            />
            <button
              type="submit"
              className="rounded-lg bg-[#0D2818] text-white font-bold px-4 py-2.5 hover:bg-[#163A24]"
            >
              {t("fa_register_btn")}
            </button>
          </div>
          {farmerMsg && <div className="text-xs font-semibold text-emerald-800">{farmerMsg}</div>}
          <div className="text-[11px] text-slate-500">
            {t("fa_enrolled")}: <strong>{farmers.length}</strong>
          </div>
        </form>

        <div className="ck-card p-5 space-y-3">
          <h3 className="text-sm font-bold text-[#0D2818] flex items-center gap-2">
            <Camera className="w-4 h-4 text-[#163A24]" />
            {t("fa_history_title")} ({dossier?.farm?.name})
          </h3>
          <div className="space-y-3">
            {(dossier?.evidence_records || []).map((ev) => (
              <div
                key={ev.id}
                className="flex flex-col sm:flex-row gap-3 p-3 rounded-xl border border-[#E5DFD1] bg-[#FAF8F4]"
              >
                <img
                  src={ev.file_path}
                  alt={ev.original_filename}
                  className="w-28 h-20 object-cover rounded-lg border border-[#E5DFD1] shrink-0"
                />
                <div className="flex-1 text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[#0D2818]">{ev.original_filename}</span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                        ev.status === "VERIFIED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-amber-100 text-amber-900"
                      }`}
                    >
                      {ev.status === "VERIFIED" ? (
                        <span className="inline-flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> VERIFIED
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3" /> CHECK NEEDED
                        </span>
                      )}
                    </span>
                  </div>
                  {viewMode === "auditor" && (
                    <div className="font-mono text-[11px] text-slate-600">
                      SHA-256: {ev.file_sha256.slice(0, 18)}… · dHash: {ev.perceptual_dhash}
                    </div>
                  )}
                  <div className="text-[11px] text-slate-600">
                    {ev.exif_present
                      ? `GPS & Camera Verified (${ev.upload_timestamp.slice(0, 10)})`
                      : "No camera GPS found inside photo"}
                  </div>
                  <div className="text-[11px] text-slate-500">{ev.notes}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
