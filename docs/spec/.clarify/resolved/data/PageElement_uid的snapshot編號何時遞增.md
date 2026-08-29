# 釐清問題

PageElement 的 uid 中 snapshot 編號何時遞增？

# 定位

ERM：PageElement.uid 格式 `s{snapshot#}-{index}`。規格未寫 snapshot# 在 start / inspect / 每次 show_step 回傳 / 僅 DOM 變化時何者加一。這決定陳舊 uid 何時必然驗證失敗。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 每次產生 snapshot（start、inspect、show_step 回傳前）都加一 |
| B | 僅當 page.url 變更時加一；同頁重拍只改 index |
| C | 整個 Session 固定 snapshot#=1，只靠 index；格式中的世代僅文件示意 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

PageElement.uid、顯示步驟 uid_not_in_snapshot、檢查頁面、開始教學例子中的 s1-4 / s2-3。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：A - 每次產生 snapshot 都加一（start 從 1 起算；inspect 與 show_step 附 page 時再加一）
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/開始教學.feature、docs/spec/features/檢查頁面.feature、docs/spec/features/顯示步驟.feature
- **變更內容**：陳舊 snapshot# 的 uid 必然不在最新 page.elements

