# pi-homelab-starter

在 Raspberry Pi 5(Ubuntu 24.04)上跑的家用媒體/下載伺服器 Docker Compose 堆疊,搭配一個自製的靜態儀表板。這是**這台實際機器目前在跑的設定**,不是可攜式範本——路徑、掛載點、IP 都是寫死對應這台機器的環境,拿去別的機器用之前請先讀完下面的「這不是即插即用的東西」。

## 這個 repo 裡有什麼

`docker-compose.yml` 定義三個服務,共用同一個 bridge network:

| 服務 | 用途 | Port | 說明 |
|---|---|---|---|
| `qbittorrent` | BT 下載器(headless,linuxserver/qbittorrent image) | 8080 (WebUI)、6881 (peer) | 資料掛載在 `/media/jason/Mydisk` → 容器內 `/data` |
| `rss-manager` | 動漫 RSS 自動下載後端(自寫,FastAPI) | 5090 | 見下方「rss-manager」 |
| `dashboard` | 靜態導覽首頁 + 裝置健康儀表板(nginx:alpine 純靜態檔) | 8090 | 見下方「dashboard」 |

Jellyfin(影音串流)是另一組獨立的 compose,**不在這個 repo 裡**(路徑在機器上是 `~/jellyfin/docker-compose.yml`,用 host network 跑,原因是要直接吃 `/dev/dri`、`/dev/video*` 做硬體轉碼)。Pi-hole、SSH、Samba、UxPlay 也都是原生服務或獨立 compose,同樣不在這裡管理。

### dashboard(`dashboard/html/`)

純靜態檔案,由 nginx:alpine 唯讀掛載,沒有後端。三個頁面 + 排程腳本產生的 JSON/HTML 共用一套 design tokens(`common.css`),支援亮/暗色主題,側邊導覽在窄螢幕自動收成頂部列。

- **首頁**(`index.html`):服務連結卡片(Jellyfin/qBittorrent/Pi-hole)、新增追番的 RSS 表單、健康摘要條
- **裝置健康**(`health.html`):主機資源(CPU/記憶體/磁碟)、磁碟 SMART 健康(sda/sdb)、Docker 容器狀態、區網裝置在線摘要
- **區網裝置**(`devices.html`):Pi-hole DNS 查詢紀錄被動辨識出的區網裝置清單

`pi_status.json`、`health.json`、`devices.html`、`devices.json` 都是由機器上 crontab 排程的 Python 腳本(`~/scripts/generate_*.py`,不在這個 repo 裡,是機器本機的排程腳本)定期產生的靜態檔,前端用 `fetch()` 輪詢更新,**這些檔案本身不進版控**(見 `.gitignore`)。

### rss-manager(`rss-manager/`)

FastAPI 服務,把「輸入劇名關鍵字 → 建立 DMHY RSS feed → qBittorrent 分類 + 自動下載規則(篩繁體+內嵌字幕)→ 立刻抓一次現有符合文章」這個流程包成一支 API(`POST /api/create`),給 dashboard 首頁的輸入框呼叫。沒有自己的資料庫,所有狀態都活在 qBittorrent 裡。

```bash
cd rss-manager
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest   # 16 個測試,用 respx mock qBittorrent API,不打真實網路
```

## 這不是即插即用的東西

跟這個 repo 名稱可能給人的印象不同,這**不是**一鍵 `git clone` 就能跑的通用範本:

- `docker-compose.yml` 裡的路徑(`/home/jason/docker-stack/...`、`/media/jason/Mydisk`)是寫死的,對應這台機器實際的磁碟掛載
- qBittorrent 設定成「LAN + Tailscale CGNAT 網段免密碼」(`bypass_auth_subnet_whitelist`),這是**刻意**只給信任的家用網路用的取捨,不建議直接對外開放
- dashboard 的「新增追番」輸入框**沒有任何身分驗證**,能連到 8090 就能建規則,同樣是家用網路信任範圍內的設計,不是安全疏漏
- 帳號密碼一律不進版控(`qbittorrent/config/` 已在 `.gitignore`),要跑起來需要自己走一輪 qBittorrent WebUI 初次設定

如果你不是在跟這台 Pi 一樣的環境上跑,把這裡當「怎麼把幾個服務串起來」的參考,而不是照抄設定檔。

## 需求

- Docker Engine + Compose v2
- 一般使用者需要在 `docker` 群組裡才能免 sudo 操作
- dashboard 的裝置健康儀表板需要 `smartmontools`(讀 SMART)和 Pi-hole 的 FTL 資料庫(讀區網裝置),這兩個資料來源都是機器本機排程腳本產生,不含在這個 repo
