const API_BASE = "";

async function handleJson(res) {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      msg = err.detail || msg;
    } catch {
      // ignore
    }
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  getDashboard: () => fetch(`${API_BASE}/api/dashboard`).then(handleJson),
  getFarmers: () => fetch(`${API_BASE}/api/farmers`).then(handleJson),
  createFarmer: (data) =>
    fetch(`${API_BASE}/api/farmers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(handleJson),

  getFarm: (farmId, simulateTamperSeq = null) => {
    const qs = simulateTamperSeq ? `?simulate_tamper_seq=${simulateTamperSeq}` : "";
    return fetch(`${API_BASE}/api/farms/${farmId}${qs}`).then(handleJson);
  },

  registerFarm: (data) =>
    fetch(`${API_BASE}/api/farms`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(handleJson),

  runEstimation: (farmId, data) =>
    fetch(`${API_BASE}/api/farms/${farmId}/estimate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then(handleJson),

  uploadEvidence: (formData) =>
    fetch(`${API_BASE}/api/evidence/upload`, {
      method: "POST",
      body: formData,
    }).then(handleJson),

  simulateFraud: (farmId, scenario) =>
    fetch(`${API_BASE}/api/fraud/simulate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ farm_id: farmId, scenario }),
    }).then(handleJson),

  resolveAlert: (alertId) =>
    fetch(`${API_BASE}/api/alerts/${alertId}/resolve`, {
      method: "POST",
    }).then(handleJson),

  issuePassport: (farmId) =>
    fetch(`${API_BASE}/api/passports/${farmId}/issue`, {
      method: "POST",
    }).then(handleJson),

  verifyPassport: (farmId, simulateTamperSeq = null) => {
    const qs = simulateTamperSeq ? `?simulate_tamper_seq=${simulateTamperSeq}` : "";
    return fetch(`${API_BASE}/api/passports/${farmId}/verify${qs}`).then(handleJson);
  },

  getSamplePhotos: () => fetch(`${API_BASE}/api/sample-photos`).then(handleJson),
};

