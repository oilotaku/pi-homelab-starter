#!/usr/bin/env bash
# 安裝 Samba,並把 .env 設定的分享區塊 append 進 /etc/samba/smb.conf
# 不會整檔覆蓋既有設定,只追加一個新的分享區塊(若已存在同名區塊則跳過)。

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=../lib/common.sh
source "${ROOT_DIR}/lib/common.sh"

require_root
load_env

SMB_CONF="/etc/samba/smb.conf"

: "${SMB_SHARE_NAME:?請在 .env 設定 SMB_SHARE_NAME}"
: "${SMB_SHARE_PATH:?請在 .env 設定 SMB_SHARE_PATH}"
: "${SMB_USER:?請在 .env 設定 SMB_USER}"

log_info "安裝 samba 套件..."
apt-get update -qq
apt-get install -y samba

CREATED_SHARE_DIR=0
if [[ ! -d "$SMB_SHARE_PATH" ]]; then
  log_warn "分享路徑 ${SMB_SHARE_PATH} 不存在。"
  log_warn "若這是外接硬碟的掛載點,請先確認硬碟已掛載,再重新執行本腳本。"
  if confirm "要現在建立這個目錄嗎?(如果只是單純資料夾,不是掛載點,選 y 沒問題)"; then
    mkdir -p "$SMB_SHARE_PATH"
    CREATED_SHARE_DIR=1
  else
    log_error "已取消,分享路徑不存在無法繼續。"
    exit 1
  fi
fi

if ! id -u "$SMB_USER" &>/dev/null; then
  log_warn "系統使用者 ${SMB_USER} 不存在。"
  if confirm "要建立系統使用者 ${SMB_USER} 嗎?"; then
    useradd -m -s /usr/sbin/nologin "$SMB_USER"
  else
    log_error "已取消,分享需要一個既有的系統使用者。"
    exit 1
  fi
fi

# smb.conf 用 force user = $SMB_USER,所以 Samba 寫檔時是用這個使用者的身分。
# 剛建立的目錄預設是 root:root,若 SMB_USER 不是 root 會沒有寫入權限,這裡補上正確擁有者。
# 若目錄本來就存在(例如外接硬碟已有的資料),不動它的既有擁有者/權限,只提醒使用者自行確認。
if [[ "$CREATED_SHARE_DIR" == 1 ]]; then
  chown "${SMB_USER}:${SMB_USER}" "$SMB_SHARE_PATH"
else
  log_warn "分享路徑 ${SMB_SHARE_PATH} 是既有目錄,腳本不會更動它的擁有者/權限。若之後從網路芳鄰寫入檔案時遇到 Permission Denied,請確認 ${SMB_USER} 對這個路徑有寫入權限。"
fi

log_info "設定 Samba 密碼(給 ${SMB_USER} 用,系統登入密碼與 Samba 密碼是分開的):"
smbpasswd -a "$SMB_USER"

BACKUP="${SMB_CONF}.bak.$(date +%Y%m%d%H%M%S)"
cp "$SMB_CONF" "$BACKUP"
log_info "已備份原始設定至 ${BACKUP}"

if grep -q "^\[${SMB_SHARE_NAME}\]" "$SMB_CONF"; then
  log_warn "smb.conf 內已經有 [${SMB_SHARE_NAME}] 區塊,略過追加,請自行檢查設定是否符合需求。"
else
  log_info "追加分享區塊 [${SMB_SHARE_NAME}] 到 ${SMB_CONF}..."
  sed \
    -e "s#__SMB_SHARE_NAME__#${SMB_SHARE_NAME}#g" \
    -e "s#__SMB_SHARE_PATH__#${SMB_SHARE_PATH}#g" \
    -e "s#__SMB_USER__#${SMB_USER}#g" \
    "${SCRIPT_DIR}/share.conf.template" >> "$SMB_CONF"
fi

if [[ -n "${SMB_WORKGROUP:-}" ]]; then
  sed -i "s/^\(\s*workgroup\s*=\s*\).*/\1${SMB_WORKGROUP}/" "$SMB_CONF"
fi

log_info "驗證設定檔語法..."
if ! testparm -s "$SMB_CONF" &>/dev/null; then
  log_error "smb.conf 語法驗證失敗,還原剛才的變更並中止。"
  cp "$BACKUP" "$SMB_CONF"
  exit 1
fi

systemctl enable --now smbd
log_info "完成。分享路徑:${SMB_SHARE_PATH} → \\\\<pi-ip>\\${SMB_SHARE_NAME}"
