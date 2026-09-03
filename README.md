# pi-homelab-starter

兩個各自獨立的部分,合放在同一個 repo:

- **[一鍵安裝腳本](#一鍵安裝-pi-holesambatailscale)**:在任何 Raspberry Pi / Debian 系 Linux 上快速配置 Pi-hole、Samba、Tailscale 三個最常見的家用伺服器服務,可攜式、透過 `.env` 參數化,不綁特定機器
- **[dashboard](#dashboard-監控管理頁面)**:一台實際 Raspberry Pi 5 家用伺服器在跑的整合監控管理頁面(服務入口、主機資源、磁碟健康、Docker 容器、區網裝置狀態),綁定那台機器的實際環境,主要當作參考範本

兩者可以獨立使用,不必一起裝。

## 一鍵安裝 Pi-hole/Samba/Tailscale

- **[Pi-hole](pihole/)** — 網路廣告過濾 DNS(Docker)
- **[Samba](samba/)** — 檔案分享(原生安裝)
- **[Tailscale](tailscale/)** — 免公網 IP 也能安全連回家的 VPN mesh 網路(原生安裝)

每個服務都可以獨立使用,不強制一起裝。這部分整理自實際在一台 Raspberry Pi 5 上跑這三個服務踩過的坑,重點放在「怎麼設定」與「常見錯誤怎麼解」,而不是把某一台機器的設定原封不動搬過來。

### 需求

- Raspberry Pi OS / Ubuntu(或其他 Debian 系發行版),有 `sudo` 權限
- Pi-hole 需要 Docker + Docker Compose v2(沒裝可參考 [官方安裝腳本](https://get.docker.com))
- Samba / Tailscale 用原生安裝,只需要 `apt` 跟一般 shell 工具

### 快速開始

```bash
git clone https://github.com/oilotaku/pi-homelab-starter.git
cd pi-homelab-starter
cp .env.example .env
chmod 600 .env   # .env 含密碼/authkey,收緊權限避免同機其他使用者讀到
$EDITOR .env     # 至少改掉 PIHOLE_WEBPASSWORD、SMB_SHARE_PATH、SMB_USER
./setup.sh
```

`setup.sh` 是一個簡單選單,可以選擇只裝其中一個服務,或一次裝三個。也可以略過選單,直接執行個別服務底下的腳本(見各自的 README)。

### 安全性提醒

這些腳本設定出來的服務,預設是給**信任的家用區網**用的:

- Samba 分享有帳號密碼保護,但沒有額外的存取控制/稽核
- Pi-hole 管理介面只有一組密碼保護,沒有多因素驗證或存取白名單
- 若要透過 Tailscale 開放給家外裝置存取,等於把上述服務暴露給你自己的 Tailscale 網路成員——請自行評估風險,不要在沒有額外防護的情況下把這些服務對外公網開放(例如直接做 port forwarding)

### 致謝

這部分只是幫忙串起安裝流程,實際的服務都來自以下上游專案,設定/使用上的細節請以它們的官方文件為準:

- [Pi-hole](https://pi-hole.net/) — [pi-hole/pi-hole](https://github.com/pi-hole/pi-hole)、[pi-hole/docker-pi-hole](https://github.com/pi-hole/docker-pi-hole)
- [Samba](https://www.samba.org/)
- [Tailscale](https://tailscale.com/)

## dashboard(監控管理頁面)

`dashboard/` 是另一台實際在跑的 Raspberry Pi 5 家用伺服器上的**監控管理頁面**——服務入口、下載自動化操作、主機與裝置健康狀態,一站集中在這裡,不用個別登入各服務才能看狀態。純靜態檔案,由 `nginx:alpine` 唯讀掛載,沒有後端。

跟上面的安裝腳本不同,這部分**不是可攜式範本**——部分內容(RSS 表單呼叫的 API 位址、健康資料的來源)對應那台機器的環境,主要當作「怎麼做一個家用伺服器監控頁面」的參考,不是拿來直接跑的工具。

### 頁面

三個頁面共用一套 design tokens(`common.css`),支援亮/暗色主題,側邊導覽在窄螢幕自動收成頂部列,並顧了觸控熱區、輸入框 iOS 自動放大等手機瀏覽細節。

- **首頁**(`index.html`):服務連結卡片、新增追番的 RSS 表單、健康摘要條(點進去看裝置健康頁)
- **裝置健康**(`health.html`):主機資源(CPU/記憶體/磁碟)、磁碟 SMART 健康、Docker 容器狀態、區網裝置在線摘要
- **區網裝置**(`devices.html`):DNS 查詢紀錄被動辨識出的區網裝置清單

### 資料從哪來

頁面本身是純靜態檔,所有數值都是前端 JS 對同目錄下幾個 JSON 檔案 `fetch()` 輪詢:

| 檔案 | 內容 | 產生方式 |
|---|---|---|
| `pi_status.json` | CPU 溫度/負載、記憶體、磁碟、開機時間 | 排程腳本每分鐘寫入 |
| `health.json` | 磁碟 SMART 健康、Docker 容器狀態 | 排程腳本每 5 分鐘寫入(需要能讀 SMART 與 `docker ps`) |
| `devices.json` / `devices.html` | 區網裝置清單與在線狀態 | 排程腳本每 10 分鐘寫入(需要能讀 Pi-hole FTL 資料庫) |

這些產生用的腳本是機器本機的 cron job,**不在這個 repo 裡**——它們對應特定的硬體/服務(smartctl 讀哪顆碟、Pi-hole DB 路徑),搬到別的機器要自己重寫。這個 repo 只放前端會讀取、渲染這些 JSON 的部分。

### 限制

- 首頁「新增追番」表單背後打的 RSS 自動下載 API(`:5090`)是另一支自架服務,不在這個 repo 裡,拿掉這段或換成自己的後端才能用
- 服務連結卡片(Jellyfin/qBittorrent/Pi-hole)的連結是照那台機器實際跑的服務兜出來的,要換成自己的服務清單
- 沒有任何身分驗證——整個設計假設只有信任的家用網路(LAN + VPN)能連到這個頁面,不要對外公網開放
