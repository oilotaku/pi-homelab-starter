// Jason-Pi dashboard 後端:提供唯讀即時系統資訊,以及需要 token 驗證的
// Docker 容器控制 / 系統音量控制。設計成獨立的原生 systemd service(非
// Docker 容器),原因見 repo README——容器管理要碰 host 的 Docker socket、
// 音量控制要碰桌面 session 的 PipeWire,兩者放進容器裡都不乾淨。
"use strict";

const path = require("path");
require("dotenv").config({ path: path.join(__dirname, ".env") });

const express = require("express");
const cors = require("cors");
const crypto = require("crypto");
const os = require("os");
const { execFile } = require("child_process");
const Docker = require("dockerode");

const PORT = Number(process.env.PORT) || 8091;
// AUTH_PIN 取代舊的 AUTH_TOKEN——手機輸入一長串 hex token 太痛苦,改成短 PIN
// (建議 6 位數字)方便用手機數字鍵盤輸入。因為 PIN 的 keyspace 遠小於原本的
// 24-byte hex token,下面额外加了失敗鎖定機制擋暴力破解,不能只靠 PIN 本身長度。
const AUTH_PIN = process.env.AUTH_PIN || process.env.AUTH_TOKEN || "";
const ALLOWED_CONTAINERS = (process.env.ALLOWED_CONTAINERS || "")
  .split(",")
  .map((s) => s.trim())
  .filter(Boolean);
const CORS_ORIGIN = process.env.CORS_ORIGIN || "*";

if (!AUTH_PIN) {
  console.error("[FATAL] AUTH_PIN 未設定(見 .env.example),拒絕啟動 —— 這個服務有容器控制與系統音量控制權限,不能沒有驗證就上線。");
  process.exit(1);
}

// ---- 失敗鎖定:PIN 只有幾位數字,keyspace 小,一定要擋暴力猜測 ----
// 單一 process 記憶體狀態即可(這是單人家用工具,不需要跨機器/跨重啟持久化)。
const MAX_ATTEMPTS = 5;
const LOCKOUT_MS = 5 * 60 * 1000;
let failedAttempts = 0;
let lockedUntil = 0;

const docker = new Docker({ socketPath: "/var/run/docker.sock" });

const app = express();
app.use(cors({ origin: CORS_ORIGIN }));
app.use(express.json());

function timingSafeEqual(a, b) {
  const bufA = Buffer.from(String(a));
  const bufB = Buffer.from(String(b));
  if (bufA.length !== bufB.length) return false;
  return crypto.timingSafeEqual(bufA, bufB);
}

function requireAuth(req, res, next) {
  const now = Date.now();
  if (now < lockedUntil) {
    const retryAfterS = Math.ceil((lockedUntil - now) / 1000);
    res.set("Retry-After", String(retryAfterS));
    return res.status(429).json({ error: "too many failed attempts, locked out", retry_after_s: retryAfterS });
  }

  const header = req.get("authorization") || "";
  const pin = header.startsWith("Bearer ") ? header.slice(7) : "";
  if (!pin || !timingSafeEqual(pin, AUTH_PIN)) {
    failedAttempts += 1;
    if (failedAttempts >= MAX_ATTEMPTS) {
      lockedUntil = now + LOCKOUT_MS;
      failedAttempts = 0;
    }
    return res.status(401).json({ error: "unauthorized" });
  }

  failedAttempts = 0;
  next();
}

// ---- /api/stats: 即時 CPU/RAM/swap/loadavg,不需要 token(唯讀) ----

function readProcStatTotals() {
  const fs = require("fs");
  const line = fs.readFileSync("/proc/stat", "utf8").split("\n")[0];
  const parts = line.trim().split(/\s+/).slice(1).map(Number);
  const idle = parts[3] + (parts[4] || 0);
  const total = parts.reduce((a, b) => a + b, 0);
  return { idle, total };
}

function readMemInfo() {
  const fs = require("fs");
  const text = fs.readFileSync("/proc/meminfo", "utf8");
  const kv = {};
  for (const line of text.split("\n")) {
    const m = line.match(/^(\w+):\s+(\d+)/);
    if (m) kv[m[1]] = Number(m[2]); // kB
  }
  const totalKb = kv.MemTotal || 0;
  const availKb = kv.MemAvailable ?? kv.MemFree ?? 0;
  const usedKb = totalKb - availKb;
  const swapTotalKb = kv.SwapTotal || 0;
  const swapFreeKb = kv.SwapFree || 0;
  const swapUsedKb = swapTotalKb - swapFreeKb;
  return {
    mem_total_mb: Math.round(totalKb / 1024),
    mem_used_mb: Math.round(usedKb / 1024),
    mem_percent: totalKb ? Math.round((usedKb / totalKb) * 1000) / 10 : 0,
    swap_total_mb: Math.round(swapTotalKb / 1024),
    swap_used_mb: Math.round(swapUsedKb / 1024),
    swap_percent: swapTotalKb ? Math.round((swapUsedKb / swapTotalKb) * 1000) / 10 : 0,
  };
}

