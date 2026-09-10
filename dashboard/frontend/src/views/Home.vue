<script setup>
import { getConfig } from "../api.js";
import HealthStrip from "../components/HealthStrip.vue";
import LiveStats from "../components/LiveStats.vue";
import VolumeControl from "../components/VolumeControl.vue";

const cfg = getConfig();
const host = window.location.hostname || cfg.fallbackHost || "localhost";

function serviceHref(svc) {
  return `http://${host}:${svc.port}${svc.path || ""}`;
}
</script>

<template>
  <div class="page-header">
    <h1>Jason-Pi 服務導覽</h1>
    <p class="subtitle">媒體伺服器與下載自動化控制台</p>
  </div>

  <div class="group">
    <HealthStrip />
  </div>

  <LiveStats />
  <VolumeControl />

  <div v-for="grp in cfg.serviceGroups || []" :key="grp.title" class="group">
    <h2>{{ grp.title }}</h2>
    <div class="grid">
      <a
        v-for="svc in grp.services"
        :key="svc.name"
        class="card card-surface"
        :href="serviceHref(svc)"
      >
        <span class="icon">{{ svc.icon }}</span>
        <span>
          <span class="name">{{ svc.name }}</span><br />
          <span class="desc">{{ svc.desc }}</span>
        </span>
      </a>
    </div>
  </div>
</template>
