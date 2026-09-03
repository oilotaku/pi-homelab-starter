#!/usr/bin/env bash
# 共用函式:給 setup.sh 與各服務 install.sh 一起 source

set -euo pipefail

COLOR_RESET='\033[0m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'

log_info()  { echo -e "${COLOR_GREEN}[INFO]${COLOR_RESET} $*"; }
log_warn()  { echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $*"; }
log_error() { echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $*" >&2; }

require_root() {
  if [[ $EUID -ne 0 ]]; then
    log_error "此步驟需要 root 權限,請用 sudo 執行。"
    exit 1
  fi
}

confirm() {
  local prompt="${1:-確定要繼續嗎?}"
  read -r -p "$prompt [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]]
}

# 從 repo 根目錄載入 .env,不存在就提示並離開
load_env() {
  local root_dir
  root_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local env_file="${root_dir}/.env"

  if [[ ! -f "$env_file" ]]; then
    log_error "找不到 .env,請先執行: cp .env.example .env 並依需求修改。"
    exit 1
  fi

  # .env 內含密碼/authkey,強制收緊權限,不讓同機其他使用者讀到
  chmod 600 "$env_file" 2>/dev/null || true

  set -a
  # shellcheck disable=SC1090
  source "$env_file"
  set +a
}
