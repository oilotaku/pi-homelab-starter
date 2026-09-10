// 這個 dashboard 有兩種資料來源:
// 1. 同源的靜態 JSON(pi_status.json / health.json / devices.json),由主機上
//    的 cron 腳本(../scripts/generate_*.py)定期產生,唯讀、不需要後端服務。
// 2. pi-dashboard-backend(見 repo 的 backend/ 目錄,原生 systemd service)提供
//    的即時 API:CPU/RAM 即時值、容器列表與啟停/重啟、系統音量。沒部署這個
//    後端(config.js 的 backendPort 留 null)時,相關功能會自動隱藏。

const TOKEN_KEY = "dashboardToken";

export function getConfig() {
  return window.DASHBOARD_CONFIG || {};
}

export function backendBase() {
  const cfg = getConfig();
  if (!cfg.backendPort) return null;
  const host = window.location.hostname || cfg.fallbackHost || "localhost";
  return `http://${host}:${cfg.backendPort}`;
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function fetchStatic(path) {
  const res = await fetch(`${path}?_=${Date.now()}`);
  if (!res.ok) throw new Error(`${path}: HTTP ${res.status}`);
  return res.json();
}

export const getPiStatus = () => fetchStatic("pi_status.json");
export const getHealth = () => fetchStatic("health.json");
export const getDevices = () => fetchStatic("devices.json");

async function backendFetch(path, opts = {}) {
  const base = backendBase();
  if (!base) throw new Error("backend not configured");
  const headers = { ...(opts.headers || {}) };
  if (opts.auth) {
    const token = getToken();
    if (!token) throw new Error("需要先輸入 PIN");
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(base + path, { ...opts, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 429 && data.retry_after_s) {
      throw new Error(`PIN 連續錯誤太多次,鎖定中,請 ${data.retry_after_s} 秒後再試`);
    }
    throw new Error(data.error || `HTTP ${res.status}`);
  }
  return data;
}

export const getLiveStats = () => backendFetch("/api/stats");
export const getContainers = () => backendFetch("/api/containers");
export const containerAction = (name, action) =>
  backendFetch(`/api/containers/${encodeURIComponent(name)}/${action}`, { method: "POST", auth: true });
export const getVolume = () => backendFetch("/api/volume");
export const setVolume = (payload) =>
  backendFetch("/api/volume", {
    method: "POST",
    auth: true,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
