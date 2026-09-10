<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { getConfig, getPiStatus, getHealth, getDevices } from "../api.js";
import ContainersPanel from "../components/ContainersPanel.vue";

const cfg = getConfig();

const host = ref(null);
const hostUpdated = ref("");
const hostFailed = ref(false);

const smart = ref([]);
const staticContainers = ref([]);
const smartUpdated = ref("");
const smartFailed = ref(false);

const lanSummary = ref("讀取中…");
const lanOnline = ref([]);

const SMART_LABEL = { ok: "正常", attention: "需留意", fail: "異常", unknown: "未知" };

function fmtHours(h) {
  if (h == null) return "-";
  return h.toLocaleString() + " 小時(約 " + (h / 24 / 365).toFixed(1) + " 年)";
}

async function refreshHost() {
  try {
    host.value = await getPiStatus();
    hostUpdated.value = "更新於 " + host.value.generated_at;
    hostFailed.value = false;
  } catch {
    hostFailed.value = true;
  }
}

async function refreshSmart() {
  try {
    const d = await getHealth();
    smart.value = d.smart;
    staticContainers.value = (d.docker && d.docker.containers) || [];
    smartUpdated.value = "更新於 " + d.generated_at;
    smartFailed.value = false;
  } catch {
    smartFailed.value = true;
  }
}

async function refreshLan() {
  try {
    const d = await getDevices();
    lanSummary.value = `${d.online_count} / ${d.total_count} 台裝置在線(更新於 ${d.generated_at})`;
    lanOnline.value = d.devices.filter((dev) => dev.online);
  } catch {
    lanSummary.value = "讀取失敗";
  }
}

let t1, t2, t3;
onMounted(() => {
  refreshHost();
  refreshSmart();
  refreshLan();
  t1 = setInterval(refreshHost, 30000);
  t2 = setInterval(refreshSmart, 60000);
  t3 = setInterval(refreshLan, 60000);
});
onUnmounted(() => {
  clearInterval(t1);
  clearInterval(t2);
  clearInterval(t3);
});
</script>

<template>
  <div class="page-header">
    <h1>裝置健康儀表板</h1>
    <p class="subtitle">主機資源、磁碟 SMART 健康、Docker 容器、區網裝置線上狀態一覽</p>
  </div>

  <div class="group">
    <h2>主機資源</h2>
    <div v-if="hostFailed" class="empty-hint card-surface">讀取失敗</div>
    <div v-else-if="host" class="stat-grid card-surface">
      <div class="stat"><div class="label">CPU 溫度</div><div class="value">{{ host.cpu_temp_c.toFixed(1) }} °C</div></div>
      <div class="stat">
        <div class="label">CPU 負載</div>
        <div class="value">{{ host.load_1.toFixed(2) }}</div>
        <div class="subvalue">5/15分: {{ host.load_5.toFixed(2) }} / {{ host.load_15.toFixed(2) }}({{ host.cpu_cores }} 核)</div>
      </div>
      <div class="stat">
        <div class="label">記憶體</div>
        <div class="value">{{ host.mem_percent }}%</div>
        <div class="subvalue">{{ host.mem_used_gb }} / {{ host.mem_total_gb }} GB</div>
      </div>
      <div class="stat">
        <div class="label">系統碟 /</div>
        <div class="value">{{ host.disk_system_percent }}%</div>
        <div class="subvalue">{{ host.disk_system_used_gb }} / {{ host.disk_system_total_gb }} GB</div>
      </div>
      <div class="stat" v-if="host.disk_media_percent != null">
        <div class="label">媒體碟</div>
        <div class="value">{{ host.disk_media_percent }}%</div>
        <div class="subvalue">{{ host.disk_media_used_gb }} / {{ host.disk_media_total_gb }} GB</div>
      </div>
      <div class="stat"><div class="label">開機時間</div><div class="value">{{ host.uptime }}</div></div>
    </div>
    <div v-else class="empty-hint card-surface">讀取中…</div>
    <div class="section-updated">{{ hostUpdated }}</div>
  </div>

  <div class="group">
    <h2>磁碟健康(SMART)</h2>
    <div v-if="smartFailed" class="empty-hint card-surface">讀取失敗</div>
    <div v-else-if="!smart.length" class="empty-hint card-surface">未設定 SMART_DISKS,略過磁碟健康檢查(見 scripts/generate_health.py 說明)</div>
    <div v-else class="smart-grid">
      <div v-for="s in smart" :key="s.device" class="card-surface smart-card">
        <div class="smart-head">
          <span class="device">{{ s.device }}</span>
          <span class="badge" :class="s.status">{{ SMART_LABEL[s.status] || s.status }}</span>
        </div>
        <div class="smart-stats">
          <div><div class="label">溫度</div>{{ s.temp_c != null ? s.temp_c + " °C" : "-" }}</div>
          <div><div class="label">通電時數</div>{{ fmtHours(s.power_on_hours) }}</div>
          <div><div class="label">重新配置磁區</div>{{ s.reallocated_sectors ?? "-" }}</div>
          <div><div class="label">待處理磁區</div>{{ s.pending_sectors ?? "-" }}</div>
          <div><div class="label">離線不可修正磁區</div>{{ s.offline_uncorrectable ?? "-" }}</div>
          <div><div class="label">磁頭停靠循環</div>{{ s.load_cycle_count != null ? s.load_cycle_count.toLocaleString() : "-" }}</div>
        </div>
        <div v-if="s.notes && s.notes.length" class="smart-notes">
          <div v-for="n in s.notes" :key="n">⚠ {{ n }}</div>
        </div>
      </div>
    </div>
    <div class="section-updated">{{ smartUpdated }}</div>
  </div>

  <!-- 有部署 pi-dashboard-backend 時用即時、可操作的版本;沒有就退回唯讀列表 -->
  <ContainersPanel v-if="cfg.backendPort" />
  <div v-else class="group">
    <h2>Docker 容器</h2>
    <div class="docker-list card-surface">
      <div v-if="!staticContainers.length" class="docker-row">無容器資料</div>
      <div v-for="c in staticContainers" :key="c.name" class="docker-row">
        <span class="name">{{ c.name }}</span>
        <span class="status-text">{{ c.status }}</span>
        <span class="badge" :class="c.state === 'running' && c.health !== 'unhealthy' ? 'ok' : 'fail'">
          {{ c.health === "unhealthy" ? "不健康" : c.state === "running" ? "運作中" : c.state }}
        </span>
      </div>
    </div>
  </div>

  <div class="group">
    <h2>區網裝置</h2>
    <div class="lan-card card-surface">
      <div class="lan-summary">{{ lanSummary }}</div>
      <div class="lan-online-list">
        <span v-for="dev in lanOnline" :key="dev.ip" class="lan-chip">
          {{ dev.ip }}<template v-if="dev.vendor && dev.vendor !== '-'"> · {{ dev.vendor }}</template>
        </span>
      </div>
      <router-link class="lan-link" to="/devices">查看完整清單 →</router-link>
    </div>
  </div>
</template>
