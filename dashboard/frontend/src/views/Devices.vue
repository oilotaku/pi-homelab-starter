<script setup>
import { onMounted, ref } from "vue";
import { getDevices } from "../api.js";

const generatedAt = ref("");
const rows = ref([]);
const failed = ref(false);

async function refresh() {
  try {
    const d = await getDevices();
    generatedAt.value = d.generated_at;
    rows.value = d.devices;
    failed.value = false;
  } catch {
    failed.value = true;
  }
}

onMounted(refresh);
</script>

<template>
  <div class="page-header">
    <h1>區網裝置清單</h1>
    <p class="subtitle">資料來源: Pi-hole DNS 查詢紀錄(被動辨識,非主動掃描) · 產生時間: {{ generatedAt }}</p>
  </div>
  <div class="group">
    <div v-if="failed" class="empty-hint card-surface">讀取失敗</div>
    <div v-else class="table-wrap card-surface">
      <table>
        <thead>
          <tr><th>狀態</th><th>IP</th><th>廠商</th><th>MAC</th><th>最後查詢</th><th>推測系統</th></tr>
        </thead>
        <tbody>
          <tr v-if="!rows.length"><td colspan="6">目前無資料</td></tr>
          <tr v-for="d in rows" :key="d.ip">
            <td><span class="dot" :class="d.online ? 'on' : 'off'"></span>{{ d.online ? "在線" : "離線" }}</td>
            <td>{{ d.ip }}</td>
            <td>{{ d.vendor }}</td>
            <td class="mono">{{ d.hwaddr }}</td>
            <td>{{ d.last_seen }}</td>
            <td>{{ d.guess }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="note">
      「狀態」是產生頁面當下對每台裝置做一次 ping 的即時結果(非累積紀錄),裝置有防火牆擋 ICMP 時可能誤判離線。推測系統僅依 DNS 查詢網域特徵判斷,非精確指紋辨識(例如查過 Google 服務網域不代表一定是 Android 裝置,iOS App 也常用 Google 的 Firebase/分析服務)。此頁面資料每 10 分鐘由排程腳本重新產生一次。
    </div>
  </div>
</template>
