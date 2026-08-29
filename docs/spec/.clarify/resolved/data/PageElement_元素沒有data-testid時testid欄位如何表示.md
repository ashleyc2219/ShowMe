# 釐清問題

元素沒有 data-testid 時 testid 欄位如何表示？

# 定位

ERM：PageElement.testid。§7.1 例子中 Settings 沒有 testid 欄；§9.1 有的元素有、有的沒有。JSON 是省略鍵還是 `"testid": ""` 會改契約與測試。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 省略該鍵，agent 收到的 element 物件沒有 testid |
| B | 鍵永遠存在，沒有時值為空字串 |
| C | 沒有 data-testid 的元素不進入 page.elements |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

PageElement、開始教學 / 檢查頁面 / 顯示步驟 的 page.elements DataTable。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：B - testid 鍵永遠存在，沒有時為空字串
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/開始教學.feature
- **變更內容**：Settings 例子鎖定空字串而非省略鍵
