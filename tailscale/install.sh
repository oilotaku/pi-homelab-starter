#!/usr/bin/env bash
# 安裝 Tailscale(若尚未安裝)並依 .env 設定執行 `tailscale up`

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# shellcheck source=../lib/common.sh
source "${ROOT_DIR}/lib/common.sh"

require_root
load_env

if command -v tailscale &>/dev/null; then
  log_info "Tailscale 已安裝,略過安裝步驟。"
else
  log_info "安裝 Tailscale(官方安裝腳本)..."
  curl -fsSL https://tailscale.com/install.sh | sh
fi

UP_ARGS=()

if [[ -n "${TS_AUTHKEY:-}" ]]; then
  UP_ARGS+=("--authkey=${TS_AUTHKEY}")
fi

if [[ "${TS_ADVERTISE_EXIT_NODE:-false}" == "true" ]]; then
  UP_ARGS+=("--advertise-exit-node")
fi

if [[ -n "${TS_ADVERTISE_ROUTES:-}" ]]; then
  UP_ARGS+=("--advertise-routes=${TS_ADVERTISE_ROUTES}")
fi

UP_ARGS+=("--accept-dns=${TS_ACCEPT_DNS:-true}")

DISPLAY_ARGS=("${UP_ARGS[@]}")
for i in "${!DISPLAY_ARGS[@]}"; do
  if [[ "${DISPLAY_ARGS[$i]}" == --authkey=* ]]; then
    DISPLAY_ARGS[$i]="--authkey=***"
  fi
done

log_info "執行: tailscale up ${DISPLAY_ARGS[*]}"
log_warn "若沒有設定 TS_AUTHKEY,接下來會印出一個網址,需要用瀏覽器登入 Tailscale 帳號完成連線。"
tailscale up "${UP_ARGS[@]}"

log_info "完成。目前狀態:"
tailscale status
