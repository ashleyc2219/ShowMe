# ShowMe Canonical Design

**狀態：** Draft（2026-08-29）  
**觀眾：** 5 小時 hackathon 實作者與驗收測試撰寫者  
**目的：** 把已釐清規格收成一份可拆切片、可寫測試的設計。本檔不是實作、不是 plan repo。  
**目前 repo：** 高階骨架已有 `pyproject.toml`、`showme/`、`overlay/overlay.js`。四個 tool 仍回 `not_implemented`。`demo-app/` 不在本 repo。尚未 `uv sync`／未接 Playwright。

標記慣例：

| 標記 | 意思 |
|---|---|
| **約束** | hackathon / 產品不可違反 |
| **clarified** | `.clarify/resolved/` + 現行 `erm.dbml` / `.feature` |
| **design** | 本文件選擇；可改但須留理由 |
| **open** | 規格未寫死；不得假裝已定案 |

---

## 1. 文件目的與狀態

ShowMe 是給 **Qoder Coding Agent** 用的 **stdio MCP server**。Agent 剛做好的 Web App 跑在本機，開發者在 Qoder 聊天問「教我怎麼 create a project」：ShowMe 在真實頁面畫箭頭，**人自己點／打字**，做完再畫下一步。核心是教人，不是替人操作。

本檔回答：四個工具怎麼接、Session 怎麼轉、snapshot／uid 怎麼產生、完成怎麼判定、錯誤怎麼回、5 小時先做哪幾片、**兩人怎麼拆**（第 15.1 節）。

---

## 2. Source of Truth 與衝突裁決

優先序（與 `docs/spec/prompts/4.design_prompt.md` §3 相同）：

1. `docs/spec/.clarify/resolved/` 解決記錄  
2. `docs/spec/erm.dbml` 與 `docs/spec/features/*.feature`  
3. 本檔第 3 節 hackathon 約束（若與 1、2 衝突須標出來，不得默改規格）  
4. `docs/spec/draft/design-draft.md` D1–D10 與 §6–§10（僅 1、2 未覆蓋時）  
5. 本檔 **design** 選擇  

`design-draft.md` 早於 clarify。下列 draft 敘述**不得回流**：

| Draft 舊敘述 | 現行裁決 | 來源 |
|---|---|---|
| `raise ToolError(...)` | 回傳 `error` 欄，MCP 仍成功 | clarified：錯誤通道 B |
| 非阻塞 + `wait_for_user` | MVP 只做阻塞 `show_step` | clarified |
| `session_ttl = 30 min` | 無 ttl | clarified |
| 結束後 state=DONE 可查 | 刪除 Session | clarified |
| 只准 localhost | 不檢查 host；開不了才 `navigation_failed` | clarified |
| click：500 ms 內 mutation ≥ N | 刪除；只認移除／隱藏、URL、Next | clarified |
| 上限「約 150、viewport 優先」 | 硬上限 150、DOM 順序 | clarified |
| uid 世代未寫死 | 每次產生 snapshot，snapshot# +1 | clarified |
| 狀態機含 DONE | 成功 `end_tutorial` 後無 Session | clarified |
| §7.1 例子省略 Settings 的 testid 鍵 | 鍵永遠在，值為 `""` | clarified |

**未當來源：** `docs/plan/dev-prompts/phase0829.md`（他課殘留）、design-draft **§15**、**附錄 C**、**§14**（§14 只進本檔第 16 節 Demo 風險）。

`docs/spec/draft/architecture-ascii.md` 是 stub，拓樸以 design-draft §6 為準，再套 clarify。

---

## 3. 產品範圍

### Goals（MVP）

- G1. Qoder 問一句，能在剛 build 的 app 上逐步畫箭頭，人從頭走到尾完成 **create a project**。**約束**  
- G2. 每步綁最新 snapshot 的 `uid`，模型不准寫 CSS selector。**約束**  
- G3. 完成由程式看 DOM／網址／Next，不問模型、不等 HTTP。**約束 + clarified**  
- G4. 標準 MCP stdio 接到 Qoder；ShowMe 內無 LLM。**約束**  

### Non-Goals（MVP 不做）

- 第五個 MCP tool、`wait_for_user`、pending 輪詢（`等待使用者.feature` 僅第一條 Rule 有效）  
- click / type / navigate / 任意 `evaluate` 給 agent  
- chrome-devtools-mcp、FastAPI sidecar、第二個 agent／controller  
- 資料庫、queue、多服務、K8s  
- `off_script`、Not this one、SHOW runtime、evidence log、just do it（§15）  
- 任意網站 extension、多 tab、iframe、shadow DOM、canvas、登入牆  
- 頁內聊天框（入口是 Qoder）  
- 為正式站或 150 個元素以外的規模預留架構  

---

## 4. 現況基線

**程式碼觀察（2026-08-29，repo root `hackathonQoder/`）：**