let lastCpuSample = readProcStatTotals();

app.get("/api/stats", (req, res) => {
  const now = readProcStatTotals();
  const idleDelta = now.idle - lastCpuSample.idle;
  const totalDelta = now.total - lastCpuSample.total;
  const cpuPercent = totalDelta > 0 ? Math.round((1 - idleDelta / totalDelta) * 1000) / 10 : 0;
  lastCpuSample = now;

  res.json({
    generated_at: new Date().toISOString(),
    cpu_percent: Math.max(0, Math.min(100, cpuPercent)),
    cpu_cores: os.cpus().length,
    load_1: os.loadavg()[0],
    load_5: os.loadavg()[1],
    load_15: os.loadavg()[2],
    uptime_s: os.uptime(),
    ...readMemInfo(),
  });
});

// ---- /api/containers: 唯讀列表不需要 token,啟停/重啟需要 ----

async function listContainers() {
  const containers = await docker.listContainers({ all: true });
  return containers
    .map((c) => ({
      id: c.Id.slice(0, 12),
      name: (c.Names[0] || "").replace(/^\//, ""),
      image: c.Image,
      state: c.State, // running / exited / ...
      status: c.Status,
    }))
    .filter((c) => !ALLOWED_CONTAINERS.length || ALLOWED_CONTAINERS.includes(c.name))
    .sort((a, b) => a.name.localeCompare(b.name));
}

app.get("/api/containers", async (req, res) => {
  try {
    res.json({ generated_at: new Date().toISOString(), containers: await listContainers() });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

const CONTAINER_ACTIONS = new Set(["start", "stop", "restart"]);

app.post("/api/containers/:name/:action", requireAuth, async (req, res) => {
  const { name, action } = req.params;
  if (!CONTAINER_ACTIONS.has(action)) {
    return res.status(400).json({ error: "unknown action" });
  }
  if (ALLOWED_CONTAINERS.length && !ALLOWED_CONTAINERS.includes(name)) {
    return res.status(403).json({ error: "container not in allowlist" });
  }
  try {
    const container = docker.getContainer(name);
    await container[action]();
    res.json({ ok: true, name, action });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

// ---- /api/volume: 系統預設音訊輸出(wpctl),讀取不需要 token,調整需要 ----

const WPCTL_ENV = {
  ...process.env,
  XDG_RUNTIME_DIR: process.env.XDG_RUNTIME_DIR || `/run/user/${process.getuid()}`,
  DBUS_SESSION_BUS_ADDRESS:
    process.env.DBUS_SESSION_BUS_ADDRESS || `unix:path=/run/user/${process.getuid()}/bus`,
};

function runWpctl(args) {
  return new Promise((resolve, reject) => {
    execFile("wpctl", args, { env: WPCTL_ENV, timeout: 5000 }, (err, stdout, stderr) => {
      if (err) return reject(new Error(stderr || err.message));
      resolve(stdout);
    });
  });
}

app.get("/api/volume", async (req, res) => {
  try {
    const out = await runWpctl(["get-volume", "@DEFAULT_AUDIO_SINK@"]);
    // 格式範例: "Volume: 0.45" 或 "Volume: 0.45 [MUTED]"
    const m = out.match(/Volume:\s*([\d.]+)/);
    const volume = m ? Number(m[1]) : null;
    const muted = /MUTED/.test(out);
    res.json({ volume, muted });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.post("/api/volume", requireAuth, async (req, res) => {
  const { value, mute } = req.body || {};
  try {
    if (typeof value === "number") {
      const clamped = Math.max(0, Math.min(1, value));
      await runWpctl(["set-volume", "@DEFAULT_AUDIO_SINK@", String(clamped)]);
    }
    if (typeof mute === "boolean") {
      await runWpctl(["set-mute", "@DEFAULT_AUDIO_SINK@", mute ? "1" : "0"]);
    }
    const out = await runWpctl(["get-volume", "@DEFAULT_AUDIO_SINK@"]);
    const m = out.match(/Volume:\s*([\d.]+)/);
    res.json({ volume: m ? Number(m[1]) : null, muted: /MUTED/.test(out) });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
});

app.listen(PORT, () => {
  console.log(`pi-dashboard-backend listening on :${PORT}`);
});
