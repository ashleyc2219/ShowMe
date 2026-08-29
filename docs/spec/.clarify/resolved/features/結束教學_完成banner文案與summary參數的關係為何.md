# 釐清問題

完成 banner 文案與 summary 參數的關係為何？

# 定位

Feature：結束教學「顯示完成 banner」。§7.4 參數有 summary，例子 banner 為「✅ Done — you created a project」，未寫 summary 是否嵌入。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | banner 固定為 ✅ Done — {summary} |
| B | banner 固定字串 ✅ Done — you created a project，忽略 summary |
| C | 只清 overlay 不保證 banner 文案；summary 僅給 agent 日誌 |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

結束教學 banner 規則、end_tutorial 參數、UX 驗收。

# 優先級

Medium
- Medium：影響邊界條件或測試完整性

---
# 解決記錄

- **回答**：B - banner 固定為 ✅ Done — you created a project，忽略 summary
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/結束教學.feature
- **變更內容**：summary 不嵌入橫幅

