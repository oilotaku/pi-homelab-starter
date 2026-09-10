<script setup>
import { getConfig } from "./api.js";

const cfg = getConfig();
const host = window.location.hostname || cfg.fallbackHost || "localhost";
</script>

<template>
  <div class="app">
    <nav class="sidebar">
      <div class="brand">🖥️ Jason-Pi</div>
      <router-link class="navlink" to="/">🏠 首頁</router-link>
      <router-link class="navlink" to="/health">💚 裝置健康</router-link>
      <router-link class="navlink" to="/devices">📶 區網裝置</router-link>
      <div class="navfoot">連線主機:{{ host }}</div>
    </nav>

    <main class="main">
      <router-view />
    </main>
  </div>
</template>
