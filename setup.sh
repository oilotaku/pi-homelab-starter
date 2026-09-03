#!/usr/bin/env bash
# 主選單:選要安裝哪些服務

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=lib/common.sh
source "${SCRIPT_DIR}/lib/common.sh"

if [[ ! -f "${SCRIPT_DIR}/.env" ]]; then
  log_warn "找不到 .env,先幫你從 .env.example 複製一份,請編輯後再重新執行。"
  cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env"
  chmod 600 "${SCRIPT_DIR}/.env"
  log_info "已建立 ${SCRIPT_DIR}/.env,請編輯裡面的值後再執行 ./setup.sh"
  exit 0
fi

load_env

check_pihole_password() {
  if [[ -z "${PIHOLE_WEBPASSWORD:-}" || "${PIHOLE_WEBPASSWORD}" == "changeme" ]]; then
    log_error "PIHOLE_WEBPASSWORD 還是預設值或未設定,請先編輯 .env 改成一組強密碼再繼續。"
    exit 1
  fi
}

echo "要安裝哪個服務?"
echo "  1) Pi-hole (Docker)"
echo "  2) Samba"
echo "  3) Tailscale"
echo "  4) 全部"
echo "  q) 離開"
read -r -p "選擇: " choice

PIHOLE_UP=(docker compose -f "${SCRIPT_DIR}/pihole/docker-compose.yml" --env-file "${SCRIPT_DIR}/.env" up -d)

case "$choice" in
  1)
    check_pihole_password
    "${PIHOLE_UP[@]}"
    ;;
  2)
    sudo "${SCRIPT_DIR}/samba/install.sh"
    ;;
  3)
    sudo "${SCRIPT_DIR}/tailscale/install.sh"
    ;;
  4)
    check_pihole_password
    "${PIHOLE_UP[@]}"
    sudo "${SCRIPT_DIR}/samba/install.sh"
    sudo "${SCRIPT_DIR}/tailscale/install.sh"
    ;;
  q|Q)
    exit 0
    ;;
  *)
    log_error "不是有效選項"
    exit 1
    ;;
esac
