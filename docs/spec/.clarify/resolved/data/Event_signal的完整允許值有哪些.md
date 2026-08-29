# 釐清問題

Event 與 StepResult 的 signal 完整允許值有哪些？

# 定位

ERM：Event.signal、StepResult.signal。規格只舉 `url_changed`、`input_filled`；§9.3 還有元素移除、hidden、blur/change、expect_text、Next、I'm stuck，未對到 signal 列舉。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 固定列舉：url_changed、element_removed、element_hidden、dom_mutated、input_filled、select_changed、text_appeared、next_clicked、stuck_clicked（僅這些） |
| B | 只保證規格已出現的 url_changed 與 input_filled；其餘 signal 字串實作自訂但不列入驗收 |
| C | signal 可為空；完成只看 event 欄位 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Event、StepResult、顯示步驟所有完成規則的 Then 資料。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：C - signal 可為空；完成只看 event
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：回傳不再驗收 signal 值；Then 只看 event
