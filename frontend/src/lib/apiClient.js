// Local dev falls back to the local backend. A production build (e.g. Vercel)
// has no such fallback: if VITE_API_URL is missing there, request() below fails
// with a clear message instead of quietly calling the wrong host. (Vercel's
// catch-all rewrite would otherwise answer /api/* calls with index.html.)
const API_URL = (
  import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://127.0.0.1:8000" : "")
).replace(/\/+$/, "");

/**
 * Thin fetch wrapper for the FastAPI backend. Every authenticated call needs
 * a token (the JWT returned by /api/auth/login) passed explicitly — this
 * file has no knowledge of where that token is stored; useAuth.jsx owns that.
 */
async function request(path, { method = "GET", body, token, raw = false } = {}) {
  if (!API_URL) {
    throw new Error(
      "VITE_API_URL is not set for this build. Set it to the backend URL in the " +
        "hosting environment variables (Vercel: Project Settings > Environment Variables) and redeploy."
    );
  }

  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* response wasn't JSON — keep statusText */
    }
    throw new Error(detail);
  }

  if (raw) return res; // caller wants the raw Response (file downloads)

  const contentType = res.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return res.json();
  return res;
}

/** Trigger a browser download from a fetch Response containing a file. */
async function downloadResponse(res, fallbackFilename) {
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : fallbackFilename;

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  // ---- Auth ---------------------------------------------------------------
  register: (data) => request("/api/auth/register", { method: "POST", body: data }),
  login: (data) => request("/api/auth/login", { method: "POST", body: data }),

  // ---- My profile / laboratory --------------------------------------------
  getMyProfile: (token) => request("/api/users/me", { token }),
  updateMyProfile: (data, token) => request("/api/users/me", { method: "PUT", body: data, token }),
  getMyLaboratory: (token) => request("/api/laboratories/me", { token }),
  updateMyLaboratory: (data, token) => request("/api/laboratories/me", { method: "PUT", body: data, token }),

  // ---- Users (lab admin) ----------------------------------------------------
  getUsers: (token) => request("/api/users", { token }),
  createUser: (data, token) => request("/api/users", { method: "POST", body: data, token }),

  // ---- Instruments --------------------------------------------------------
  getInstruments: (token) => request("/api/instruments", { token }),
  getInstrument: (id, token) => request(`/api/instruments/${id}`, { token }),
  createInstrument: (data, token) =>
    request("/api/instruments", { method: "POST", body: data, token }),
  updateInstrument: (id, data, token) =>
    request(`/api/instruments/${id}`, { method: "PUT", body: data, token }),

  // ---- Standards / test definitions / applicability / MPE (admin) -----------
  getStandards: (token) => request("/api/standards", { token }),
  createStandard: (data, token) => request("/api/standards", { method: "POST", body: data, token }),
  updateStandard: (id, data, token) => request(`/api/standards/${id}`, { method: "PUT", body: data, token }),

  getTestDefinitions: (token) => request("/api/test-definitions", { token }),
  createTestDefinition: (data, token) =>
    request("/api/test-definitions", { method: "POST", body: data, token }),
  updateTestDefinition: (id, data, token) =>
    request(`/api/test-definitions/${id}`, { method: "PUT", body: data, token }),

  getApplicabilityRules: (token) => request("/api/test-applicability-rules", { token }),
  createApplicabilityRule: (data, token) =>
    request("/api/test-applicability-rules", { method: "POST", body: data, token }),
  updateApplicabilityRule: (id, data, token) =>
    request(`/api/test-applicability-rules/${id}`, { method: "PUT", body: data, token }),

  getMpeRules: (token) => request("/api/mpe-rules", { token }),
  createMpeRule: (data, token) => request("/api/mpe-rules", { method: "POST", body: data, token }),
  updateMpeRule: (id, data, token) => request(`/api/mpe-rules/${id}`, { method: "PUT", body: data, token }),

  // ---- Test equipment -------------------------------------------------------
  getTestEquipment: (token) => request("/api/test-equipment", { token }),
  createTestEquipment: (data, token) =>
    request("/api/test-equipment", { method: "POST", body: data, token }),
  updateTestEquipment: (id, data, token) =>
    request(`/api/test-equipment/${id}`, { method: "PUT", body: data, token }),
  deleteTestEquipment: (id, token) =>
    request(`/api/test-equipment/${id}`, { method: "DELETE", token }),

  // ---- Test sessions --------------------------------------------------------
  getTestSessions: (token) => request("/api/test-sessions", { token }),
  getTestSession: (id, token) => request(`/api/test-sessions/${id}`, { token }),
  createTestSession: (data, token) =>
    request("/api/test-sessions", { method: "POST", body: data, token }),
  updateTestSessionStatus: (id, status, token) =>
    request(`/api/test-sessions/${id}/status`, { method: "PATCH", body: { status }, token }),

  // ---- Session tests / observations / calculations ---------------------------
  addTestToSession: (testSessionId, data, token) =>
    request(`/api/test-sessions/${testSessionId}/tests`, { method: "POST", body: data, token }),
  addObservation: (sessionTestId, data, token) =>
    request(`/api/test-sessions/${sessionTestId}/observations`, { method: "POST", body: data, token }),
  saveCalculationResult: (sessionTestId, data, token) =>
    request(`/api/test-sessions/${sessionTestId}/calculation-result`, { method: "POST", body: data, token }),

  // ---- Environmental conditions ----------------------------------------------
  addEnvironmentalCondition: (data, token) =>
    request("/api/environmental-conditions", { method: "POST", body: data, token }),
  getEnvironmentalConditions: (testSessionId, token) =>
    request(`/api/environmental-conditions/session/${testSessionId}`, { token }),

  // ---- Reports --------------------------------------------------------------
  getReportData: (testSessionId, token) =>
    request(`/api/test-sessions/${testSessionId}/report-data`, { token }),
  generateReport: (testSessionId, token) =>
    request(`/api/test-sessions/${testSessionId}/generate-report`, { method: "POST", token, raw: true }),
  downloadDocx: (testSessionId, token) =>
    request(`/api/test-sessions/${testSessionId}/report/download-docx`, { token, raw: true }),
  downloadPdf: (testSessionId, token) =>
    request(`/api/test-sessions/${testSessionId}/report/download-pdf`, { token, raw: true }),
  approveReport: (testSessionId, token) =>
    request(`/api/test-sessions/${testSessionId}/approve-report`, { method: "PATCH", token }),
};

export { API_URL, downloadResponse };
