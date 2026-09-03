# Tailscale

封裝官方安裝腳本,依 `.env` 的設定跑 `tailscale up`。

## 安裝步驟

Tailscale 是「多裝置互連」的服務,只裝在這台 Pi 上還不夠用——至少要有第二台裝置(手機、筆電)也加入同一個帳號,才會真的形成一個可以互連的網路。

1. **如果還沒有 Tailscale 帳號**:到 [tailscale.com](https://tailscale.com/) 註冊,可以直接用 Google / GitHub / Microsoft 帳號登入,不需要另外設密碼。

2. **決定要不要用 authkey(決定 `.env` 怎麼填)**:
   - **留空 `TS_AUTHKEY`**(適合第一次設定):安裝時會印出一個登入網址,手動用瀏覽器開啟、登入 Tailscale 帳號完成連線。
   - **填 `TS_AUTHKEY`**(適合無頭安裝/自動化):免互動,但要先到 Tailscale 後台 Settings → Keys 產生一組 key,注意有效期限與是否為 reusable/ephemeral。建議優先用 one-time/ephemeral key,用完即失效,降低外洩風險。
   - 依需求決定要不要設 `TS_ADVERTISE_EXIT_NODE`(把這台機器當成其他裝置的出口節點,等於免費個人 VPN)、`TS_ADVERTISE_ROUTES`(把這台機器所在的實體 LAN 廣播給 tailnet 內其他裝置,填法例如 `192.168.1.0/24`;廣播後還要到 Tailscale 後台手動核准該路由才會生效)。

3. **在這台 Pi 上執行**:
   ```bash
   sudo ./tailscale/install.sh
   ```
   若 `TS_AUTHKEY` 留空,終端機會印出類似 `https://login.tailscale.com/a/xxxxxxxx` 的網址,複製到瀏覽器登入完成連線(可以用手機開,不用一定在電腦上)。

4. **確認這台 Pi 連線成功**:
   ```bash
   tailscale status
   ```
   應該會看到這台機器列在清單裡(狀態通常是 `idle` 或 `active`)。

5. **記下這台 Pi 的 Tailscale IP**,之後從其他裝置要連過來就是用這組 IP:
   ```bash
   tailscale ip -4
   ```

6. **在其他裝置(手機、筆電)也安裝 Tailscale**:手機到 App Store / Google Play 搜尋 Tailscale,電腦到 [tailscale.com/download](https://tailscale.com/download),用**同一個帳號**登入。同帳號底下的裝置會自動變成同一個 tailnet 的成員,彼此就能直接互連,不需要額外配對。

7. **從其他裝置測試連線**:例如在手機/筆電開終端機 `ping <步驟 5 的 IP>`,或直接用瀏覽器連這台 Pi 上跑的服務(例如 Pi-hole 後台 `http://<tailscale-ip>/admin`),也可以直接 `ssh <使用者>@<tailscale-ip>` 測試。連得上代表整個 tailnet 設定成功——之後在家外用手機連 Tailscale,就能像在家裡一樣存取這台 Pi 上的服務。

## 常見坑:CGNAT 網段常被誤判成「非區網」

Tailscale 的裝置 IP 落在 `100.64.0.0/10`(CGNAT 保留網段),**不算 RFC1918 私有位址**。很多自架服務(媒體伺服器、NAS 管理介面等)判斷「是不是區網連線」時只認 `192.168.0.0/16`、`10.0.0.0/8`、`172.16.0.0/12` 這幾個 RFC1918 範圍,導致明明是自己的 Tailscale 裝置連進來,卻被判定成「外部連線」而擋下或要求額外驗證。

如果某個自架服務有類似「允許區網跳過登入/允許區網直連」的設定,而透過 Tailscale 連線時卡住,通常代表要去該服務自己的「信任網段」設定裡,把 `100.64.0.0/10` 加進允許清單,而不是去改 Tailscale 本身的設定。

## 常見坑:DNS 相關的無害警告

在部分 Ubuntu 桌面環境(有 `systemd-resolved`)上,`tailscale status` 可能出現類似:

```
Tailscale failed to set the DNS configuration of your device: running /usr/sbin/resolvconf ...
```

若裝置本身 DNS 解析功能一切正常(能正常上網、能解析網域),這通常只是 `resolvconf` 相容層找不到介面的無害警告,不影響 Tailscale 連線本身。