| 路徑 | 狀態 |
|---|---|
| `docs/spec/**` | 規格與 prompt 存在 |
| `docs/design/showme.md` | Canonical design |
| `docs/plan/` | 存在；`dev-prompts/phase0829.md` **不讀** |
| `showme/`、`overlay/overlay.js`、`pyproject.toml` | 高階骨架（tool body 仍 `not_implemented`） |
| `demo-app/` | **不存在**（Qoder 產出，非本 repo MVP） |

目標切分（design-draft §6.6 + 官方 MCP `uv` 專案：根目錄 `pyproject.toml`、stdio `mcp.run`）：

```text
hackathonQoder/
├── pyproject.toml            uv / mcp[cli] / playwright；script：showme
├── showme/                   人員 A：MCPServer + 四 tool
│   ├── __main__.py           python -m showme → stdio
│   └── server.py
├── overlay/                  人員 B：固定 overlay.js（非 AI 產生）
│   └── overlay.js
├── tests/                    後補
├── docs/
└── demo-app/                 不在本 repo 實作；活動前 Qoder 產出 :3000
```

官方入門常用根目錄單一 `server.py`。本 repo 仍把 Python 放 `showme/`、JS 放 `overlay/`，對齊 A/B 目錄與 Playwright `add_init_script` 路徑。不採用 `src/`、不拆 tools/resources/prompts（四個 tool 不夠拆）。

---

## 5. 目標架構與相依方向

**約束：** 單向相依。沒有反向呼叫、沒有頁面打 HTTP 回 ShowMe。

```text
Qoder Agent
    │  MCP stdio（server 名稱 showme）
    │  tools: start_tutorial · inspect_page · show_step · end_tutorial
    ▼
ShowMe Python（process 記憶體：至多一個 Session）
    │  Playwright：launch / goto / add_init_script / expose_function / evaluate
    ▼
Chrome（ShowMe 啟動，headed）
    │  目標 app（通常 localhost:3000）
    │  overlay.js → window.__showme
    │
    └── __showme_emit(event) ──expose_function──▶ Python 等待 Future
```

| 模組（規劃） | 職責 | 主責 | 不可做 |
|---|---|---|---|
| `showme/` | 四工具、狀態機、uid 驗證、阻塞等待、timeout、濃縮 page 組裝、錯誤欄 | 人員 A | 操作頁面、呼叫模型 |
| `overlay/` | DOM 走訪、寫 `data-showme-uid`、Driver.js 高亮、完成觀察、emit | 人員 B | 替使用者 submit |
| Playwright | 瀏覽器生命週期與 JS 橋 | 人員 A | 不當 MCP tool 暴露給 agent |
| Qoder Agent | 規劃、挑 uid、寫說明 | S9 兩人；MCP 設定歸 A | 驅動等待、操作頁面 |
| `demo-app/` | 被教的網站 | 人員 B 確認可教（Qoder 產出） | 非本 repo MVP 實作範圍 |

**design：** Python 3.12、官方 `mcp` 的 `MCPServer` + `run(transport="stdio")`（或 `run_stdio_async`）、Playwright **async** API（tool handler 已是 async）。  
否決：FastMCP 另套一層（現行 SDK 的高階伺服器就是 `MCPServer`，見 [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/get-started/first-steps)）；否決 sync Playwright（會卡住 asyncio MCP）。

**design：** Overlay 用 vanilla JS + Driver.js（MIT），檔案放 `overlay/`，由 `add_init_script(path=...)` 注入。否決：自寫高亮以節省依賴——5 小時內 Driver.js 夠 demo（D7）。

