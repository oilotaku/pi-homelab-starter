#!/usr/bin/env python3
"""定期產生 Raspberry Pi 主機狀態(CPU 溫度/負載、記憶體、磁碟、開機時間),
寫成 JSON 給 dashboard 首頁的前端 JS 抓取顯示。

不需要 sudo:CPU 溫度、/proc、df 都是一般使用者可讀。建議用 cron 排程,例如每分鐘一次:
    */1 * * * * /usr/bin/python3 /path/to/scripts/generate_pi_status.py >> /path/to/scripts/generate_pi_status.log 2>&1

可用環境變數調整(不設就用預設值):
    DASHBOARD_HTML_DIR  dashboard/html 的路徑,預設是這支腳本所在 repo 裡的 dashboard/html
    MEDIA_DISK_PATH     額外要顯示用量的資料碟掛載點,例如 /media/mydisk;留空(預設)則不顯示這個區塊
"""
import json
import os
import subprocess
import time
from pathlib import Path

DEFAULT_HTML_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "html"
HTML_DIR = Path(os.environ.get("DASHBOARD_HTML_DIR") or DEFAULT_HTML_DIR)
OUT = HTML_DIR / "pi_status.json"
MEDIA_DISK_PATH = os.environ.get("MEDIA_DISK_PATH", "").strip()


def read_cpu_temp():
    try:
        out = subprocess.run(["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=5)
        # 格式: temp=52.1'C
        return float(out.stdout.strip().split("=")[1].split("'")[0])
    except (FileNotFoundError, IndexError, ValueError):
        # 非 Raspberry Pi(沒有 vcgencmd)時退回一般 Linux 的 thermal zone
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            return round(int(f.read().strip()) / 1000, 1)


def read_loadavg():
    with open("/proc/loadavg") as f:
        parts = f.read().split()
    return float(parts[0]), float(parts[1]), float(parts[2])


def read_mem():
    info = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, val = line.split(":", 1)
            info[key] = int(val.strip().split()[0])  # kB
    total_kb = info["MemTotal"]
    avail_kb = info["MemAvailable"]
    used_kb = total_kb - avail_kb
    return used_kb / 1024 / 1024, total_kb / 1024 / 1024, round(used_kb / total_kb * 100, 1)


def read_disk(path):
    st = os.statvfs(path)
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    used = total - free
    gb = 1024 ** 3
    percent = round(used / total * 100, 1)
    return round(used / gb, 1), round(total / gb, 1), percent


def read_uptime():
    with open("/proc/uptime") as f:
        seconds = float(f.read().split()[0])
    days, rem = divmod(int(seconds), 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days:
        return f"{days} 天 {hours} 小時"
    if hours:
        return f"{hours} 小時 {minutes} 分鐘"
    return f"{minutes} 分鐘"


def main():
    cpu_temp = read_cpu_temp()
    load1, load5, load15 = read_loadavg()
    mem_used, mem_total, mem_percent = read_mem()
    sys_used, sys_total, sys_percent = read_disk("/")

    data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cpu_temp_c": cpu_temp,
        "cpu_cores": os.cpu_count(),
        "load_1": load1,
        "load_5": load5,
        "load_15": load15,
        "mem_used_gb": round(mem_used, 1),
        "mem_total_gb": round(mem_total, 1),
        "mem_percent": mem_percent,
        "disk_system_used_gb": sys_used,
        "disk_system_total_gb": sys_total,
        "disk_system_percent": sys_percent,
        "uptime": read_uptime(),
    }

    if MEDIA_DISK_PATH:
        media_used, media_total, media_percent = read_disk(MEDIA_DISK_PATH)
        data["disk_media_used_gb"] = media_used
        data["disk_media_total_gb"] = media_total
        data["disk_media_percent"] = media_percent

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(OUT) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT)


if __name__ == "__main__":
    main()
