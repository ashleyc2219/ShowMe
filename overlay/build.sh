#!/usr/bin/env bash
# 產生 overlay/overlay.js（人員 A 的 add_init_script 注入的那個檔案）。
#
# 這是「不自建 bundler」的最小版本：純 cat，沒有 webpack/rollup。
# 編輯 overlay.src.js，不要直接編輯 overlay.js —— overlay.js 是產物，
# 每次 build.sh 都會整份覆蓋掉。
#
# vendor/driver.iife.js、vendor/driver.css 還沒 vendor 進來之前（S3 階段），
# 這支腳本會跳過 Driver.js 那段，只把 overlay.src.js 原樣輸出成 overlay.js，
# 讓 snapshot() 能先跑；等 S4 vendor 進 Driver.js 後兩段都會一起接上。

set -euo pipefail
cd "$(dirname "$0")"

OUT=overlay.js

{
  echo "/*"
  echo " * GENERATED FILE — 由 overlay/build.sh 產生，不要手動編輯。"
  echo " * 要改邏輯請改 overlay/overlay.src.js 後重跑 ./build.sh。"
  echo " */"

  if [ -f vendor/driver.iife.js ]; then
    echo
    echo "/* ===== vendor: Driver.js（MIT）— 版本與授權見 vendor/LICENSE ===== */"
    cat vendor/driver.iife.js
  fi

  if [ -f vendor/driver.css ]; then
    echo
    echo "/* ===== vendor: driver.css，內嵌成字串常數給 overlay.src.js 注入 ===== */"
    printf 'var __SHOWME_DRIVER_CSS__ = '
    node -e "process.stdout.write(JSON.stringify(require('fs').readFileSync('vendor/driver.css','utf8')))"
    printf ';\n'
  fi

  echo
  echo "/* ===== ShowMe overlay 邏輯（來源：overlay/overlay.src.js） ===== */"
  cat overlay.src.js
} > "$OUT"

echo "built $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes)"
