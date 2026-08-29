# 釐清問題

既有進行中場次時再次呼叫 start_tutorial 要新建還是重用？

# 定位

ERM：Session 的生命週期與 `session_id` 唯一性。設計稿 §7.1 寫「啟動（或重用）Chrome」，未定義第二次 `start_tutorial` 是新 Session 還是覆蓋同一個。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 每次 start_tutorial 都新建 Session 並回傳新 session_id；舊場次視為結束 |
| B | 同一 process 只允許一個 Session；再次呼叫覆蓋 goal、重開 url，session_id 不變 |
| C | 同一 url 重用既有 Session；不同 url 則新建 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Session、TutorialStart、開始教學、結束教學（是否需先 end）、顯示步驟（舊 session_id 是否仍有效）。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：B - 同一 process 只允許一個 Session；再次呼叫覆蓋 goal、重開 url，session_id 不變
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/開始教學.feature
- **變更內容**：Session 註明單場覆蓋與 session_id 不變、steps_shown 歸零、state 回 READY；開始教學新增對應 Rule 與 Example
