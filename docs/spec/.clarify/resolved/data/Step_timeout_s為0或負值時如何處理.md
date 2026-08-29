# 釐清問題

timeout_s 為 0 或負值時如何處理？

# 定位

ERM：Step.timeout_s（預設 120）。規格未寫呼叫端傳 0 或負數時是立即 timeout、視為預設 120，還是操作失敗。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗（需補錯誤碼） |
| B | 視為 0：立即回 event=timeout，state=READY |
| C | 忽略非法值，改用預設 120 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Step.timeout_s、顯示步驟 timeout 規則、等待使用者的 timeout_s=25。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：C - 未傳、0 或負值改用預設 120
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：不新增錯誤碼、不立即 timeout
