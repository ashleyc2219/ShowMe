# 釐清問題

kind 不屬於四選一時是否操作失敗？

# 定位

Feature：顯示步驟；ERM：Step.kind ∈ {click, input, select, observe}。規格未寫傳入其他字串的前置失敗。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗（需補錯誤碼，例如 invalid_kind） |
| B | 視為 observe（最寬鬆完成條件） |
| C | 視為 click |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

顯示步驟前置條件、Step.kind、錯誤列舉。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：B - 不屬於四選一時視為 observe
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：非法 kind 走 observe；expect_text 空則 expect_text_required

