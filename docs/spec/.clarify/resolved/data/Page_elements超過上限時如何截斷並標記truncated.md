# 釐清問題

page.elements 超過上限時如何截斷並標記 truncated？

# 定位

ERM：Page.truncated 與 PageElement 數量。§9.1 寫「上限約 150 個 node，viewport 內優先；truncated: true」。約、優先順序、是否剛好 150 仍 truncated 皆未定。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 硬上限 150：先 viewport 內互動角色再其他；滿 150 後丟棄其餘且 truncated=true；少於等於 150 則 truncated=false |
| B | 硬上限 150 但不分 viewport，依 DOM 走訪順序取前 150 |
| C | 超過 150 仍全回傳，只把 truncated 設 true 當警告 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Page、PageElement、開始教學、檢查頁面、顯示步驟回傳的 page、snapshot 測試。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：B - 硬上限 150，依 DOM 走訪順序取前 150，不分 viewport；≤150 則 truncated=false
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/開始教學.feature
- **變更內容**：刪除「約 150」與 viewport 優先；超過則丟棄其餘

