import { createRouter, createWebHashHistory } from "vue-router";
import Home from "./views/Home.vue";
import Health from "./views/Health.vue";
import Devices from "./views/Devices.vue";

// hash 路由:nginx 只是單純 serve 靜態檔,沒有設定 SPA fallback rewrite,
// hash 模式讓 index.html?# 之後的路徑都不需要伺服器端支援也能重新整理不出錯。
export default createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: "/", name: "home", component: Home },
    { path: "/health", name: "health", component: Health },
    { path: "/devices", name: "devices", component: Devices },
  ],
});
