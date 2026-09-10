#!/usr/bin/env bash
# build Vue 前端,把靜態檔部署進 dashboard/html/(nginx 直接 serve 這個目錄)。
# 保留 dashboard/html/ 裡既有的 config.js 與 cron 產生的 *.json,只換掉 build 產物。
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f dashboard/html/config.js ]; then
  echo "找不到 dashboard/html/config.js,先從範本複製一份並依你的機器調整內容:"
  echo "  cp dashboard/config.example.js dashboard/html/config.js"
  exit 1
fi

(cd dashboard/frontend && npm install && npm run build)

mkdir -p dashboard/html
rsync -a --delete --exclude 'config.js' --exclude '*.json' dashboard/frontend/dist/ dashboard/html/

echo "已部署到 dashboard/html/(nginx 容器直接讀這個目錄,不需要重啟)"
