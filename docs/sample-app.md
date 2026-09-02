# 示範產品頁：finefoods-antd

ShowMe 是「教使用者怎麼在別人的網站上操作」的工具，需要一個真實、夠複雜的網站來當
測試對象——也就是 [`docs/handoff.md`](handoff.md) 圖裡的「產品頁 :3000」。

我們用 [refine](https://refine.dev) 官方的 **finefoods-antd** example 當這個示範產品頁：
一個用 Ant Design 做的外送平台後台（訂單、商品、顧客管理），頁面元素多、互動流程長，
適合拿來驗證 `start_tutorial` / `show_step` 這些 MCP tool 能不能在真實頁面上找到元素、
畫箭頭、等使用者操作完。

它是**外部 example**，不是 ShowMe 本身的程式碼，所以整包都不進版控（見下方 .gitignore）。

---

## 一鍵建置

```bash
./scripts/setup-sample-app.sh
```

腳本會把 example 拉到 `sample-app/finefoods-antd/` 並裝好依賴，最後印出啟動指令。
`npm run dev` 是長駐的 dev server，腳本故意不幫你執行，跑完照畫面提示自己啟動：

```bash
cd sample-app/finefoods-antd
npm run dev
```

打開 http://localhost:3000。

已經建好一份的話重跑腳本會直接跳過 scaffold；想重新拉一份乾淨的，先 `rm -rf sample-app/finefoods-antd` 再跑。

目前腳本只在 macOS（BSD `sed`）上跑過。Linux 上請把腳本裡 `sed -i ''` 改成 `sed -i`。

---

## 手動步驟（腳本做的事，拆開講）

在 repo 根目錄下：

```bash
mkdir -p sample-app && cd sample-app

# 1. 用 refine 的 CLI 把 finefoods-antd example 拉下來
#    非互動：帶了 --example 就不會再跳問卷，直接照 example 名稱建資料夾
npm create refine-app@latest -- --example finefoods-antd

cd finefoods-antd

# 2. 修掉 package.json 裡鎖死的 peer dependency
#    這個 example 目前把某個套件鎖在 ^5.1.0，會讓下一步的 npm install 解不出依賴樹而失敗；
#    降回 ^5.0.0 才裝得起來。之後若 refine 官方修掉這個版本鎖定，這步可以拿掉。
sed -i '' 's/"\^5\.1\.0"/"^5.0.0"/g' package.json

# 2b. 讓 dev server 固定開在 :3000
#    vite 預設 port 是 5173，但 ShowMe 全專案（handoff.md、CLAUDE.md）都假設產品頁在 localhost:3000。
#    refine dev 會把參數原樣轉給 vite，所以直接在 npm script 補 --port 3000。
sed -i '' 's/"dev": "refine dev"/"dev": "refine dev --port 3000"/' package.json

# 3. 安裝依賴
#    --legacy-peer-deps：跳過 npm 對 peer dependency 衝突的嚴格檢查，
#    對這個 example 目前的依賴狀態是必要的，不然 npm install 會直接中止。
npm install --legacy-peer-deps

# 4. 啟動
npm run dev
```

---

## 目錄與版控

- 產出位置固定在 `sample-app/finefoods-antd/`。
- 整個 `sample-app/` 已加進 `.gitignore`——它是外部 example 加上自己的
  `node_modules`，體積大又跟 ShowMe 本身無關，不進版控。
- 需要重建就直接刪掉整個資料夾重跑腳本：`rm -rf sample-app && ./scripts/setup-sample-app.sh`。

## 疑難排解

- **`npm install` 卡在 peer dependency 衝突**：確認 step 2 的 `sed` 有跑到（打開
  `sample-app/finefoods-antd/package.json` 搜尋還有沒有 `^5.1.0`），或直接補跑
  `npm install --legacy-peer-deps`。
- **scaffold 出來的資料夾名稱跟預期不同**：`create-refine-app` 是照 example 名稱
  （`finefoods-antd`）建資料夾，如果 CLI 版本更新改了行為，腳本會在找不到
  `sample-app/finefoods-antd` 時報錯並停下——照錯誤訊息調整 `scripts/setup-sample-app.sh`
  裡的 `APP_DIR`。
- **port 3000 被佔用**：`npm run dev` 啟動失敗時看終端機輸出，refine/vite 通常會自動
  改用下一個空的 port，用它印出來的網址即可。
