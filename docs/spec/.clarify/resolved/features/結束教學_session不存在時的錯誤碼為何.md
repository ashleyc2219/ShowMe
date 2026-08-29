# 釐清問題

session 不存在時結束教學的錯誤碼為何？

# 定位

Feature：結束教學。§7.4 只定義成功回 `{ok: true}`，未寫 session_id 無效時的行為。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗且錯誤為 session_not_found |
| B | 冪等成功：回 ok=true，不改變任何狀態 |
| C | 操作失敗但使用另一個錯誤碼（請用 Short 寫出） |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

結束教學前置條件、與檢查頁面 / 顯示步驟的錯誤一致性。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：A - 操作失敗且錯誤為 session_not_found
- **更新的規格檔**：docs/spec/features/結束教學.feature、docs/spec/erm.dbml
- **變更內容**：end_tutorial 在 Session 不存在時回 session_not_found
