# 釐清問題

等待時間剛好等於 timeout_s 時算 timeout 還是完成？

# 定位

Feature：顯示步驟「等待超過 timeout_s 時 event 為 timeout」。未寫 elapsed 剛好等於 timeout_s、以及事件與 timeout 同時到達的先後。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | elapsed >= timeout_s 即 timeout（含剛好相等） |
| B | 僅 elapsed > timeout_s 才 timeout；相等時若已有完成訊號則 step_done |
| C | 同一瞬間完成訊號優先於 timeout |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

顯示步驟 timeout 規則、elapsed_s 邊界測試、Step.timeout_s。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：A - elapsed_s >= timeout_s 即 timeout（含剛好相等；同一瞬間完成訊號仍算 timeout）
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：規則由「超過」改為「大於等於」

