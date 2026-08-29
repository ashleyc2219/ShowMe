# 釐清問題

session_ttl 到期時進行中的等待如何結束？

# 定位

ERM：Session 的 `session_ttl = 30 min`（Table Note 常數）。規格未寫到期後 state 變成什麼、阻塞中的 `show_step` 回什麼 event。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 到期視為 timeout：show_step 回 event=timeout，state=READY，Session 仍在 |
| B | 到期釋放 Session：呼叫端得到 session_not_found，state 不再可查 |
| C | 到期視為 DONE 且清 overlay，後續 tool 皆失敗 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Session.state、Event.kind、顯示步驟 timeout 規則、結束教學、session_ttl 測試。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：Short - 不要這個限制
- **更新的規格檔**：docs/spec/erm.dbml
- **變更內容**：移除 session_ttl = 30 min，教學場次沒有總時長上限