**design：** `page.expose_function("__showme_emit", callback)`。官方行為：在 page 的 `window` 上掛名、回傳 Promise、**跨導航仍在**（[Page.expose_function](https://playwright.dev/python/docs/api/class-page#page-expose-function)）。`browser_context.add_init_script` 在每次導航、document 腳本之前執行（[BrowserContext.add_init_script](https://playwright.dev/python/docs/api/class-browsercontext)）。否決：頁面 `fetch` 到 sidecar。

**design：** `session_id` 沿用規格舉例形如 `s_8f2a`；產生演算法不鎖定（例如固定前綴 + 短 hex）。同一 process 同時只有一個有效 id。

**design：** `next_action` 沿用 draft 舉例字串，**不是** `.feature` 驗收字。

---

## 6. 端到端流程

Happy path（demo：create a project）：

1. 人在 Qoder 說要用 ShowMe 教 create a project。  
2. Agent 呼叫 `start_tutorial(url, goal)` → Chrome 開頁、注入 overlay、回 `s1-*` snapshot。**clarified：** goal 可空。  
3. Agent **心中**有一條大綱（約 3–8 步，例如 New Project → 填名稱 → Create）。這不是 MCP 存的步驟表，也不是一開始就排好的 uid list。  
4. 只從 **目前這份** `page.elements` 挑一個 `uid`，呼叫 `show_step`。驗證 uid → 畫 overlay → **阻塞**直到完成或 timeout → 回 `event` + **新 page**（snapshot# +1，uid 變成 `s2-*`）。  
5. 大綱不變；**uid 必須重挑**。重複 4，直到畫面看起來目標達成。舊 snapshot 的 uid 不准再用。  
6. `end_tutorial(session_id, summary)` → 清 overlay、固定 banner、刪 Session。**clarified：** summary 不進橫幅。

兩層（**design**，給 agent 用法，不是新 tool）：

| | 誰有 | 何時定 |
|---|---|---|
| 大綱 | 只在 Qoder 腦子裡 | `start` 後大致一次（目標路線） |
| 這一小步的 uid / instruction | 每次 `show_step` 前 | 看最新 page 才選 |

`inspect_page`：READY 時重拍、不畫箭頭、snapshot# +1；uid 對不上或頁變了就重看，不要死守第一張清單。

覆蓋：場次還在時再 `start_tutorial` → 同 `session_id`、新 goal、重開 url、`steps_shown=0`、READY。**clarified**

---

## 7. MCP tool 契約

**約束：** Server 名稱 `showme`。Qoder 全名 `mcp__showme__<tool>`。只有下列四個工具。

**clarified：** 失敗不丟 MCP 例外。官方 SDK 對「handler 丟例外」會把 tool result 標成 `is_error`（[handling-errors](https://py.sdk.modelcontextprotocol.io/servers/handling-errors)）。因此 handler **return dict**，`error` 非空 = 規格上的「操作失敗」；MCP 呼叫仍成功。

`MCPServer(name="showme", instructions=<SHOW protocol>)`。instructions 內容採 design-draft §7.5 意旨（教、不代做、一次一步、uid 來自最新 page），不是驗收字串。

### 7.1 `start_tutorial(url: str, goal: str) → TutorialStart`

| | |
|---|---|
| 前置 | 無（無 Session 則新建；有則覆蓋）。**clarified** |
| 成功 | `error=""`；`session_id`、`goal`（可空）、`page`、`next_action` |
| 失敗 | `error=navigation_failed`（`page.goto` 因連不上／逾時／無效 URL 丟錯）。**clarified：** 不檢查 host。HTTP 404/500 仍算導航成功（Playwright `goto` 不因 4xx/5xx 丟錯，見 [page.goto](https://playwright.dev/python/docs/api/class-page)） |
| Page | snapshot# 從 **1** 起算（含覆蓋）。elements ≤150、testid 鍵必在 |

覆蓋時：**design：** 關掉進行中的完成觀察、`clear()` overlay、同一 Browser/Page 若仍活著則 `goto` 新 url；死掉則重 launch。`steps_shown=0`，state=READY。

### 7.2 `inspect_page(session_id: str) → Page + error`

規格實體是 Page；失敗通道與其他工具相同，故回傳加 `error`。**design**（對齊 clarified 錯誤欄，非新產品能力）

| | |
|---|---|
| 前置 | Session 存在且 **READY**。**clarified** |
| 成功 | 新鮮 page；snapshot# +1；不呼叫 `__showme.show` |
| 失敗 | 無 Session：`session_not_found`。SHOWING／非 READY：見第 17 節 **open** |

### 7.3 `show_step(session_id, uid, instruction, kind, step_index, step_total, expect_text="", timeout_s=120) → StepResult`

| | |
|---|---|
| 前置 | Session 存在且 READY；否則見下表 |
| `kind` | `click`／`input`／`select`／`observe`；其他字串**視為 observe**。**clarified** |
| `expect_text` | 視為 observe 後若空 → 立即失敗 `expect_text_required`（**不畫、steps_shown 不加**）。**clarified** |
| `timeout_s` | 未傳、0、負值 → 120。**clarified** |
| 成功畫出 | uid ∈ 最新 elements → `steps_shown+1`（含 stuck 後同 uid）→ state=SHOWING → 阻塞 |
| 完成回傳 | `event` ∈ {`step_done`,`stuck`,`timeout`}；MVP 不發 `off_script`。`signal` 可空、不驗收。附新 page（snapshot# +1）。state=READY |
| 失敗（不畫） | 見第 13 節；uid 失敗仍附新鮮 page 且 snapshot# +1 |

並發：SHOWING 時第二個 `show_step` → `show_step_in_progress`（不取消第一次）。**clarified**

`max_steps=12`：`steps_shown >= 12` 時失敗 `max_steps_exceeded`。**clarified**

### 7.4 `end_tutorial(session_id: str, summary: str) → {ok, error}`

| | |
|---|---|
| 前置 | Session 存在且 READY |
| 成功 | `ok=true`，`error=""`；`evaluate(__showme.clear)` + `__showme.done("✅ Done — you created a project")`；**忽略 summary**；刪除 Session（瀏覽器可關）。**clarified** |
| 失敗 | 無 Session：`session_not_found`。非 READY：第 17 節 **open** |

---

## 8. Session 狀態機

**clarified：** 記憶體裡至多一個 Session。沒有 ttl。沒有長期 DONE。

實務狀態：

```text
（無 Session）──start_tutorial 成功──▶ READY
READY ──show_step 畫出──▶ SHOWING ──完成或 timeout──▶ READY
READY ──end_tutorial 成功──▶ （刪除，無 Session）
READY 或 SHOWING ──start_tutorial 成功──▶ READY（同 session_id，覆蓋）
SHOWING ──inspect / end──▶ 失敗（error 字串見 open）
SHOWING ──第二個 show_step──▶ show_step_in_progress（第一次繼續等）
```

erm 的 IDLE = **沒有 Session 物件**，不要真的存一筆 IDLE 列。無物件時 inspect／show／end 皆 `session_not_found`。

常數：**clarified** `max_steps=12`，預設 `timeout_s=120`。

`start_tutorial` 在 SHOWING 覆蓋時，已阻塞的那次 `show_step` 如何收尾 → 第 17 節 **open**。

---

## 9. 資料模型（記憶體，不是 DB）

對應 `docs/spec/erm.dbml`。ShowMe process 內一個 `Session` dataclass 即可。

| 規格 Table | 實作位置 | 備註 |
|---|---|---|
| Session | `showme` 單一 optional 物件 | `session_id`,`goal`,`state`,`steps_shown` + Playwright page 握把 + snapshot# 計數 + 進行中 wait Future |
| Page / PageElement | `latest_page` dict | 只留最新一份 |
| Step | SHOWING 時的進行中參數 | 不存歷史步驟列表 |
| Event | 當下 callback 資料 | 主鍵語意：同 `(session_id, ts)` 後至丟棄；不落盤。**clarified** |
| TutorialStart / StepResult | tool 回傳 dict | 非持久化 |

PageElement：`uid`,`role`,`name`,`testid`（必有鍵）。  
Event.kind（overlay）：`step_done` \| `stuck` \| `off_script`（MVP 不發最後一個）。  
StepResult.event：另含 `timeout`。**clarified** 分開建模。

---

## 10. Snapshot 與 uid

**clarified**

- 角色白名單：button、link、textbox、checkbox、radio、combobox、menuitem、tab、heading、alert。  
- DOM 走訪順序取前 **150**；多於 150 → 丟掉後面、`truncated=true`；≤150 → `truncated=false`。不分 viewport。  
- `name`：a11y name；沒有則 `""`，元素仍列出。  
- `testid`：`data-testid` 或 `""`。  
- `uid`：`s{snapshot#}-{index}`。index 為本次清單中的序（設計：**design** 用 1-based 與規格舉例 `s1-4` 對齊即可；不要求 index 連續對應 DOM 全域第 n 個）。  
- 計數器在 **Python Session**（reload 後 overlay 重跑也不丟世代）：  
  - `start_tutorial` 成功：snapshot# = 1  
  - `inspect_page` 成功：+1  
  - `show_step` 回傳且附 page（含 `uid_not_in_snapshot`）：+1  

Walker 在 overlay：`__showme.snapshot(snapshotNumber)` 寫 `data-showme-uid` 並回傳 elements。Python 組 `url`（`page.url`）、`title`（`page.title()`）。

驗證：`uid` 必須等於 **latest_page.elements** 某筆。失敗：先拍新鮮 page（+1），`error=uid_not_in_snapshot`，不畫、`steps_shown` 不加。**clarified**

---

## 11. 完成判定

判定在 **overlay.js**；Python 只等第一個 `__showme_emit` 或本地 timer。完成只看 StepResult.`event`。**clarified**

每步 overlay **只 emit 一次**。同 ts 後至丟棄。**clarified**

| kind | overlay 何時 emit `step_done` |
|---|---|
| click | 目標從 DOM 移除，或判定為隱藏，或 `location.href` 相對本步開始時改變，或按 Next |
| input | 目標 `value.length > 0` 且發生 `blur` 或 `change`，或按 Next |
| select | 目標 `change`，或按 Next（「任何 kind Next」） |
| observe（含非法 kind 轉入） | 頁面文字出現 `expect_text`，或按 Next |

**不是** click 完成條件：DOM mutation 次數、任何 HTTP／`waitForResponse`。**clarified**  
MutationObserver **仍可用**於「目標被拿掉／隱藏」，不是計次。**design**

**隱藏（design，規格未給演算法）：** 節點不在 document，或 `display:none`／`visibility:hidden`，或 `aria-hidden="true"`。不做 IntersectionObserver 進視窗判斷（與「不分 viewport」一致，避免兩套幾何）。

**URL（design）：** 開始觀察時記下 `location.href`；`popstate`、包裝 `history.pushState`／`replaceState`、以及 `hashchange`。比到字串不相等即完成。不等待特定 path 白名單（MVP 無 off_script）。

**I'm stuck：** emit `kind=stuck` → StepResult.`event=stuck`。Agent 應同 uid 再 `show_step`（會再 +1）。**clarified**

**timeout：** Python 在 `elapsed_s >= timeout_s` 時結束等待，**不**等 overlay emit。同一瞬間 Next 與截止：仍 `timeout`。**clarified** 然後 `clear()` 觀察器、拍 page、state=READY。

`off_script`：stretch，MVP overlay 不發。偏離腳本會落到 timeout 或下一步 `uid_not_in_snapshot`。

---

## 12. Overlay 與 `__showme_emit` 邊界

`window.__showme`（頁面，規劃檔 `overlay/overlay.js`）：

| 方法 | 職責 |
|---|---|
| `snapshot(n)` | 走訪、寫 uid、回傳 elements + 是否超過 150 |
| `show({uid, instruction, kind, index, total, expect})` | `clear` → 找 `[data-showme-uid]` → scrollIntoView → Driver.js highlight → popover（說明、Step k/N、Next、I'm stuck）→ `observe(kind)` |
| `observe(kind)` | 依第 11 節掛 listener；第一個合格訊號呼叫 emit |
| `clear()` | 拆 Driver、移除 listener、不拆 `__showme` 本身 |
| `done(text)` | 完成 banner；文案由 Python 傳入固定句 |

Python：

- launch headed Chromium／Chrome、`goto`、context `add_init_script`、`expose_function`  
- 驗證 uid、`evaluate` show／snapshot／clear／done  
- 擁有 Session、steps_shown、timeout timer、error 欄  
- **不**在 Python 做 click／fill  

Driver.js 放 `overlay/` 第三方檔或 CDN。**design：** hackathon 用官方打包／單檔 vendor，不自建 bundler。若 CSP 擋 CDN，改成本地檔（demo app 是自己的 localhost，通常可注入 init script，不經 app CSP 限制外部 script 的同一路徑——init script 由 Playwright 注入，不需 app 改 CSP）。

---

## 13. 錯誤與異常語意

**已定案（clarified）——只能用這些當驗收錯誤碼：**

| error | 何時 |
|---|---|
| `navigation_failed` | `start_tutorial` 開不了 url |
| `session_not_found` | 無 Session（含結束後）時 inspect／show／end |
| `max_steps_exceeded` | `steps_shown >= 12` 仍 `show_step` |
| `uid_not_in_snapshot` | uid 不在最新 snapshot；附新 page |
| `expect_text_required` | observe（含非法 kind）且 expect_text 空 |
| `show_step_in_progress` | SHOWING 時第二個 `show_step` |

成功時 `error` 為空字串。

**不是錯誤碼：** `timeout`、`stuck`、`step_done` 是 `event`。

**不得假裝已定：** SHOWING 時 `inspect_page`／`end_tutorial` 的 error 字串（第 17 節）。

---

## 14. 測試策略

來源：`docs/spec/features/*.feature`。統計（本檔撰寫時）：

| Feature | Rule 數 | 本設計 |
|---|---|---|
| 開始教學 | 13 | 全覆蓋 |
| 檢查頁面 | 6 | 全覆蓋；非 READY 的 Example 仍 `#TODO` |
| 顯示步驟 | 30 | 29 條 MVP；`off_script` 標 Non-Goal |
| 結束教學 | 6 | 全覆蓋；非 READY 的 Example 仍 `#TODO` |
| 等待使用者 | 4 | **僅**「MVP 不提供 wait_for_user」；其餘 3 條 Non-Goal |

總 Rule 59；MVP 負責 13+6+29+6+1 = **55**；Non-Goal 4。

原則：

- 有 Example 的 Rule：行為測試對那張表。  
- 只有 `#TODO` 的 Rule：測負責層的不變條件，**不要發明規格沒有的例子當需求**。  
- 不把 `signal` 當 Then。  
- 不啟動真實 MCP 客戶端也可先測：純函數（截斷 150、uid 格式、timeout_s 正規化、kind 正規化）+ overlay 在 Playwright 測頁的 fixture。

建議層次：

1. **單元：** snapshot#、150 截斷、`timeout_s`、非法 kind→observe、error 欄組裝  
2. **overlay + Playwright：** 高亮、Next／stuck emit 一次、click 換 URL、不因單純 mutation 完成  
3. **MCP 契約（可後做）：** stdio 列出四工具、無 `wait_for_user`、例外不會變成 `is_error`  

---

## 15. 交付切片（約 5 小時，DAG）

每一片結束必須能**手動看到**結果。不做 stretch。

```text
S0 活動前（非切片時數）
   demo-app :3000 已跑（Qoder 產出）
        │
        ▼
S1  Playwright 開 headed Chrome + goto 指定 url
        │  驗證：視窗出現目標頁
        ▼
S2  add_init_script(overlay.js) + expose_function
        │  驗證：reload 後 window.__showme 仍在；頁面能呼叫 emit 印到 Python
        ▼
S3  snapshot walker：uid、150、testid=""
        │  驗證：console／假 tool 印出 s1-* 清單
        ▼
S4  Driver.js 對一個 uid 高亮 + Next / I'm stuck
        │  驗證：人眼看到箭頭；點 Next 有一次 emit
        ▼
S5  MCPServer stdio：start_tutorial 真走 S1–S3
        │  驗證：Qoder 或 MCP inspector 看到 TutorialStart
        ▼
S6  inspect_page + uid 驗證失敗回新鮮 page
        │
        ▼
S7  show_step 阻塞 + click/input/Next/stuck/timeout + 狀態機
        │  驗證：人做完 create a project 中的一步，tool 才回來
        ▼
S8  end_tutorial 固定 banner + 刪 Session
        │  驗證：再 end → session_not_found
        ▼
S9  端到端：Qoder「教我 create a project」走到 banner
```

相依：S1→S2→S3 與 S4 可在 S2 後分頭；S5 依賴 S1–S3；S7 依賴 S4+S5；S9 依賴 S7+S8。  
不要先做：off_script、wait_for_user、connect_over_cdp、viewport 優先截斷。

切片 × 人員（細節見 15.1）：

| 切片 | 主責 | 搭配 |
|---|---|---|
| S0 | 人員 B | 人員 A 確認 url 能開 |
| S1 | 人員 A | — |
| S2 | **兩人一起鎖定介面**（約 20 分鐘）後再分頭 | A：expose_function；B：init script 骨架 |
| S3 | 人員 B | 人員 A 把回傳組成 Page |
| S4 | 人員 B | — |
| S5 | 人員 A | 呼叫 B 的 snapshot |
| S6 | 人員 A | — |
| S7 | 人員 A 狀態機 + 人員 B 完成觀察 | 對接 `__showme_emit` |
| S8 | 人員 A | 人員 B 實作 `clear`／`done` |
| S9 | **兩人一起** | — |

### 15.1 兩人分工

切在模組邊界，不要兩人都改同一份 Python 狀態機。對齊 design-draft §13.2 的 A／B，並套現行規格。名字可自行填上。

| | **人員 A — ShowMe / Python** | **人員 B — overlay / 頁面** |
|---|---|---|
| 目錄（規劃） | `showme/` | `overlay/`；盯 `demo-app/` 能不能教 |
| 一句話 | MCP 四工具、Session、錯誤欄、阻塞等待、開瀏覽器 | 畫箭頭、掃 DOM、看人做完了沒、emit 一次事件 |
| 對應負責層 | T、S、N，以及 Page 組裝 | O、W 的 DOM 走訪 |

#### 人員 A 負責

- `pyproject.toml`、Python 3.12、`mcp`、Playwright async、stdio 進入點 `MCPServer(name="showme")`。
- 啟動 headed Chrome、`goto`、`add_init_script` 路徑、`expose_function("__showme_emit")`、`navigation_failed`。
- 四工具契約與 `error` 欄（不丟 MCP 例外）：`start_tutorial`、`inspect_page`、`show_step`、`end_tutorial`。
- Session：單一場次、覆蓋 start、READY／SHOWING、刪除後 `session_not_found`、`steps_shown`／`max_steps=12`、`show_step_in_progress`。
- `timeout_s` 正規化、Python 側 `elapsed_s >= timeout_s` → `event=timeout`。
- 擁有 **snapshot#**；呼叫 B 的 `snapshot(n)` 後補 `url`／`title`、截斷旗標。
- uid 驗證、`uid_not_in_snapshot` 附新鮮 page；非法 kind→observe、`expect_text_required`。
- `show_step` **阻塞**等到 emit 或 timeout；SHOW protocol `instructions`／tool docstring。
- Qoder 掛 MCP stdio、量 Request Timeout（第 16 節）。S9 主操 agent 對話。

**不要做：** Driver.js 樣式、完成觀察 listener、改 demo-app 畫面。

#### 人員 B 負責

- `overlay/overlay.js` + Driver.js（MIT vendor）。
- `__showme.snapshot(n)`：白名單角色、DOM 順序 150、`data-showme-uid`、`testid` 鍵、空 `name`。
- `__showme.show`：高亮、popover（說明、Step k/N、Next、I'm stuck）、`scrollIntoView`。
- `__showme.observe`：第 11 節完成條件（移除／隱藏／URL／input／select／expect_text／Next／stuck）。**不**數 mutation、**不**等 HTTP。每步只 `__showme_emit` 一次。
- `__showme.clear`、`__showme.done("✅ Done — you created a project")`（文案由 A 傳入）。
- S0：確認 demo-app `:3000` 的 create-project 走得完、關鍵鈕有 a11y name（app 由 Qoder 產出，B 負責「能不能被教」）。
- 用靜態 HTML fixture 測 overlay，不必等 MCP 骨架。

**不要做：** Session 狀態機、MCP tool 簽名、`error` 碼表、自己 `launch` 第二個瀏覽器當正式路徑。

#### 接縫（S2 必須先寫死，否則合不起來）

兩人先約好，再分頭寫：

```text
window.__showme.snapshot(snapshotNumber) → { elements, truncated }
window.__showme.show({ uid, instruction, kind, index, total, expect })
window.__showme.clear()
window.__showme.done(text)
window.__showme_emit({ kind, url, ts, signal? })
  kind: step_done | stuck     （MVP 不發 off_script）
```

- `elements[]`：`uid`、`role`、`name`、`testid`（必有鍵）。  
- A 不解析 CSS selector；B 不決定 snapshot#。  
- emit 的 `kind` 是 overlay 事件；A 把 timeout 寫在 StepResult.`event`，不叫 B 發 timeout。

#### 不要搶的檔

| 預設擁有者 | 路徑 |
|---|---|
| A | `showme/**` |
| B | `overlay/**` |
| 兩人碰 S2／S9 才改 | 本 design 的介面段落；Qoder MCP 設定 |

Open question 1–2（SHOWING 時 inspect／end、覆蓋 start 時卡住的 show_step）歸 **A** 先用第 17 節傾向實作。Open question 3（何謂隱藏）歸 **B**，採用第 11 節最小集合。

---

## 16. Demo 當日風險（design-draft §14，不是 tool 契約）

| 風險 | 處理（營運，不改規格） |
|---|---|
| Qoder 對長時間阻塞 tool 的 timeout | 活動前用 sleep tool 量；IDE 調高 Request Timeout。**MVP 仍不實作 wait_for_user**；真的擋死再另開規格，不在本檔偷加第五個 tool |
| 每個 MCP tool 要人工確認 | 把 `mcp__showme__*` 加進 allow list |
| Chrome vs Chromium | Playwright `channel="chrome"` 優先，沒有再 Chromium；屬啟動參數，不是 API 契約 |
| IDE vs CLI | 擇一當 demo 主場 |
| headed 視窗被擋 | 不要用 headless 當教學（人必須看到箭頭） |

---

## 17. 假設、限制與 open questions

### 假設（不是規格）

- Demo 當日 `:3000` 已有可點的 create-project 流程與還可以的 a11y name。  
- 單一 tab、無 iframe。  
- 實作者會裝 Python 3.12、`mcp`、`playwright` 並 `playwright install`。

### 限制

- 本階段未執行安裝或瀏覽器。API 名稱來自官方文件查證，不是已跑通的程式。  
- `.feature` 仍有 `#TODO` Example：決策在，例子不在。  
- C1 詞彙表檔：Discovery 已略，本 design 不補產品能力。

### Open questions（`.clarify/data` 與 `features` 未決資料夾為空；下列是**規格空隙**，clarify 26 題已全部 resolved）

無未搬移的 clarify 檔。

設計時新發現、**不得寫成已確認**：

1. **SHOWING 時 `inspect_page`／`end_tutorial` 的 `error` 字串**  
   規格：操作失敗；已定案碼沒有 `not_ready`。  
   影響：檢查頁面、結束教學負責層。  
   傾向（非決策）：先回 `show_step_in_progress`，避免新碼；驗收 Example 仍是 `#TODO`。

2. **SHOWING 時 `start_tutorial` 覆蓋，已阻塞的 `show_step` 如何結束**  
   規格：start 隨時可覆蓋；未寫那次 MCP 回傳。  
   影響：狀態機、asyncio Future。  
   傾向（非決策）：取消等待，該次 `show_step` 回傳 `event=timeout`（已有 event，不必新 error）；demo 避開此交錯。

3. **「隱藏」的像素級定義**  
   規格只說隱藏。第 11 節 **design** 給了最小集合；若 demo 用 `opacity:0` 而未移除，可能漏判 → 人按 Next。

沒有其他新發現的產品歧義。非法 kind、signal、testid、timeout 相等、Event 主鍵、banner、空 goal 均已 clarified，不重問。

---

## 18. Spec-to-Design 規則覆蓋

負責層縮寫：T=MCP tool handler，S=Session 狀態機，N=Playwright 導航／browser，W=snapshot walker（overlay+Python 組裝），O=overlay 完成觀察，X=Non-Goal。

### 開始教學（13）

| Rule | 層 |
|---|---|
| 成功開始後回傳的 goal 等於傳入的 goal | T |
| 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1 | T+W |
| 成功開始後 session 狀態為 READY | S |
| 同一時間只允許一個教學場次，再次開始…覆蓋 | S+N |
| goal 為空字串時仍成功開始 | T |
| 開始教學不因 url 不是 localhost 而操作失敗 | N |
| 目標 url 無法開啟時… navigation_failed | N+T |
| 回傳的 page.elements 只含互動角色與 heading 與 alert | W |
| page.elements 硬上限 150… | W |
| testid 鍵永遠存在… | W |
| 沒有 a11y name… name 為空字串 | W |
| 啟動或重用 Chrome 並開啟傳入的 url | N |
| 注入 overlay.js | N |

### 檢查頁面（6）

| Rule | 層 |
|---|---|
| 成功時回傳新鮮的濃縮 page | T+W |
| session 狀態不是 READY 時操作失敗 | S（error 字串 open） |
| 成功時 uid snapshot# 比上一份加一 | W |
| session 不存在… session_not_found | S+T |
| 呼叫後不畫任何 overlay 步驟 | T（不呼叫 show） |
| page.truncated 為 true 時仍回傳濃縮 page | T+W |

### 顯示步驟（30）

| Rule | 層 |
|---|---|
| 畫出 overlay 後阻塞直到使用者做完或逾時 | T+O |
| 操作失敗時寫在回傳的 error，不丟例外 | T |
| 僅在 READY 時可成功畫出 | S |
| steps_shown ≥ 12 → max_steps_exceeded | S+T |
| uid 不在最新 snapshot → uid_not_in_snapshot | T+W |
| uid 失敗回新鮮 page 且 snapshot# 加一 | W |
| session 不存在 → session_not_found | S+T |
| uid 通過後畫高亮與 popover | O |
| uid 通過後 steps_shown +1（含 stuck 重畫） | S |
| 畫出後 state=SHOWING 直到事件 | S |
| 收到事件後 READY 並回傳新 page | S+W |
| click：目標移除或隱藏 | O |
| click：URL 變更 | O |
| click：不以 mutation 次數完成 | O |
| click：不等待 HTTP | O（禁止 N 的 waitForResponse） |
| input：value>0 且 blur/change | O |
| input：Next | O |
| select：change | O |
| 非法 kind 視為 observe | T |
| observe 且 expect_text 空 → expect_text_required | T |
| observe：出現 expect_text | O |
| observe：Next | O |
| 任何 kind Next → step_done | O |
| 任何 kind I'm stuck → stuck | O |
| 完成只看 event，signal 可空 | T |
| timeout_s 未傳／0／負 → 120 | T |
| elapsed_s ≥ timeout_s → timeout | T（timer） |
| 每步一次事件；同 ts 後至丟棄 | O+T |
| 並發 show_step → show_step_in_progress | S |
| off_script 回新 page | X（stretch） |

### 結束教學（6）

| Rule | 層 |
|---|---|
| 成功結束後 ok 為 true | T |
| session 不存在 → session_not_found | S+T |
| 成功結束後刪除 Session | S |
| 狀態不是 READY 時操作失敗 | S（error 字串 open） |
| 成功結束後清掉 overlay | O via T evaluate |
| 完成 banner 固定且忽略 summary | T+O |

### 等待使用者（4）

| Rule | 層 |
|---|---|
| MVP 不提供 wait_for_user，改阻塞 show_step | X 不實作 tool；T 阻塞 |
| 尚未完成時 event 為 pending | X |
| 完成時回傳與 show_step 相同 StepResult | X |
| timeout_s 預設為 25 | X |

無人負責的 MVP Rule：**無**。

---

## 19. 實際讀取的 source inventory

**產品草稿**

- `docs/spec/draft/design-draft.md`（v0.2：§6 拓樸、§7 工具、§8–§11；**未**把 §14／§15／附錄 C 當 MVP 架構）  
- `docs/spec/draft/architecture-ascii.md`（stub）

**作用中規格**

- `docs/spec/erm.dbml`  
- `docs/spec/features/開始教學.feature`（13 Rule）  
- `docs/spec/features/檢查頁面.feature`（6）  
- `docs/spec/features/顯示步驟.feature`（31）  
- `docs/spec/features/結束教學.feature`（6）  
- `docs/spec/features/等待使用者.feature`（4）  
- `docs/spec/.clarify/overview.md`（待辦 0）  
- `docs/spec/.clarify/resolved/data/` 全部（11 檔解決記錄）  
- `docs/spec/.clarify/resolved/features/` 全部（15 檔解決記錄）  
- `docs/spec/.clarify/data/`、`features/`：空（無未搬移項）

**Repo 現況**

- root：`.gitignore`、`docs/`  
- 確認不存在：`showme/`、`overlay/`、`demo-app/`、`pyproject.toml`、`package.json`

**刻意不讀當需求**

- `docs/plan/dev-prompts/phase0829.md`

**官方 API（查證，未改產品程式碼）**

- MCP Python SDK：`MCPServer`、`@mcp.tool()`、`instructions`、stdio `run`／`run_stdio_async`；例外會變成 `is_error`  
  - https://py.sdk.modelcontextprotocol.io/get-started/first-steps  
  - https://py.sdk.modelcontextprotocol.io/servers/handling-errors  
  - https://github.com/modelcontextprotocol/python-sdk  
- Playwright Python：`page.goto`（4xx/5xx 不丟錯；連線失敗會丟）、`browser_context.add_init_script`、`page.expose_function`（跨導航仍在）  
  - https://playwright.dev/python/docs/api/class-page  
  - https://playwright.dev/python/docs/api/class-browsercontext  

**Self-review：** 無未解釋 TBD；hackathon 約束已對；55 條 MVP Rule 有負責層；規劃目錄未寫成已存在；clarified 未推翻；open 3 項未改規格；draft 舊敘述未回流；關鍵不變條件可測；未引入 FSE／Chat Room 路徑。
