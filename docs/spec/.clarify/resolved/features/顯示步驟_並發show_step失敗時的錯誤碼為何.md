# 釐清問題

並發 show_step 失敗時的錯誤碼為何？

# 定位

Feature：顯示步驟「同一 session 並發的 show_step 被拒絕」。§12 有此失敗模式，未給錯誤字串。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗且錯誤為 show_step_in_progress（新增碼） |
| B | 操作失敗且重用 max_steps_exceeded 或 session_not_found（不新增碼） |
| C | 第二個呼叫排隊，不失敗，等第一個事件後才開始畫 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

顯示步驟並發規則、錯誤列舉、等待使用者模式下的重入。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：A - 操作失敗且錯誤為 show_step_in_progress
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：SHOWING 時第二個 show_step 回 show_step_in_progress
