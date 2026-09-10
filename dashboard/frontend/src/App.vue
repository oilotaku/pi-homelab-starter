<script setup>
import { computed, ref } from "vue";
import { getConfig } from "./api.js";
import { useToken } from "./useToken.js";

const cfg = getConfig();
const host = window.location.hostname || cfg.fallbackHost || "localhost";

const { token, unlock, lock } = useToken();
const editing = ref(false);
const input = ref("");

function startUnlock() {
  input.value = "";
  editing.value = true;
}
function confirmUnlock() {
  unlock(input.value);
  editing.value = false;
}
function cancelUnlock() {
  editing.value = false;
}

const hasToken = computed(() => !!token.value);
</script>

<template>
  <div class="app">
    <nav class="sidebar">
      <div class="brand">🖥️ Jason-Pi</div>
      <router-link class="navlink" to="/">🏠 首頁</router-link>
      <router-link class="navlink" to="/health">💚 裝置健康</router-link>
      <router-link class="navlink" to="/devices">📶 區網裝置</router-link>

      <div class="unlock" v-if="cfg.backendPort">
        <template v-if="editing">
          <input
            type="password"
            v-model="input"
            placeholder="輸入控制 token"
            style="width:100%;margin-bottom:6px;padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:0.78rem;"
            @keydown.enter="confirmUnlock"
            @keydown.esc="cancelUnlock"
          />
          <div style="display:flex;gap:6px;">
            <button @click="confirmUnlock" style="flex:1;">確認</button>
            <button @click="cancelUnlock" style="flex:1;">取消</button>
          </div>
        </template>
        <button v-else :class="{ unlocked: hasToken }" @click="hasToken ? lock() : startUnlock()">
          {{ hasToken ? "🔓 已解鎖控制功能(點擊鎖回)" : "🔒 解鎖容器/音量控制" }}
        </button>
      </div>

      <div class="navfoot">連線主機：{{ host }}</div>
    </nav>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>
