const CONFIG = window.DASHBOARD_CONFIG || { serviceGroups: [] };
const host = window.location.hostname || CONFIG.fallbackHost || "localhost";
document.getElementById("hostLine").textContent = "連線主機：" + host;

function renderServiceGroups() {
  const container = document.getElementById("serviceGroups");
  container.replaceChildren();
  for (const group of CONFIG.serviceGroups || []) {
    const groupEl = document.createElement("div");
    groupEl.className = "group";

    const h2 = document.createElement("h2");
    h2.textContent = group.title;
    groupEl.appendChild(h2);

    const grid = document.createElement("div");
    grid.className = "grid";
    for (const svc of group.services || []) {
      const a = document.createElement("a");
      a.className = "card card-surface";
      a.href = "http://" + host + ":" + svc.port + (svc.path || "");

      const icon = document.createElement("span");
      icon.className = "icon";
      icon.textContent = svc.icon;

      const label = document.createElement("span");
      const name = document.createElement("span");
      name.className = "name";
      name.textContent = svc.name;
      const desc = document.createElement("span");
      desc.className = "desc";
      desc.textContent = svc.desc;
      label.appendChild(name);
      label.appendChild(document.createElement("br"));
      label.appendChild(desc);

      a.appendChild(icon);
      a.appendChild(label);
      grid.appendChild(a);
    }
    groupEl.appendChild(grid);
    container.appendChild(groupEl);
  }
}
renderServiceGroups();

function setBadge(el, status, text) {
  el.className = "badge " + status;
  el.textContent = text;
}

async function refreshHealthStrip() {
  try {
    const res = await fetch("pi_status.json?_=" + Date.now());
    const d = await res.json();
    document.getElementById("hsTemp").textContent = d.cpu_temp_c.toFixed(1) + " °C";
  } catch (e) {
    document.getElementById("hsTemp").textContent = "讀取失敗";
  }

  try {
    const res = await fetch("health.json?_=" + Date.now());
    const d = await res.json();

    const rank = { ok: 0, attention: 1, unknown: 1, fail: 2 };
    const worstSmart = d.smart.reduce((acc, s) => (rank[s.status] > rank[acc] ? s.status : acc), "ok");
    const smartLabel = { ok: "正常", attention: "需留意", fail: "異常", unknown: "未知" }[worstSmart];
    setBadge(document.getElementById("hsSmart"), worstSmart, smartLabel);

    const containers = (d.docker && d.docker.containers) || [];
    const unhealthy = containers.filter(c => c.state !== "running" || c.health === "unhealthy");
    const dockerStatus = unhealthy.length ? "fail" : "ok";
    const dockerLabel = unhealthy.length ? unhealthy.length + " 個異常" : containers.length + " 個正常";
    setBadge(document.getElementById("hsDocker"), dockerStatus, dockerLabel);
  } catch (e) {
    setBadge(document.getElementById("hsSmart"), "unknown", "讀取失敗");
    setBadge(document.getElementById("hsDocker"), "unknown", "讀取失敗");
  }

  try {
    const res = await fetch("devices.json?_=" + Date.now());
    const d = await res.json();
    document.getElementById("hsLan").textContent = d.online_count + " / " + d.total_count + " 在線";
  } catch (e) {
    document.getElementById("hsLan").textContent = "讀取失敗";
  }
}
refreshHealthStrip();
setInterval(refreshHealthStrip, 30000);
