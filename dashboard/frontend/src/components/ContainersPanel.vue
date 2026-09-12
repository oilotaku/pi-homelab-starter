<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { getConfig, getContainers, containerAction } from "../api.js";
import { useToken } from "../useToken.js";

const cfg = getConfig();
const { token } = useToken();
const hasToken = computed(() => !!token.value);

const containers = ref([]);
const failed = ref(false);
const pending = ref({}); // name -> action in flight
const errorMsg = ref("");

async function refresh() {
  try {
    const d = await getContainers();
    containers.value = d.containers;
    failed.value = false;
  } catch {
    failed.value = true;
  }
}

async function act(name, action) {
  errorMsg.value = "";
  pending.value = { ...pending.value, [name]: action };
  try {
    await containerAction(name, action);
    await refresh();
  } catch (e) {
    errorMsg.value = `${name} ${action} 失敗: ${e.message}`;
  } finally {
    const next = { ...pending.value };
    delete next[name];
    pending.value = next;
  }
}

const STATE_LABEL = { running: "運作中", exited: "已停止", restarting: "重啟中", paused: "已暫停" };

// 後端回傳 controllable=false 代表不在 ALLOWED_CONTAINERS 白名單,只列出、不給操作。
// 舊版後端沒有這個欄位(undefined)視為可操作,向下相容。
function canAct(c) {
  return hasToken.value && c.controllable !== false && !pending.value[c.name];
}

let timer;
onMounted(() => {
  if (!cfg.backendPort) return;
  refresh();
  timer = setInterval(refresh, 15000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <div v-if="cfg.backendPort" class="group">
    <h2>Docker 容器控制</h2>
    <div v-if="failed" class="empty-hint card-surface">無法連線到 pi-dashboard-backend</div>
    <div v-else class="docker-list card-surface">
      <div v-if="!containers.length" class="docker-row">讀取中…</div>
      <div v-for="c in containers" :key="c.id" class="docker-row">
        <span class="name">{{ c.name }}</span>
        <span class="status-text">{{ c.status }}</span>
        <span class="badge" :class="c.state === 'running' ? 'ok' : 'fail'">
          {{ STATE_LABEL[c.state] || c.state }}
        </span>
        <div v-if="c.controllable === false" class="docker-actions">
          <span class="status-text" title="不在後端 ALLOWED_CONTAINERS 白名單,僅顯示狀態">僅顯示</span>
        </div>
        <div v-else class="docker-actions">
          <button :disabled="!canAct(c)" @click="act(c.name, 'start')" title="啟動">▶ 啟動</button>
          <button :disabled="!canAct(c)" @click="act(c.name, 'restart')" title="重啟">⟳ 重啟</button>
          <button :disabled="!canAct(c)" @click="act(c.name, 'stop')" title="停止">■ 停止</button>
        </div>
      </div>
    </div>
    <div v-if="!hasToken" class="note">需要在上面輸入 PIN 解鎖才能操作按鈕(唯讀列表不需要)。</div>
    <div v-if="errorMsg" class="note" style="color:var(--fail);">{{ errorMsg }}</div>
  </div>
</template>
