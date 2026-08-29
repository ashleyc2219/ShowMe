# 釐清問題

使用者按 I'm stuck 後重畫同 uid 是否增加 steps_shown？

# 定位

Feature：顯示步驟 stuck 規則與「uid 通過驗證後 steps_shown 加 1」。§8.3 要 agent 用更白話說明對同一 uid 再呼叫 show_step；§8.2 每次成功畫出都 +1。是否因此更快撞 max_steps=12 未寫明。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 每次成功進入畫出都 +1，含 stuck 後的重畫 |
| B | 同一 uid 重畫不 +1，只改 instruction |
| C | stuck 當下就 +1，重畫再 +1（兩次） |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Session.steps_shown、max_steps_exceeded、顯示步驟 stuck 與加一規則。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：A - 每次成功畫出都 +1，含 stuck 後重畫同一 uid
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：steps_shown 於 uid 驗證通過並畫出時加 1；卡住當下不加第二次

