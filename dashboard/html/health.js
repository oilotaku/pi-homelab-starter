const CONFIG = window.DASHBOARD_CONFIG || {};
const host = window.location.hostname || CONFIG.fallbackHost || "localhost";
document.getElementById("hostLine").textContent = "連線主機：" + host;

async function refreshHost() {
  try {
    const res = await fetch("pi_status.json?_=" + Date.now());
    const d = await res.json();
    document.getElementById("stCpuTemp").textContent = d.cpu_temp_c.toFixed(1) + " °C";
    document.getElementById("stLoad").textContent = d.load_1.toFixed(2);
    document.getElementById("stCores").textContent = "5/15分: " + d.load_5.toFixed(2) + " / " + d.load_15.toFixed(2) + "(" + d.cpu_cores + " 核)";
    document.getElementById("stMem").textContent = d.mem_percent + "%";
    document.getElementById("stMemSub").textContent = d.mem_used_gb + " / " + d.mem_total_gb + " GB";
    document.getElementById("stDiskSys").textContent = d.disk_system_percent + "%";
    document.getElementById("stDiskSysSub").textContent = d.disk_system_used_gb + " / " + d.disk_system_total_gb + " GB";
    if (d.disk_media_percent != null) {
      document.getElementById("stMediaStat").hidden = false;
      document.getElementById("stDiskMedia").textContent = d.disk_media_percent + "%";
      document.getElementById("stDiskMediaSub").textContent = d.disk_media_used_gb + " / " + d.disk_media_total_gb + " GB";
    }
    document.getElementById("stUptime").textContent = d.uptime;
    document.getElementById("hostUpdated").textContent = "更新於 " + d.generated_at;
  } catch (e) {
    document.getElementById("hostUpdated").textContent = "狀態讀取失敗";
  }
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

const SMART_LABEL = { ok: "正常", attention: "需留意", fail: "異常", unknown: "未知" };

function fmtHours(h) {
  if (h == null) return "-";
  return h.toLocaleString() + " 小時(約 " + (h / 24 / 365).toFixed(1) + " 年)";
}

async function refreshSmart() {
  const grid = document.getElementById("smartGrid");
  try {
    const res = await fetch("health.json?_=" + Date.now());
    const d = await res.json();

    grid.innerHTML = !d.smart.length
      ? '<div class="card-surface smart-card">未設定 SMART_DISKS,略過磁碟健康檢查(見 scripts/generate_health.py 說明)</div>'
      : d.smart.map(s => {
      const notes = (s.notes && s.notes.length)
        ? `<div class="smart-notes">${s.notes.map(n => "⚠ " + esc(n)).join("<br>")}</div>`
        : "";
      return `
        <div class="card-surface smart-card">
          <div class="smart-head">
            <span class="device">${esc(s.device)}</span>
            <span class="badge ${esc(s.status)}">${esc(SMART_LABEL[s.status] || s.status)}</span>
          </div>
          <div class="smart-stats">
            <div><div class="label">溫度</div>${s.temp_c != null ? s.temp_c + " °C" : "-"}</div>
            <div><div class="label">通電時數</div>${fmtHours(s.power_on_hours)}</div>
            <div><div class="label">重新配置磁區</div>${s.reallocated_sectors ?? "-"}</div>
            <div><div class="label">待處理磁區</div>${s.pending_sectors ?? "-"}</div>
            <div><div class="label">離線不可修正磁區</div>${s.offline_uncorrectable ?? "-"}</div>
            <div><div class="label">磁頭停靠循環</div>${s.load_cycle_count != null ? s.load_cycle_count.toLocaleString() : "-"}</div>
          </div>
          ${notes}
        </div>`;
    }).join("");

    document.getElementById("dockerList").innerHTML = (d.docker.containers || []).map(c => `
      <div class="docker-row">
        <span class="name">${esc(c.name)}</span>
        <span class="status-text">${esc(c.status)}</span>
        <span class="badge ${c.state === 'running' && c.health !== 'unhealthy' ? 'ok' : 'fail'}">
          ${esc(c.health === 'unhealthy' ? '不健康' : (c.state === 'running' ? '運作中' : c.state))}
        </span>
      </div>`).join("") || "<div class=\"docker-row\">無容器資料</div>";

    document.getElementById("smartUpdated").textContent = "更新於 " + d.generated_at;
  } catch (e) {
    grid.innerHTML = '<div class="card-surface smart-card">讀取失敗</div>';
    document.getElementById("dockerList").innerHTML = "讀取失敗";
  }
}

async function refreshLan() {
  try {
    const res = await fetch("devices.json?_=" + Date.now());
    const d = await res.json();
    document.getElementById("lanSummary").textContent = d.online_count + " / " + d.total_count + " 台裝置在線(更新於 " + d.generated_at + ")";
    const online = d.devices.filter(dev => dev.online);
    document.getElementById("lanOnlineList").innerHTML = online.map(dev =>
      `<span class="lan-chip">${esc(dev.ip)}${dev.vendor && dev.vendor !== '-' ? ' · ' + esc(dev.vendor) : ''}</span>`
    ).join("");
  } catch (e) {
    document.getElementById("lanSummary").textContent = "讀取失敗";
  }
}

refreshHost();
refreshSmart();
refreshLan();
setInterval(refreshHost, 30000);
setInterval(refreshSmart, 60000);
setInterval(refreshLan, 60000);
