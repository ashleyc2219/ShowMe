# 釐清問題

overlay 發出的 Event.kind 與 StepResult.event 是否使用同一組值？

# 定位

ERM：Event.kind（step_done / stuck / off_script）對 StepResult.event（另含 timeout、pending）。同名異義：一個是頁面事件，一個是 tool 回傳。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 分開建模：overlay 只發三種 kind；timeout 與 pending 只存在 StepResult.event |
| B | 合併為同一列舉，overlay 也可發 timeout/pending（server 寫回頁面） |
| C | 取消 Event.kind，一律只用 StepResult.event |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Event、StepResult、顯示步驟、等待使用者、erm.dbml 欄位合併或拆表。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：A - overlay 只發三種 kind；timeout 只在 StepResult.event；MVP 無 pending
- **更新的規格檔**：docs/spec/erm.dbml
- **變更內容**：Event.kind 與 StepResult.event 分開建模
