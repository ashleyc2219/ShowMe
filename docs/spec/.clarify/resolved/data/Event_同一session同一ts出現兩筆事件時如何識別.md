# 釐清問題

同一 session 同一 ts 出現兩筆事件時如何識別？

# 定位

ERM：Event 主鍵目前為 (session_id, ts)。§9.4 只有 ts 舉例 1756400000；每步恰好一次可降低碰撞，但 stuck 與誤觸重送未定義。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 維持 (session_id, ts)；同 ts 後至事件丟棄（每步恰好一次） |
| B | 主鍵改為 session_id 加單調序號（規格需新增欄位） |
| C | Event 不持久化、不需主鍵，只當作當下 callback 資料 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Event 主鍵、顯示步驟「每步恰好一次」、erm.dbml Indexes。

# 優先級

Low
- Low：優化或細節調整

---
# 解決記錄

- **回答**：A - 維持 (session_id, ts)；同 ts 後至丟棄；每步恰好一次
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：不新增序號欄位

