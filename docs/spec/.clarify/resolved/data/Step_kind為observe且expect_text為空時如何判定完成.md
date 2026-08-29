# 釐清問題

kind 為 observe 且 expect_text 為空時如何判定完成？

# 定位

ERM：Step.kind 與 Step.expect_text 的跨屬性不變條件。§9.3 寫 observe 完成條件為「出現 expect_text 或按 Next」；未寫 expect_text 缺省時「出現 expect_text」如何評。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 視為前置失敗，show_step 操作失敗（需補錯誤碼） |
| B | 忽略文字條件，只接受 Next（或 I'm stuck / timeout） |
| C | 目標元素一出現在 snapshot 即 step_done |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Step、顯示步驟 observe 規則、Event.kind、錯誤契約。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：A - 視為前置失敗，error 為 expect_text_required
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：kind 為 observe 且 expect_text 為空時操作失敗
