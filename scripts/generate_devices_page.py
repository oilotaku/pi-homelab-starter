#!/usr/bin/env python3
"""定期產生區網裝置清單頁面,寫到 dashboard 的靜態目錄。
資料來源: Pi-hole FTL DB (被動 DNS 查詢紀錄,非主動掃描)。

需要 sudo 執行(讀取 pihole-FTL.db 需要 pihole 群組權限)。建議用 cron 排程,例如每 10 分鐘一次:
    */10 * * * * /usr/bin/sudo /usr/bin/python3 /path/to/scripts/generate_devices_page.py >> /path/to/scripts/generate_devices_page.log 2>&1

可用環境變數調整(不設就用預設值):
    DASHBOARD_HTML_DIR  dashboard/html 的路徑,預設是這支腳本所在 repo 裡的 dashboard/html
    PIHOLE_DB           Pi-hole FTL 資料庫路徑,預設 /etc/pihole/pihole-FTL.db(官方預設安裝路徑)
    LAN_PREFIX          只列出這個前綴開頭的 IP,例如 192.168.1.;留空(預設)則列出 Pi-hole 看過的所有裝置
    THIS_HOST_IP        要從清單排除的本機 IP(通常是這台跑 Pi-hole 的機器自己);
                         留空(預設)則自動偵測連到外網時使用的本機 IP,偵測失敗就不排除任何裝置
"""
import sqlite3
import socket
import time
import html
import json
import os
import subprocess
from pathlib import Path

DEFAULT_HTML_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "html"
HTML_DIR = Path(os.environ.get("DASHBOARD_HTML_DIR") or DEFAULT_HTML_DIR)
OUT = HTML_DIR / "devices.html"
OUT_JSON = HTML_DIR / "devices.json"
DB = os.environ.get("PIHOLE_DB") or "/etc/pihole/pihole-FTL.db"
LAN_PREFIX = os.environ.get("LAN_PREFIX", "")


def detect_this_host_ip():
    override = os.environ.get("THIS_HOST_IP", "").strip()
    if override:
        return override
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return ""


THIS_HOST_IP = detect_this_host_ip()

SIGNATURES = [
    ("iOS / macOS (Apple)", ["apple.com", "aaplimg.com", "apple-dns.net", "icloud.com", "push.apple.com", "mzstatic.com"]),
    ("Android / Google", ["googleapis.com", "gstatic.com", "google.com", "android.com", "gvt1.com", "googleusercontent.com"]),
    ("Windows", ["windowsupdate.com", "microsoft.com", "msftconnecttest.com", "windows.com", "live.com"]),
    ("Amazon 裝置", ["amazonaws.com", "amazon.com", "media-amazon.com"]),
    ("TP-Link IoT (Tapo/Kasa)", ["tplinkcloud.com", "tplinknbu.com", "tp-link.com"]),
    ("Samsung", ["samsungapps.com", "samsungosp.com", "samsung.com"]),
    ("Xiaomi", ["xiaomi.com", "mi.com", "miui.com"]),
    ("Roku", ["roku.com"]),
    ("Sonos", ["sonos.com"]),
    ("Nintendo", ["nintendo.net", "nintendo.com"]),
    ("Ubuntu/Linux", ["ubuntu.com", "canonical.com", "snapcraft.io"]),
]


def guess_system(domains_text):
    for label, keywords in SIGNATURES:
        if any(kw in domains_text for kw in keywords):
            return label
    return "未知"


