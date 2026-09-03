#!/usr/bin/env python3
"""定期產生主機硬體健康狀態(SMART 磁碟健康、Docker 容器狀態),
寫成 JSON 給 dashboard 裝置健康儀表板頁面抓取顯示。

SMART 讀取需要 root 權限,建議用 sudo 跑 cron,例如每 5 分鐘一次:
    */5 * * * * /usr/bin/sudo /usr/bin/python3 /path/to/scripts/generate_health.py >> /path/to/scripts/generate_health.log 2>&1

可用環境變數調整(不設就用預設值):
    DASHBOARD_HTML_DIR  dashboard/html 的路徑,預設是這支腳本所在 repo 裡的 dashboard/html
    SMART_DISKS         要檢查 SMART 健康的磁碟裝置,逗號分隔,例如 /dev/sda,/dev/sdb;
                         留空(預設)則跳過 SMART 這個區塊(適合完全沒有實體磁碟健康疑慮的環境,例如 VM)
"""
import json
import os
import subprocess
import time
from pathlib import Path

DEFAULT_HTML_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "html"
HTML_DIR = Path(os.environ.get("DASHBOARD_HTML_DIR") or DEFAULT_HTML_DIR)
OUT = HTML_DIR / "health.json"
DISKS = [d.strip() for d in os.environ.get("SMART_DISKS", "").split(",") if d.strip()]

# Load_Cycle_Count 這類 THRESH=0 的 old-age 屬性,VALUE 掉到個位數是設計壽命統計逼近的警訊,
# 但不是壞軌(仍要看 Reallocated/Pending/Offline_Uncorrectable),所以獨立標記為 attention 而非 fail。
ATTENTION_ATTRS = {"Load_Cycle_Count"}
FAIL_IF_NONZERO = {"Reallocated_Sector_Ct", "Current_Pending_Sector", "Offline_Uncorrectable"}


def read_smart(device):
    try:
        out = subprocess.run(
            ["smartctl", "-H", "-A", "-j", device],
            capture_output=True, text=True, timeout=15,
        )
        d = json.loads(out.stdout)
    except Exception as e:
        return {"device": device, "status": "unknown", "error": str(e)}

    passed = d.get("smart_status", {}).get("passed")
    attrs = {a["name"]: a for a in d.get("ata_smart_attributes", {}).get("table", [])}

    def raw_int(name):
        a = attrs.get(name)
        if not a:
            return None
        try:
            return int(a["raw"]["string"].split()[0])
        except (ValueError, KeyError, IndexError):
            return None

    status = "ok"
    notes = []
    if passed is False:
        status = "fail"
        notes.append("SMART overall-health 未通過")
    for name in FAIL_IF_NONZERO:
        v = raw_int(name)
        if v:
            status = "fail"
            notes.append(f"{name}={v}")
    if status != "fail":
        for name in ATTENTION_ATTRS:
            a = attrs.get(name)
            if a and a.get("value") is not None and a.get("thresh") is not None:
                if a["value"] <= a["thresh"] + 5:
                    status = "attention"
                    notes.append(f"{name} 已逼近設計壽命門檻(VALUE={a['value']}, THRESH={a['thresh']})")

    return {
        "device": device,
        "status": status,
        "passed": passed,
        "temp_c": d.get("temperature", {}).get("current"),
        "power_on_hours": d.get("power_on_time", {}).get("hours"),
        "power_cycle_count": d.get("power_cycle_count"),
        "reallocated_sectors": raw_int("Reallocated_Sector_Ct"),
        "pending_sectors": raw_int("Current_Pending_Sector"),
        "offline_uncorrectable": raw_int("Offline_Uncorrectable"),
        "load_cycle_count": raw_int("Load_Cycle_Count"),
        "notes": notes,
    }


def read_docker():
    try:
        out = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10, check=True,
        )
    except Exception as e:
        return {"error": str(e), "containers": []}

    containers = []
    for line in out.stdout.strip().splitlines():
        if not line:
            continue
        c = json.loads(line)
        status_text = c.get("Status", "")
        running = c.get("State") == "running"
        health = "unknown"
        if "(healthy)" in status_text:
            health = "healthy"
        elif "(unhealthy)" in status_text:
            health = "unhealthy"
        elif running:
            health = "running_no_healthcheck"
        containers.append({
            "name": c.get("Names"),
            "state": c.get("State"),
            "status": status_text,
            "health": health,
        })
    return {"containers": containers}


def main():
    smart = [read_smart(dev) for dev in DISKS]
    docker = read_docker()

    data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "smart": smart,
        "docker": docker,
    }

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    tmp = str(OUT) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT)


if __name__ == "__main__":
    main()
