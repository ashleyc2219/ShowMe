# 釐清問題

session 不存在時檢查頁面的錯誤碼為何？

# 定位

Feature：檢查頁面。§7.3 只在 show_step 列出 session_not_found；inspect_page 吃 session_id 但未寫失敗契約。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 與 show_step 相同：操作失敗且錯誤為 session_not_found |
| B | 操作失敗但使用另一個錯誤碼（請用 Short 寫出） |
| C | 不視為錯誤，回傳空 page（url 空、elements 空、truncated=false） |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

檢查頁面前置條件、錯誤列舉是否跨 tool 共用。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：A - 操作失敗且錯誤為 session_not_found
- **更新的規格檔**：docs/spec/features/檢查頁面.feature、docs/spec/erm.dbml
- **變更內容**：inspect_page 在 Session 不存在時回 session_not_found
