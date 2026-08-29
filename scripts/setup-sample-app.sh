#!/usr/bin/env bash
# 一鍵建立 ShowMe 的示範產品頁：refine 的 finefoods-antd example。
# 對應文件：docs/sample-app.md
#
# 用法：
#   ./scripts/setup-sample-app.sh
#
# 只做到 npm install 為止；npm run dev 是長駐 server，故意不放進腳本，
# 完成後照畫面提示自己手動啟動。
#
# 目前只驗證過 macOS（BSD sed）。Linux 請把下面的 `sed -i ''` 改成 `sed -i`。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SAMPLE_DIR="$ROOT_DIR/sample-app"
APP_DIR="$SAMPLE_DIR/finefoods-antd"

mkdir -p "$SAMPLE_DIR"
cd "$SAMPLE_DIR"

if [ -d "$APP_DIR" ]; then
  echo "==> sample-app/finefoods-antd 已存在，略過 scaffold（想重新拉一份就先 rm -rf sample-app/finefoods-antd）"
else
  echo "==> npm create refine-app@latest -- --example finefoods-antd"
  npm create refine-app@latest -- --example finefoods-antd
fi

if [ ! -d "$APP_DIR" ]; then
  echo "!! 預期的目錄 $APP_DIR 不存在，scaffold 出來的資料夾名稱可能跟預期不同，請手動確認 sample-app/ 底下的內容並更新這支腳本。" >&2
  exit 1
fi

cd "$APP_DIR"

echo "==> 修正 package.json 內鎖死的 peer dependency（^5.1.0 -> ^5.0.0）"
sed -i '' 's/"\^5\.1\.0"/"^5.0.0"/g' package.json

echo "==> npm install --legacy-peer-deps"
npm install --legacy-peer-deps

cat <<EOF

==> 完成。啟動方式：

    cd sample-app/finefoods-antd
    npm run dev

然後打開 http://localhost:3000
EOF
