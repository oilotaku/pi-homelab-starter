# Samba

原生安裝(不 Docker 化)。檔案分享要直接碰觸 host 檔案系統,原生跑最單純,也不用處理容器內外的權限對應問題。

## 掛載外接硬碟(如果 `SMB_SHARE_PATH` 要指到外接硬碟)

如果只是分享 Pi 本機的資料夾,可以跳過這一段。如果是要分享外接 USB 硬碟,得先把硬碟掛載起來,而且要設定成**開機自動掛載**,不然重開機後掛載點是空的,`install.sh` 建立的分享路徑也會跟著變成一個空資料夾。

1. **插上硬碟後,先找出裝置代號**:
   ```bash
   lsblk
   ```
   從輸出找到你的硬碟(用容量大小判斷),記下分割區名稱,例如 `sda1`(裝置路徑即 `/dev/sda1`)。

2. **建立掛載點目錄**(路徑自訂,之後會填進 `.env` 的 `SMB_SHARE_PATH`):
   ```bash
   sudo mkdir -p /mnt/mydisk
   ```

3. **先手動掛載測試看看**:
   ```bash
   sudo mount /dev/sda1 /mnt/mydisk
   df -h /mnt/mydisk   # 確認掛上去了、容量正確
   ls /mnt/mydisk       # 確認看得到原本的資料
   ```

4. **查硬碟的 UUID**(設定開機自動掛載要用 UUID,不要用 `/dev/sda1` 這種裝置代號——USB 隨插拔順序不同,裝置代號可能會變,UUID 才是固定的):
   ```bash
   sudo blkid /dev/sda1
   ```
   輸出裡 `UUID="xxxx-xxxx"` 那串就是要用的值,同一行的 `TYPE="..."` 是檔案系統類型。

5. **設定開機自動掛載**,編輯 `/etc/fstab`(`sudo $EDITOR /etc/fstab`),依檔案系統類型加一行:

   | 檔案系統 | 需要的套件 | fstab 那一行 |
   |---|---|---|
   | ext4(Linux 原生格式,推薦) | 內建,不用額外裝 | `UUID=xxxx-xxxx /mnt/mydisk ext4 defaults 0 2` |
   | NTFS(Windows 格式化過的硬碟常見) | `sudo apt install ntfs-3g` | `UUID=xxxx-xxxx /mnt/mydisk ntfs-3g defaults,uid=1000,gid=1000 0 0` |
   | exFAT(常見於隨身碟) | `sudo apt install exfatprogs` | `UUID=xxxx-xxxx /mnt/mydisk exfat defaults,uid=1000,gid=1000 0 0` |

   把 `UUID=xxxx-xxxx`、`/mnt/mydisk` 換成步驟 4、2 的實際值。`uid=1000,gid=1000` 是 NTFS/exFAT 專用(這兩種檔案系統沒有 Linux 的權限概念,掛載時要指定用哪個使用者/群組的身分讀寫——`1000` 通常是第一個一般使用者的 uid/gid,可用 `id <你的使用者名稱>` 確認)。

6. **不重開機,直接測試 fstab 有沒有寫對**:
   ```bash
   sudo umount /mnt/mydisk
   sudo mount -a
   df -h /mnt/mydisk
   ```
   `mount -a` 沒有印出錯誤,且 `df -h` 看得到掛載,代表 fstab 設定沒問題,重開機也會自動掛好。如果 `mount -a` 報錯,先修正 fstab 內容再繼續,不要先重開機測試(fstab 寫錯可能導致開機卡住)。

7. 確認硬碟已穩定掛載後,把掛載點路徑填進 `.env` 的 `SMB_SHARE_PATH`(例如 `SMB_SHARE_PATH=/mnt/mydisk`),再照下面的「安裝」步驟跑 `samba/install.sh`。

## 安裝

```bash
sudo ./samba/install.sh
```

會做的事:

1. `apt-get install samba`
2. 檢查 `.env` 裡的 `SMB_SHARE_PATH` 存在(不存在會問要不要建立;如果這其實是外接硬碟的掛載點,記得先照上面「掛載外接硬碟」的步驟把硬碟掛好再跑腳本,不要讓腳本在硬碟沒掛載時建出一個空資料夾)
3. 確認/建立 `SMB_USER` 這個系統使用者,並設定 Samba 密碼(`smbpasswd`,跟系統登入密碼是分開的兩組密碼)
4. 備份現有 `/etc/samba/smb.conf`,**只 append 一個新的分享區塊**,不覆蓋既有設定
5. `testparm` 驗證語法,失敗就自動還原備份、不重啟服務
6. `systemctl enable --now smbd`

## 從 Windows / Mac 連線

- Windows:檔案總管網址列輸入 `\\<pi-ip>\<SMB_SHARE_NAME>`
- macOS:Finder → 前往 → 連接伺服器 → `smb://<pi-ip>/<SMB_SHARE_NAME>`

## 重複執行

腳本會偵測 `smb.conf` 內是否已有同名分享區塊,有的話會跳過追加(避免重複),但仍會重新設定 Samba 密碼與 workgroup。如果要改分享路徑或其他參數,建議直接編輯 `/etc/samba/smb.conf` 或改用不同的 `SMB_SHARE_NAME` 建立新分享。

## 常見坑:連得上但寫入 Permission Denied

分享區塊用 `force user = $SMB_USER`,代表 Samba 實際寫檔時是用這個使用者的身分,跟目錄本身的擁有者要對得上,不然會出現「連得上、看得到檔案,但新增/修改檔案一律 Permission Denied」的狀況。

- 若 `SMB_SHARE_PATH` 原本不存在、是腳本幫你新建的:腳本會自動把目錄 `chown` 給 `SMB_USER`,不用額外處理。
- 若 `SMB_SHARE_PATH` 是既有目錄(例如外接硬碟上已經有資料):腳本**不會**動它原本的擁有者/權限,請自行確認 `SMB_USER` 對這個路徑有寫入權限(例如 `chown -R $SMB_USER:$SMB_USER $SMB_SHARE_PATH`,或至少確保群組/other 有寫入權限),否則就會踩到這個坑。
