# 釐清問題

Session 各狀態允許呼叫哪些 MCP 工具？

# 定位

ERM：Session.state（IDLE / READY / SHOWING / DONE）與合法轉換。§8.1 只畫 happy path；未寫 SHOWING 時 `inspect_page` / `end_tutorial`、DONE 時再 `show_step`、尚未 start 時呼叫其他 tool 是否合法。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 嚴格依狀態機：僅 READY 可 show_step/inspect/end；SHOWING 只等事件；DONE 全拒；未存在則 session_not_found |
| B | 除 show_step 需 READY 外，inspect 與 end 在 READY 與 SHOWING 皆可（輪詢模式需要） |
| C | 不檢查 state，只檢查 session 是否存在；非法時序由 agent 自己負責 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Session.state 轉換、檢查頁面、顯示步驟、結束教學、等待使用者（非阻塞時 SHOWING 仍可能被呼叫）。依賴「阻塞與輪詢如何擇一」。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：A - 嚴格依狀態機（最簡單實作）：僅 READY 可 show_step/inspect/end；SHOWING 只等；start_tutorial 仍可覆蓋
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature、docs/spec/features/檢查頁面.feature、docs/spec/features/結束教學.feature
- **變更內容**：補工具與狀態對照；SHOWING/DONE 時 inspect/show/end 操作失敗