def ping_all(ips):
    """平行 ping 一輪,回傳 {ip: True/False}。比只看 DNS 紀錄準,因為有些裝置(如 IoT 攝影機)查詢間隔可能長達數十分鐘。"""
    procs = {
        ip: subprocess.Popen(
            ["ping", "-c", "1", "-W", "1", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for ip in ips
    }
    return {ip: (p.wait() == 0) for ip, p in procs.items()}


def main():
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute(
        """
        SELECT na.ip, n.macVendor, n.hwaddr
        FROM network_addresses na
        JOIN network n ON na.network_id = n.id
        WHERE na.ip LIKE ?
        ORDER BY na.ip
        """,
        (LAN_PREFIX + "%",),
    )
    devices = cur.fetchall()

    ips_to_ping = [d["ip"] for d in devices if d["ip"] != THIS_HOST_IP]
    online_map = ping_all(ips_to_ping)

    rows = []
    for d in devices:
        ip = d["ip"]
        if ip == THIS_HOST_IP:
            continue
        vendor = d["macVendor"] or "-"
        hwaddr = d["hwaddr"] or "-"
        online = online_map.get(ip, False)

        cur.execute(
            """
            SELECT domain, MAX(timestamp) as ts
            FROM queries
            WHERE client = ?
            GROUP BY domain
            ORDER BY ts DESC
            LIMIT 200
            """,
            (ip,),
        )
        qrows = cur.fetchall()
        if not qrows:
            last_seen = "無查詢紀錄"
            guess = "-"
            last_ts = 0
        else:
            last_ts = max(r["ts"] for r in qrows)
            last_seen = time.strftime("%m-%d %H:%M", time.localtime(last_ts))
            domains_text = " ".join(r["domain"] for r in qrows)
            guess = guess_system(domains_text)

        rows.append((ip, vendor, hwaddr, last_seen, guess, last_ts, online))

    conn.close()

    rows.sort(key=lambda r: r[5], reverse=True)
    rows.sort(key=lambda r: r[6], reverse=True)

    generated_at = time.strftime("%Y-%m-%d %H:%M:%S")

    trs = []
    for ip, vendor, hwaddr, last_seen, guess, _, online in rows:
        status_html = (
            "<span class='dot on'></span>在線" if online
            else "<span class='dot off'></span>離線"
        )
        trs.append(
            f"<tr><td>{status_html}</td><td>{html.escape(ip)}</td><td>{html.escape(vendor)}</td>"
            f"<td class='mono'>{html.escape(hwaddr)}</td><td>{html.escape(last_seen)}</td>"
            f"<td>{html.escape(guess)}</td></tr>"
        )

    page = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>區網裝置清單</title>
<link rel="stylesheet" href="common.css">
<link rel="stylesheet" href="devices.css">
</head>
<body>
  <div class="app">
    <nav class="sidebar">
      <div class="brand">🖥️ Jason-Pi</div>
      <a class="navlink" href="index.html">🏠 首頁</a>
      <a class="navlink" href="health.html">💚 裝置健康</a>
      <a class="navlink active" href="devices.html">📶 區網裝置</a>
      <div class="navfoot">產生於 {generated_at}</div>
    </nav>

    <main class="main">
      <div class="page-header">
        <h1>區網裝置清單</h1>
        <p class="subtitle">資料來源: Pi-hole DNS 查詢紀錄(被動辨識,非主動掃描) &middot; 產生時間: {generated_at}</p>
      </div>
      <div class="group">
        <div class="table-wrap card-surface">
          <table>
            <thead><tr><th>狀態</th><th>IP</th><th>廠商</th><th>MAC</th><th>最後查詢</th><th>推測系統</th></tr></thead>
            <tbody>
              {''.join(trs) if trs else '<tr><td colspan="6">目前無資料</td></tr>'}
            </tbody>
          </table>
        </div>
        <div class="note">
          「狀態」是產生頁面當下對每台裝置做一次 ping 的即時結果(非累積紀錄),裝置有防火牆擋 ICMP 時可能誤判離線。推測系統僅依 DNS 查詢網域特徵判斷,非精確指紋辨識(例如查過 Google 服務網域不代表一定是 Android 裝置,iOS App 也常用 Google 的 Firebase/分析服務)。此頁面每 10 分鐘由排程腳本重新產生一次。
        </div>
      </div>
    </main>
  </div>
</body>
</html>
"""

    HTML_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page)

    devices_json = [
        {
            "ip": ip,
            "vendor": vendor,
            "hwaddr": hwaddr,
            "last_seen": last_seen,
            "guess": guess,
            "online": online,
        }
        for ip, vendor, hwaddr, last_seen, guess, _, online in rows
    ]
    payload = {
        "generated_at": generated_at,
        "online_count": sum(1 for d in devices_json if d["online"]),
        "total_count": len(devices_json),
        "devices": devices_json,
    }
    tmp = str(OUT_JSON) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    os.replace(tmp, OUT_JSON)


if __name__ == "__main__":
    main()
