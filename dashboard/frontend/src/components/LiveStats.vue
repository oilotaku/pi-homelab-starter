<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { getConfig, getLiveStats } from "../api.js";

const cfg = getConfig();
const stats = ref(null);
const failed = ref(false);

async function refresh() {
  try {
    stats.value = await getLiveStats();
    failed.value = false;
  } catch {
    failed.value = true;
  }
}

function fmtUptime(s) {
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  return days > 0 ? `${days} 天 ${hours} 小時` : `${hours} 小時`;
}

let timer;
onMounted(() => {
  if (!cfg.backendPort) return;
  refresh();
  timer = setInterval(refresh, 3000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <div v-if="cfg.backendPort" class="group">
    <h2>即時系統資源</h2>
    <div v-if="failed" class="empty-hint card-surface">無法連線到 pi-dashboard-backend,略過即時資訊(仍可在「裝置健康」頁看每分鐘更新一次的資料)</div>
    <div v-else-if="stats" class="stat-grid card-surface">
      <div class="stat">
        <div class="label">CPU 使用率</div>
        <div class="value">{{ stats.cpu_percent.toFixed(1) }}%</div>
        <div class="subvalue">{{ stats.cpu_cores }} 核 · 負載 {{ stats.load_1.toFixed(2) }}</div>
      </div>
      <div class="stat">
        <div class="label">記憶體</div>
        <div class="value">{{ stats.mem_percent.toFixed(1) }}%</div>
        <div class="subvalue">{{ (stats.mem_used_mb / 1024).toFixed(1) }} / {{ (stats.mem_total_mb / 1024).toFixed(1) }} GB</div>
      </div>
      <div class="stat">
        <div class="label">Swap</div>
        <div class="value">{{ stats.swap_percent.toFixed(1) }}%</div>
        <div class="subvalue">{{ (stats.swap_used_mb / 1024).toFixed(1) }} / {{ (stats.swap_total_mb / 1024).toFixed(1) }} GB</div>
      </div>
      <div class="stat">
        <div class="label">開機時間</div>
        <div class="value" style="font-size:1rem;">{{ fmtUptime(stats.uptime_s) }}</div>
      </div>
    </div>
    <div v-else class="empty-hint card-surface">讀取中…</div>
  </div>
</template>
