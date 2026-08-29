# 釐清問題

click 完成所需的 DOM mutation 次數 N 為何？

# 定位

Feature：顯示步驟「kind 為 click 時目標被點擊後 500 ms 內 DOM mutation 達到規格的 N 次即完成」。§9.3 寫 ≥ N 但未給 N。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | N=1：500 ms 內至少一次 mutation 即完成 |
| B | N=3：500 ms 內至少三次 mutation 才完成 |
| C | 刪除此條件，click 只認元素移除／隱藏或 URL 變更或 Next |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

顯示步驟 click 完成規則、overlay MutationObserver、誤觸／漏觸測試。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：C - 刪除 mutation ≥ N 條件；click 只認元素移除／隱藏、URL 變更、或 Next；不等待 HTTP response
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature
- **變更內容**：Step 註明 click 完成條件；刪除「500 ms 內 mutation N 次」規則；debounce 題因條件刪除而不再適用

