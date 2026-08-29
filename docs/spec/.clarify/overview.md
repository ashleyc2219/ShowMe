# ShowMe 規格釐清總覽

**掃描日期：** 2026-08-29  
**作用中規格：** `docs/spec/erm.dbml`、`docs/spec/features/*.feature`  
**對照來源：** `docs/spec/draft/design-draft.md`（v0.2）  
**已解決項目：** 見 `docs/spec/.clarify/resolved/`

路徑對應 prompt 的 `spec/.clarify/` → 本 repo 的 `docs/spec/.clarify/`。

---

## 3.1 釐清項目統計

- 資料模型相關：0 項
- 功能模型相關：0 項
- 總計：0 項（Discovery 26 項皆已釐清）

## 3.2 優先級分佈

- High：0 項
- Medium：0 項
- Low：0 項

## 3.3 建議釐清順序

無待處理項目。

## 3.4 釐清策略說明

Discovery 列出的 26 項已全部寫回 `docs/spec/erm.dbml` 與 `docs/spec/features/*.feature`。

刻意不建項（仍過濾）：§14 技術棧／demo 營運、§15 SHOW runtime、附錄 C、off_script 是否 MVP、`session_id` 字串格式、`next_action` 逐字鎖定、詞彙表檔（C1）。

## 3.5 覆蓋度摘要

| 檢查項 | 狀態 | 說明 |
|---|---|---|
| A1 實體完整性 | Resolved | Session 生命週期、單場覆蓋、無 ttl |
| A2 屬性定義 | Resolved | testid、signal、kind vs event |
| A3 屬性值邊界 | Resolved | timeout_s、truncated 150、timeout 相等 |
| A4 跨屬性不變條件 | Resolved | observe × expect_text |
| A5 關係與唯一性 | Resolved | Event 主鍵 (session_id, ts)，同 ts 後至丟棄 |
| A6 生命週期與狀態 | Resolved | 狀態×工具、結束後刪除 Session |
| B1 功能識別 | Resolved | wait_for_user 不做；show_step 阻塞 |
| B2 規則完整性 | Resolved | 非法 kind 視為 observe、stuck 計步 |
| B3 例子覆蓋度 | Outstanding | 部分 Rule 仍 `#TODO`（缺例子不是缺決策） |
| B4 邊界條件 | Resolved | 空 goal、N／debounce 已刪、timeout 邊界 |
| B5 錯誤與異常 | Resolved | error 欄、session_not_found、並發 show_step |
| C1 詞彙表 | Outstanding | 不改實作，Discovery 已略 |
| C2 術語衝突 | Resolved | Event.kind 與 StepResult.event 分開 |
| D1 待決事項 | Resolved | 阻塞 vs 輪詢已定 |
| D2 模糊描述 | Resolved | 「約 150」、mutation N |

---

Clarify 完成。下一步見 `docs/spec/prompts/4.design_prompt.md`（或專案規劃／實作），**不要**重跑 formulation 硬補例子。
