# 釐清問題

show_step 的錯誤是丟出 ToolError 還是寫在回傳值？

# 定位

Feature：顯示步驟所有「Then 操作失敗」規則。§8.2 偽碼 `raise ToolError(...)`；§7.3 JSON 成功形狀沒有 error 欄。測試要斷言例外還是 StepResult。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 一律 MCP ToolError / 例外，訊息或 code 為 uid_not_in_snapshot 等；無 StepResult |
| B | 一律回 StepResult，另加 error 欄；HTTP/MCP 仍成功 |
| C | uid_not_in_snapshot 回傳帶 page 的結構（因為要附新鮮 page），其餘丟例外 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

顯示步驟、檢查頁面、結束教學、開始教學的失敗 Then、Gherkin「操作失敗」的 StepDef。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：B - 一律回傳，另加 error 欄；MCP 仍成功
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：TutorialStart 與 StepResult 新增 error；失敗不丟例外
