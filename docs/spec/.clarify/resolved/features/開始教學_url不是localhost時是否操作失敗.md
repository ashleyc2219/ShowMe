# 釐清問題

url 不是 localhost 時是否操作失敗？

# 定位

Feature：開始教學。產品範圍寫 MVP 為 localhost，D9 同旨；tool 契約未寫拒絕非 localhost 的前置條件。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 非 localhost / 非 127.0.0.1 一律操作失敗（需補錯誤碼） |
| B | 不檢查 host，任何 url 都嘗試開啟 |
| C | 允許 localhost 與 127.0.0.1 任意 port；其餘失敗 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

開始教學前置條件、安全邊界、Hackathon demo 是否只能打 :3000。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：B - 不檢查 host，任何 url 都嘗試開啟
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/開始教學.feature
- **變更內容**：開始教學不因不是 localhost 而失敗；打不開仍是 navigation_failed
