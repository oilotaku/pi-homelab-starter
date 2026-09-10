<script setup>
import { computed, ref } from "vue";
import { getConfig } from "../api.js";
import { useToken } from "../useToken.js";

const cfg = getConfig();
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
  <div v-if="cfg.backendPort" class="group">
    <div class="token-card card-surface">
      <template v-if="editing">
        <input
          class="pin-input"
          type="tel"
          inputmode="numeric"
          pattern="[0-9]*"
          maxlength="6"
          v-model="input"
          placeholder="PIN"
          autofocus
          @keydown.enter="confirmUnlock"
          @keydown.esc="cancelUnlock"
        />
        <button @click="confirmUnlock">確認</button>
        <button @click="cancelUnlock">取消</button>
      </template>
      <template v-else>
        <span class="token-status">{{ hasToken ? "🔓 已解鎖容器/音量控制" : "🔒 容器/音量控制目前鎖定" }}</span>
        <button @click="hasToken ? lock() : startUnlock()">{{ hasToken ? "鎖回" : "輸入 PIN 解鎖" }}</button>
      </template>
    </div>
  </div>
</template>
