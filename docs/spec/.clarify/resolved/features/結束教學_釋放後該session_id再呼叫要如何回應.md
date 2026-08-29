# 釐清問題

釋放後該 session_id 再呼叫要如何回應？

# 定位

Feature：結束教學「釋放 session」。未寫釋放是刪除還是 state=DONE 仍可查；之後 inspect / show_step / 再次 end 的契約不明。

# 多選題

| 選項 | 描述 |
|--------|-------------|
| A | 刪除 Session：之後任何 tool 皆 session_not_found |
| B | 保留 DONE 紀錄：inspect 可回最後 page，show_step 失敗，end 冪等 ok=true |
| C | 保留 DONE 但所有 tool 都操作失敗且錯誤為 session_done |
| Short | 提供其他簡短答案（<=5 字）|

# 影響範圍

Session 生命週期、檢查頁面、顯示步驟、結束教學冪等、session_not_found 語意。

# 優先級

High
- High：阻礙核心功能定義或資料建模

---
# 解決記錄

- **回答**：A - 刪除 Session；之後任何 tool 皆 session_not_found
- **更新的規格檔**：docs/spec/erm.dbml、docs/spec/features/結束教學.feature
- **變更內容**：end_tutorial 成功後刪除 Session，不保留 DONE
