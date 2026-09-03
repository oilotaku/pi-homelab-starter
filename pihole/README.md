# Pi-hole

用官方 `pihole/pihole` Docker image,設定值來自專案根目錄的 `.env`(`PIHOLE_WEBPASSWORD`、`PIHOLE_DNS_UPSTREAM`、`TZ`)。

## 安裝步驟

1. **確認有 Docker + Docker Compose v2**:
   ```bash
   docker compose version
   ```
   沒有的話用官方安裝腳本:`curl -fsSL https://get.docker.com | sh`

2. **設定 `.env`**(還沒做過的話,在 repo 根目錄):
   ```bash
   cp .env.example .env
   chmod 600 .env
   $EDITOR .env   # 至少把 PIHOLE_WEBPASSWORD 改成一組強密碼
   ```

3. **先檢查 53 埠有沒有被佔用**(常見到值得先做這步,不然容器直接啟動失敗):
   ```bash
   sudo ss -tulpn | grep ':53 '
   ```
   若有東西佔用(通常是 `systemd-resolved`),先處理完再繼續,做法見下面「常見坑:53 埠被 systemd-resolved 佔用」。

4. **啟動容器**(在 repo 根目錄執行,不是 `pihole/` 內):
   ```bash
   docker compose -f pihole/docker-compose.yml --env-file .env up -d
   ```
   **注意**:不要單純 `cd pihole && docker compose up -d`——Docker Compose 預設只會在「執行指令當下的目錄」找 `.env`,不會自動往上層目錄找,這樣會靜默套用 compose 檔裡寫死的預設值(不會報錯,只是密碼/時區都不是你 `.env` 裡設的值),務必用上面帶 `--env-file` 的寫法。`./setup.sh` 已經處理好這件事。

5. **確認容器真的跑起來了**:
   ```bash
   docker compose -f pihole/docker-compose.yml ps
   docker compose -f pihole/docker-compose.yml logs -f pihole   # Ctrl+C 離開
   ```

6. **登入管理介面確認**:瀏覽器開 `http://<pi-ip>/admin`,密碼是 `.env` 裡的 `PIHOLE_WEBPASSWORD`。

7. **關鍵的最後一步:讓區網裝置真的去問這台 Pi-hole 要 DNS**——前面幾步只是把 Pi-hole 跑起來,裝置預設還是問原本的 DNS(通常是路由器或 ISP),不會自動經過 Pi-hole。兩種做法擇一:
   - **改路由器的 DHCP 設定**(推薦,一次設定全家裝置都套用):登入路由器管理介面,找 DHCP / LAN 設定裡的 DNS Server 欄位,改成這台 Pi 的區網 IP(`hostname -I` 查)。改完裝置通常要重新連一次 Wi-Fi 或重開機才會拿到新的 DNS 設定。
   - **只在單一裝置測試**:該裝置的網路設定裡手動把 DNS Server 指到 Pi 的區網 IP,不動路由器。適合先測試效果,或不想/不能動路由器設定的情況。

8. **驗證真的生效**:
   ```bash
   dig doubleclick.net @<pi-ip>
   ```
   如果看到回應是 `0.0.0.0` 或 `NXDOMAIN`(而不是正常的廣告網域 IP),代表有擋到。也可以直接用瀏覽器上網,回到管理介面的 Query Log 看有沒有即時查詢記錄。

## 常見坑:53 埠被 systemd-resolved 佔用

大多數 Ubuntu / Raspberry Pi OS 預設會跑 `systemd-resolved`,它會佔用 DNS 相關的埠或介面,導致 Pi-hole 容器啟不起來(`bind: address already in use`)。

檢查是否衝突:

```bash
sudo ss -tulpn | grep ':53 '
```

若確認是 `systemd-resolved` 佔用,標準解法(擇一):

1. **關掉 stub listener**(推薦,對其他服務影響最小):
   編輯 `/etc/systemd/resolved.conf`,在 `[Resolve]` 下加 `DNSStubListener=no`,然後:
   ```bash
   sudo systemctl restart systemd-resolved
   sudo rm /etc/resolv.conf
   sudo ln -s /run/systemd/resolve/resolv.conf /etc/resolv.conf
   ```
2. 若機器上其他服務有特別理由需要 `systemd-resolved` 繼續佔用 53 埠,也可以改把 Pi-hole 容器的 DNS 埠對外改成別的(例如 `5353:53`),但這樣區網內其他裝置就不能直接把 Pi-hole 設成 DNS(因為標準 DNS 用戶端只會打 53 埠),不建議作為長期方案。

## 之後要接 Tailscale?

若想讓透過 Tailscale 連回家的裝置也走這台 Pi-hole 過濾廣告,通常做法是把 Tailscale 的 DNS 設定指到這台機器的 Tailscale IP(`tailscale ip`),而不是修改 Pi-hole 本身設定。細節請參考 Tailscale 官方文件的 "Use Tailscale as your DNS server" / MagicDNS 章節。
