<script setup>
import { onMounted, onUnmounted, ref } from "vue";
import { getPiStatus, getHealth, getDevices } from "../api.js";

const temp = ref("-");
const smart = ref({ status: "unknown", label: "讀取中" });
const dockerBadge = ref({ status: "unknown", label: "讀取中" });
const lan = ref("-");

const SMART_LABEL = { ok: "正常", attention: "需留意", fail: "異常", unknown: "未知" };
const RANK = { ok: 0, attention: 1, unknown: 1, fail: 2 };

async function refresh() {
  try {
    const d = await getPiStatus();
    temp.value = d.cpu_temp_c.toFixed(1) + " °C";
  } catch {
    temp.value = "讀取失敗";
  }

  try {
    const d = await getHealth();
    const worst = d.smart.reduce((acc, s) => (RANK[s.status] > RANK[acc] ? s.status : acc), "ok");
    smart.value = { status: worst, label: SMART_LABEL[worst] };

    const containers = (d.docker && d.docker.containers) || [];
    const unhealthy = containers.filter((c) => c.state !== "running" || c.health === "unhealthy");
    dockerBadge.value = unhealthy.length
      ? { status: "fail", label: unhealthy.length + " 個異常" }
      : { status: "ok", label: containers.length + " 個正常" };
  } catch {
    smart.value = { status: "unknown", label: "讀取失敗" };
    dockerBadge.value = { status: "unknown", label: "讀取失敗" };
  }

  try {
    const d = await getDevices();
    lan.value = `${d.online_count} / ${d.total_count} 在線`;
  } catch {
    lan.value = "讀取失敗";
  }
}

let timer;
onMounted(() => {
  refresh();
  timer = setInterval(refresh, 30000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <router-link to="/health" class="health-strip card-surface">
    <div class="hs-item">
      <span class="hs-label">主機溫度</span>
      <span class="hs-value">{{ temp }}</span>
    </div>
    <div class="hs-item">
      <span class="hs-label">磁碟健康</span>
      <span class="badge" :class="smart.status">{{ smart.label }}</span>
    </div>
    <div class="hs-item">
      <span class="hs-label">Docker 容器</span>
      <span class="badge" :class="dockerBadge.status">{{ dockerBadge.label }}</span>
    </div>
    <div class="hs-item">
      <span class="hs-label">區網裝置</span>
      <span class="hs-value">{{ lan }}</span>
    </div>
    <span class="hs-more">查看詳情 →</span>
  </router-link>
</template>
