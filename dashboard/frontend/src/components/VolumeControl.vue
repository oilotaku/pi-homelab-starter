<script setup>
import { computed, onMounted, ref } from "vue";
import { getConfig, getVolume, setVolume } from "../api.js";
import { useToken } from "../useToken.js";

const cfg = getConfig();
const { token } = useToken();
const hasToken = computed(() => !!token.value);

const volume = ref(0); // 0-100 for the slider
const muted = ref(false);
const loaded = ref(false);
const failed = ref(false);
const errorMsg = ref("");
let debounceTimer;

async function refresh() {
  try {
    const d = await getVolume();
    volume.value = Math.round((d.volume ?? 0) * 100);
    muted.value = d.muted;
    loaded.value = true;
    failed.value = false;
  } catch {
    failed.value = true;
  }
}

function onSlide(e) {
  volume.value = Number(e.target.value);
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(commitVolume, 250);
}

async function commitVolume() {
  errorMsg.value = "";
  try {
    const d = await setVolume({ value: volume.value / 100 });
    volume.value = Math.round((d.volume ?? volume.value / 100) * 100);
    muted.value = d.muted;
  } catch (e) {
    errorMsg.value = "調整失敗: " + e.message;
  }
}

async function toggleMute() {
  errorMsg.value = "";
  try {
    const d = await setVolume({ mute: !muted.value });
    muted.value = d.muted;
  } catch (e) {
    errorMsg.value = "調整失敗: " + e.message;
  }
}

onMounted(() => {
  if (cfg.backendPort) refresh();
});
</script>

<template>
  <div v-if="cfg.backendPort" class="group">
    <h2>系統音量</h2>
    <div v-if="failed" class="empty-hint card-surface">無法連線到 pi-dashboard-backend</div>
    <div v-else-if="!loaded" class="empty-hint card-surface">讀取中…</div>
    <div v-else class="volume-card card-surface">
      <button class="mute-btn" :class="{ muted }" :disabled="!hasToken" @click="toggleMute">
        {{ muted ? "🔇" : "🔊" }}
      </button>
      <input type="range" min="0" max="100" :value="volume" :disabled="!hasToken" @input="onSlide" />
      <span class="vol-value">{{ volume }}%</span>
    </div>
    <div v-if="!hasToken" class="note">需要在左側「解鎖容器/音量控制」輸入 token 才能調整(這會改動系統預設音訊輸出音量,影響本機所有播放音量)。</div>
    <div v-if="errorMsg" class="note" style="color:var(--fail);">{{ errorMsg }}</div>
  </div>
</template>
