# 釐清問題

MutationObserver 的 debounce 時長為何？

# 定位

Feature：顯示步驟 click 的 DOM mutation 完成條件。§10 寫 document.body 上 debounce 的 MutationObserver，未給毫秒數；與 §9.3「點擊後 500 ms 內」是否同一視窗未對齊。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | debounce = 500 ms，與 click 觀察窗相同 |
| B | debounce 另定較短值（例如 50 或 100 ms），觀察窗仍 500 ms |
| C | 不 debounce，每筆 mutation 即時計數 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

顯示步驟 click 誤觸／漏觸、overlay observer 實作、與 mutation 次數 N 的組合測試。可與 N 一併釐清。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：不適用（因 click 已刪除 mutation 計數完成條件）
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/顯示步驟.feature（與 mutation N 同一決策）
- **變更內容**：不再為「數 DOM 變幾次」規定 debounce；目標移除／隱藏仍可觀察 DOM，但不靠 mutation 次數判定完成

