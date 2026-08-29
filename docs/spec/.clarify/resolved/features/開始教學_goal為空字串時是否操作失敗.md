# 釐清問題

goal 為空字串時是否操作失敗？

# 定位

Feature：開始教學；ERM：Session.goal。規格要求記錄 goal，未寫空字串或唯空白。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 操作失敗（需補錯誤碼） |
| B | 允許空 goal，照常開頁並回傳 |
| C | 去掉首尾空白後仍空則失敗，否則接受 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

開始教學前置條件、Session.goal、TutorialStart.goal。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：B - 允許空 goal，照常開頁
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/開始教學.feature
- **變更內容**：空字串不是錯誤；不 trim
