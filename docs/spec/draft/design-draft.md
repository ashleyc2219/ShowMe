# ShowMe — 設計文件

**暫定名稱：** ShowMe
**狀態：** v0.2 — hackathon 建置規格（Qoder × Beta Fund · Agent Factory，2026-08-29）
**範圍：** 約 5 小時內要做什麼、刻意不做什麼，以及每個選擇為什麼這樣做。架構 ASCII 圖已併入 §6（現行 v0.2）與附錄 C（v0.1，供 §15 回收）。
**一句話：** *ShowMe is an MCP for coding agents that turns newly generated web apps into self-teaching software.*

> **AI builds it → ShowMe teaches you how to use it.**

---

## 0. TL;DR

ShowMe 是一個給 **Coding Agent（Qoder）** 用的 **MCP server**。Qoder 剛把一個 Web App 做出來、跑在 `localhost:3000`，開發者在 Qoder 聊天視窗問：「Use ShowMe to teach me how to create a project.」Qoder 透過 ShowMe 看目前頁面、在正在跑的 app 上畫出箭頭指向下一步、等使用者**自己**做完、再指向再下一步 — 一路教到完成。

核心不是「讓 AI 幫你操作網站」，而是：

> **Browser agents act for you. ShowMe teaches you.**
> **ShowMe is onboarding for software that didn't exist five minutes ago.**

三件事讓它成立：

1. **它是 coding agent 的 capability，不是另一個 agent。** 我們不做 LLM、不接自己的 model；ShowMe 以 MCP tools 的形式讓 Qoder Agent 多出「教人使用剛生成 App」的能力。建 app 的 agent 就是教 app 的 agent — 它知道自己寫了哪些 route 與 component。
2. **沒有預寫教學、網站不裝 SDK。** 步驟依當下頁面的 accessibility 結構即時產生，每一步綁到真實元素的 `uid`。
3. **Agent 教而不做，而且做不到。** ShowMe 只提供「看頁面」與「畫箭頭」的工具，沒有 click / type / navigate。

### v0.1 → v0.2 改了什麼

| | v0.1 | v0.2 |
|---|---|---|
| 定位 | 「Agent 的第四種權限模式 SHOW」 | 「讓剛生成的 App 自己教人怎麼用」 |
| 形態 | Python controller + Qoder Agent SDK + chrome-devtools-mcp | **一個 MCP server**（Qoder Agent 直接呼叫） |
| 誰在跑迴圈 | 我們的 Python controller | Qoder Agent（ShowMe 的 tool 回傳值驅動下一步） |
| 瀏覽器控制 | 串 chrome-devtools-mcp | ShowMe 內建 Playwright，自己啟動 Chrome |
| 頁面 → 後端事件 | FastAPI sidecar + `fetch()` | Playwright `expose_function`（不需要 HTTP server） |
| MVP 範圍 | 含 runtime security、evidence log、hooks、off-script recovery | **只保證一條主流程**；off-script 為 stretch；security / evidence 移到後續 |

> 2026-08-29：`docs/spec/draft/architecture-ascii.md` 的圖已併入本文件。§6 是現行拓樸；附錄 C 保留 v0.1 原文，不要當成 MVP 實作圖。

---

## 1. 痛點

Coding Agent（Qoder、Codex 這類）現在可以很快產生完整 App。問題出在下一秒：

```text
Developer:  "Build me a project management app."
                    ↓
            Coding Agent builds it
                    ↓
            localhost:3000
                    ↓
Developer:  「等等，這個東西到底怎麼用？」
            「Agent 到底做了哪些功能？」
            「我要怎麼 create project？」
```

Vibe coding 越普及，這個落差越大：

> **開發速度可能比人理解自己軟體的速度還快。**

| 誰 | 現況痛點 |
|---|---|
| **剛用 agent 做出 app 的開發者（主要）** | 不清楚 agent 產出了哪些流程；想走一遍「X 是怎麼運作的」，但不想讀程式碼、也不想看 agent 的長篇摘要 |
| 任何網頁 app 的新使用者 | 「我要怎麼…？」只能去文件、開支援單，或交給會「替他做完」的 agent（所以永遠學不會） |
| 產品導覽供應商的客戶 | 內容必須手寫或錄製；每次改版 selector 就壞；還要求網站安裝 SDK |

共同問題：**引導要嘛是手寫且脆弱，要嘛被「會操作、但不教學」的 agent 取代。** 對剛生成的軟體來說，兩者都不存在 — 沒人寫過教學，也沒人裝 SDK。

---

## 2. 產品定義

> **ShowMe is an MCP for coding agents that turns newly generated web apps into self-teaching software.**

- **輸入：** 一個正在跑的網頁 app（MVP：`localhost`）、使用者在 Qoder 裡問的一句自然語言問題。
- **輸出：** 頁內 overlay（高亮 + 箭頭 + 一句說明 + Next / I'm stuck），依即時頁面狀態逐步前進，直到使用者自己完成。
- **保證：** agent 只讀、只畫；ShowMe 沒有任何點擊、輸入、導航或送出表單的工具。

Demo 開場白：

> *Coding agents can build software in minutes. But sometimes even the developer doesn't know how the generated product works. ShowMe lets the app teach you itself.*

---

## 3. 定位：跟誰不一樣

### 3.1 vs. Browser Agent — act 還是 teach

```text
Browser Agent                         ShowMe
─────────────                         ──────
User: "Create a project for me."      User: "Show me how to create a project."

AI:  click                            AI:  「Click here」→ Human clicks
     ↓ type                                「Enter the name here」→ Human types
     ↓ submit                               「Now click Create」→ Human clicks
     Done                                   Human learned it
```

> **Browser agents act for you. ShowMe teaches you.**

### 3.2 vs. WalkMe / Appcues / Frigade — 箭頭不是創新點

既有 onboarding 工具本來就會 highlight、tooltip、箭頭、step-by-step。真正的差別在**對象與時機**：

```text
傳統 Product Adoption                 ShowMe
────────────────────                  ──────
成熟 SaaS                             Coding Agent
  ↓                                     ↓
公司安裝 onboarding SDK               剛剛生成的 App，跑在 localhost
  ↓                                     ↓
人工設定 / 錄製 guidance              ShowMe 立刻理解 running UI
  ↓                                     ↓
教 customers                          Developer 馬上可以問：
                                      "How does this thing work?"
```

> **ShowMe is onboarding for software that didn't exist five minutes ago.**

### 3.3 為什麼是 coding agent 的 MCP，而不是獨立產品

- Qoder 已經有模型、有 repo context、有聊天介面；缺的只是「教人使用 running app」這個 capability。Qoder 官方支援 custom MCP server，加進去之後它提供的 tools 就直接成為 Agent 可用的能力（見附錄 A）。
- **建 app 的 agent 就是教 app 的 agent。** 它剛寫完 routes / components，規劃「create a project 要幾步」時天然有 repo 知識 — 這是 Frigade 這類外掛永遠拿不到的 context。但每一步指向哪個元素，仍必須從**正在跑的頁面**綁定（程式碼 ≠ 畫面上實際渲染的東西）。
- 不做自己的 LLM、不把自己的 model 接到 Qoder 的 model：省掉一整層 orchestration，也讓「教學」跟 Qoder 的其他能力（改 code、跑測試）自然接在同一個對話裡。

### 3.4 既有方案對照

| 類別 | 例子 | 他們做什麼 | ShowMe 的差異 |
|---|---|---|---|
| 瀏覽器 agent | Gemini in Chrome、Claude for Chrome、ChatGPT Agent、Comet、Browser Use | 替使用者操作 | 教學而非操作；根本沒有操作類工具 |
| 瀏覽器 MCP | Playwright MCP、chrome-devtools-mcp | 給 agent 一雙「手」 | ShowMe 給 agent 一支「指揮棒」：只能看與指 |
| Digital adoption | WalkMe、Appcues、Userlane、**Frigade AI** | 網站裝 SDK；內容手寫／錄製，或在其 SDK 內產生 | 網站零安裝；for 剛生成的 app；步驟即時綁到 a11y `uid` |
| Tour 函式庫 | Driver.js、Shepherd.js、Intro.js | Overlay 原語 | 我們用 Driver.js 當 renderer，它不是產品本身 |

Frigade 仍是最接近的產品（「隨產品演進自動保持最新」打的是同一種脆弱性）。我們的楔子：(a) 網站端零安裝，(b) 接在 coding agent 上、app 一生成就能用，(c) 教的人知道程式碼。

---

## 4. 使用流程（end-to-end）

**Step 1 — 用 Qoder build app。**

```text
User → Qoder: "Build me a project management website."
Qoder: creates frontend/backend → runs app → http://localhost:3000
```

**Step 2 — Qoder 接上 ShowMe MCP。**

```text
Qoder Agent ──MCP (stdio)──▶ ShowMe ──▶ Chrome ──▶ localhost:3000
```

一行設定（附錄 A）。之後 ShowMe 的 tools 出現在 Qoder 的工具清單裡。

**Step 3 — Developer 問 Qoder。**

> "Use ShowMe to teach me how to create a project."

Qoder 呼叫 `start_tutorial(url="http://localhost:3000", goal="create a project")`，拿到目前頁面的結構。

**Step 4 — ShowMe 畫、人做、ShowMe 再看。**

```text
Dashboard                                  Project Name: [____________]
                                                         ↑
[New Project]  ◀── Step 1 / 4               Step 2 / 4 ── Enter a project name
     ↑
  Click here            ──Human clicks──▶            ──Human types──▶  Step 3 → Step 4 → ✅
```

Qoder 每次呼叫 `show_step(uid, instruction, …)`：ShowMe 畫箭頭、**阻塞等待**使用者做完、回傳新的頁面狀態。Qoder 依新狀態決定下一步，最後呼叫 `end_tutorial()`。

---

## 5. 目標與非目標（MVP）

### 目標

- G1. 從 Qoder 聊天視窗問一句「how do I …」，就能在 Qoder 剛 build 的 localhost app 上產生逐步頁內導覽，由人類從頭走到尾完成。
- G2. 每一步透過頁面結構的 `uid` 綁到真實元素 — 絕不使用 LLM 寫出的 CSS selector；ShowMe 拒絕不在最新 snapshot 中的 `uid`。
- G3. 用 DOM / URL 訊號判斷步驟完成，而不是問模型；**Next** 是逃生口。
- G4. 整條流程走標準 MCP 設定接上 Qoder；不改 Qoder、不做自己的 agent、不做自己的 LLM。
- G5. 4 分鐘內可 demo；換一個不同的問題不用改任何程式碼（證明不是預寫腳本）。

### Stretch（若主流程 15:15 前穩定）

- S1. **Off-script 恢復：** 使用者點錯 → overlay 回報 `off_script` → Qoder 依當前頁面重新規劃剩餘步驟，繼續帶。
- S2. 「Not this one?」— 兩個候選元素時，不呼叫模型就切到替代。

### 非目標（MVP 刻意不做）

- Runtime security（tool deny list、`PreToolUse` hook、`evaluate_script` 模板守護）、evidence log、permission mode 論述 — 移到 §15。
- 「just do it for me」→ 被拒絕 → 降級成 SHOW 的 pitch 時刻 — 移到 §15。
- 正式站點／第三方網站（需要 extension；MVP 是 `localhost` + ShowMe 自己啟動的 Chrome）。
- 多 tab、iframe、大量 shadow DOM、canvas UI；登入牆、CAPTCHA、MFA。
- 頁內問題輸入框 — 入口就是 Qoder 聊天視窗。
- Overlay 像素級精準樣式（Driver.js 預設即可）；跨瀏覽器（僅 Chrome）。

---

## 6. 架構

> Qoder Agent 擁有對話迴圈；ShowMe 只做決定性的看／畫／等；使用者自己操作。

```text
Qoder：「Use ShowMe to teach me how to create a project.」
                         │
                         ▼
              讀頁面 → 指向下一步 → 等使用者做完
              （ShowMe 從不 click / fill / navigate）
```

### 6.0 系統情境（誰跟誰說話）

```text
                 「Use ShowMe to teach me how to create a project.」
                                 │
                                 ▼
┌──────────┐   自己點、自己打字    ┌──────────────────────────────────┐
│ Developer │ ──────────────────▶ │  Demo app  :3000                  │
│           │                     │  + overlay.js（高亮 / 箭頭 / Next）│
│           │ ◀── 下一步箭頭 ──── │                                    │
└─────┬────┘                     └──────────────────────────────────┘
      │ Qoder 聊天                       ▲ page.evaluate / snapshot
      ▼                                  │ __showme_emit(event)
┌──────────────┐                  ┌──────┴─────────┐
│ Qoder Agent  │── MCP stdio ───▶ │ ShowMe MCP     │
│ 規劃 / 挑 uid │                  │ Playwright     │
└──────────────┘                  └────────────────┘
```

```text
┌────────────────────────────────────────────────────────────────┐
│  Qoder（IDE 或 CLI）                                            │
│  Agent Model：規劃大綱、讀 snapshot、挑 uid、寫說明               │
│  （可參考它剛寫的 repo：routes / components）                    │
└───────────────┬────────────────────────────────────────────────┘
                │ MCP tool calls（stdio）
                │ start_tutorial · inspect_page · show_step · end_tutorial
                ▼
┌────────────────────────────────────────────────────────────────┐
│  ShowMe MCP server（Python：mcp SDK + Playwright）   ← 我們做    │
│  - 啟動 headed Chrome，開啟目標 url                              │
│  - 注入 overlay.js（add_init_script：每次導航自動重注入）         │
│  - 濃縮 snapshot（帶 uid）· 驗證 uid · 畫步驟 · 阻塞等待完成      │
│  - 沒有 click / type / navigate 工具                             │
└───────────────┬───────────────────────────────▲────────────────┘
                │ page.evaluate(show/clear)      │ window.__showme_emit(event)
                │ page.evaluate(snapshot)        │ （expose_function）
                ▼                                │
┌────────────────────────────────────────────────┴───────────────┐
│  Chrome（ShowMe 啟動）                                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  目標 app  http://localhost:3000（Qoder build 的）          │  │
│  │  + overlay.js ── snapshot walker / 高亮 / 箭頭 / Next / Stuck│  │
│  │                  完成觀察器（listeners + MutationObserver + URL）│  │
│  └──────────────────────────────────────────────────────────┘  │
│                        ▲ Human 自己操作                          │
└────────────────────────────────────────────────────────────────┘
```

**信任邊界**

| 區域 | 信任等級 | 可做 | 不可做 |
|---|---|---|---|
| 使用者 + Demo app | 操作主體 | 點擊、輸入、導航 | — |
| overlay.js | 本機注入、只畫 / 只觀察 | highlight、emit event | 替使用者 submit |
| ShowMe MCP | 可信控制面 | snapshot、uid 驗證、畫、等待、`max_steps` | click / type / navigate |
| Qoder Agent | 不可信輸出 | 選 uid、寫說明、規劃步驟 | 驅動等待、操作頁面 |

### 6.1 元件

| 元件 | 職責 | 技術 |
|---|---|---|
| **Qoder Agent** | 想：把問題拆成 3–8 步的意圖大綱；每步從最新 snapshot 挑一個 `uid`、寫一句說明；依 `show_step` 回傳決定下一步。 | Qoder（IDE / CLI）+ 其內建模型 |
| **ShowMe MCP server** | 做：啟動／附掛瀏覽器、注入 overlay、產生濃縮 snapshot、驗證 `uid`、畫步驟、等待完成、回傳新狀態。決定性程式碼，無模型。 | Python 3.12、`mcp`（`MCPServer`, stdio）、Playwright |
| **overlay.js** | 在頁面裡：走訪 DOM 產生 `uid`、渲染步驟（Driver.js）、觀察完成、透過 `__showme_emit` 回報事件。 | Vanilla JS + Driver.js（MIT） |
| **Demo app** | 由 Qoder 在活動前 build 好的 project management app：sign up、create project、invite member、settings。關鍵元素有 `data-testid` 與 a11y name。 | Qoder 產出（Vite + React 或 Express + HTML，哪個快用哪個） |

### 6.2 誰負責想、誰負責做

| | Qoder Agent（模型） | ShowMe（程式碼） | overlay.js（頁面） |
|---|---|---|---|
| 大綱規劃 | ✅ 在自己的 reasoning 裡 | | |
| 元素綁定 | ✅ 從 snapshot 挑 `uid` | ✅ 拒絕不在最新 snapshot 的 `uid` | ✅ 產生 `uid` |
| 畫箭頭 | | ✅ 呼叫 `__showme.show` | ✅ Driver.js 渲染 |
| 判斷完成 | ❌ 從不問模型 | ✅ 等待事件、timeout | ✅ listeners / observer |
| 下一步 | ✅ 依回傳的新 page | | |
| 操作頁面 | ❌ 沒有工具 | ❌ 沒有工具 | ❌ 只畫、不動 |

```text
  決定性（ShowMe / overlay）                 機率性（Qoder Agent，有界）
  ─────────────────────────                 ─────────────────────────
  啟動瀏覽器、注入 overlay                    意圖大綱（心中，一次）
  濃縮 snapshot（互動角色 ≤150）              從 snapshot 挑一個 uid
  uid ∈ 最新 snapshot？                      寫一句第二人稱說明
  完成偵測（DOM / URL / Next）                stuck → 同 uid 改寫
  事件等待、max_steps                         off_script → 剩餘步驟 replan
  next_action 提示

  模型呼叫：1（start）+ N（show_step）+ 1（end）+ 偶爾 inspect
  其餘全是程式碼。
```

原則：模型擅長讀頁面對意圖；不擅長當迴圈（會忘預算、提早宣告完成、卡住就想操作）。等待與判定因此不在 agent 裡。

### 6.3 為什麼從 v0.1 的「controller + Agent SDK」改成「一個 MCP server」

- **v0.1 是「我們的程式呼叫 Qoder」；v0.2 是「Qoder 呼叫我們」。** 後者才符合「ShowMe 是 coding agent 的 capability」— 使用者留在 Qoder 的對話裡，教學跟建 app 是同一個 agent、同一段脈絡。
- v0.1 的 Python controller 負責 plan → bind → wait → next。在 v0.2 這個迴圈折進 `show_step` 的**阻塞語意**：一次呼叫 = 畫一步 + 等人做完 + 回傳新頁面。Agent 每次只需回答「下一步指哪裡」，不用管等待與判定。
- v0.1 擔心「模型不擅長當迴圈」（忘預算、過早宣告完成）。v0.2 的緩解：`show_step` 回傳值明確告訴 agent 下一步該做什麼（`next_action`），server 端有 `max_steps` 硬上限，server instructions 帶 SHOW protocol（§7.5）。這在 5 小時內夠用；更嚴格的 runtime 強制留到 §15。

### 6.4 為什麼 ShowMe 自己控瀏覽器（Playwright），不串 chrome-devtools-mcp

- ShowMe 本身就是 MCP server；再從 server 裡當 client 去呼叫另一個 MCP server，層層轉手、debug 困難。
- 我們自己寫 snapshot walker，`uid` 的產生、驗證、解析（`[data-showme-uid]`）全在自己手上 — v0.1 §17 的未決問題 2–5（`uid` 當 `evaluate_script` 參數是否可行、`pageId` routing、hooks 是否對 MCP tools 觸發）**全部消失**。
- Playwright 的 `page.expose_function` 讓頁面直接呼叫 Python callback — 取代 v0.1 的 FastAPI sidecar + `fetch()`；`page.add_init_script` 在每次導航自動重跑 — 取代 v0.1 的 presence probe + 重注入邏輯。
- 代價：使用者操作的是 ShowMe 啟動的 Chrome 視窗，不是自己平常的 Chrome。Demo 可接受；附掛既有 Chrome（`connect_over_cdp`）是後續選項。

### 6.5 程序拓樸（本機四個 process）

MVP 刻意做成 **單機 script-based MCP**，不是 microservice、不是 extension、不是正式站點。

```text
localhost
│
├── :3000   Demo app（Qoder 建的；Vite/React 或 Express+HTML）
│              關鍵元素有 data-testid + a11y name
│
├── Chrome（ShowMe 用 Playwright 啟動）
│      └── tab = Demo app
│             └── window.__showme  ← overlay.js（add_init_script）
│                    ├── Driver.js highlight
│                    ├── MutationObserver / URL watcher
│                    └── __showme_emit() → Python callback
│
└── stdio   ShowMe MCP server（Python：mcp + Playwright）
               start_tutorial / inspect_page / show_step / end_tutorial
               由 Qoder Agent 以 MCP client 呼叫
```

沒有 FastAPI sidecar、沒有 chrome-devtools-mcp、沒有我們自己的 controller process。v0.1 那五個 process 見附錄 C。

### 6.6 建議的 repo 切分（尚未存在，僅規劃）

目前 repo 只有 `docs/spec/**`，沒有 entry point、依賴或測試。以下對齊 v0.2：

```text
hackathonQoder/
├── docs/spec/draft/          ← 你現在在這裡
├── showme/                   MCP server（Python 3.12）
│     start_tutorial / inspect_page / show_step / end_tutorial
│     snapshot 濃縮、uid 驗證、wait_event
├── overlay/                  overlay.js + Driver.js
└── demo-app/                 :3000，Qoder 產出（活動前）
```

不要拆成多服務、不要 message queue、不要資料庫。Session 在 ShowMe process 記憶體裡就夠 demo。

---

## 7. MCP Tool 介面

Server 名稱 `showme`；在 Qoder 內 tools 命名為 `mcp__showme__<tool>`。

### 7.1 `start_tutorial(url, goal) → TutorialStart`

啟動（或重用）Chrome、開啟 `url`、注入 overlay、記錄 `goal`、回傳第一份 snapshot。

```json
{
  "session_id": "s_8f2a",
  "goal": "create a project",
  "page": { "url": "http://localhost:3000/", "title": "Dashboard",
            "elements": [ { "uid": "s1-4", "role": "button", "name": "New Project", "testid": "new-project" },
                          { "uid": "s1-7", "role": "link",   "name": "Settings" } ],
            "truncated": false },
  "next_action": "Plan 3–8 steps in your head, then call show_step for the FIRST step using a uid from page.elements."
}
```

### 7.2 `inspect_page(session_id) → Page`

不畫任何東西，只回傳新鮮的濃縮 snapshot。用於「想再看一次」或 replan。

### 7.3 `show_step(session_id, uid, instruction, kind, step_index, step_total, expect_text=None, timeout_s=120) → StepResult`

驗證 `uid` 在最新 snapshot → 畫高亮 + 箭頭 + popover（說明、「Step k / N」、Next、I'm stuck）→ **阻塞等待**完成訊號 → 回傳事件與新 snapshot。

- `kind ∈ {click, input, select, observe}`：模型對完成判定唯一能決定的事；ShowMe 把它對應到決定性規則（§9.3）。
- `expect_text`：`kind = observe` 時，出現此文字即完成。

```json
{
  "event": "step_done",
  "signal": "url_changed",
  "elapsed_s": 4.2,
  "page": { "url": "http://localhost:3000/projects/new", "title": "New Project", "elements": [ "…" ] },
  "next_action": "If the goal is not yet achieved, call show_step for the next step using a uid from page.elements. If the page shows the goal is achieved, call end_tutorial."
}
```

`event ∈ {step_done, stuck, off_script, timeout}`。`stuck` 代表使用者按了 I'm stuck：agent 應用更白話的說明對**同一個** `uid` 再呼叫一次 `show_step`。`off_script`（stretch）代表使用者去了別頁：agent 依 `page` 重新規劃剩餘步驟。

錯誤：`uid_not_in_snapshot`（附上新鮮 `page`，agent 重選）、`session_not_found`、`max_steps_exceeded`。

### 7.4 `end_tutorial(session_id, summary) → {ok: true}`

清掉 overlay，顯示完成 banner（「✅ Done — you created a project」），釋放 session。

### 7.5 Server instructions（SHOW protocol）

以 `MCPServer(instructions=…)` 與各 tool 的 docstring 帶給 Qoder：

- 你在**教**使用者，不是替他做。你沒有任何操作頁面的工具。
- 一次只教一步；每一步只能指向 `page.elements` 裡存在的 `uid`。
- 先在心裡規劃 3–8 步（可以參考你剛寫的程式碼），但每一步的元素都要從**最新**的 `page` 挑。
- 說明用第二人稱、一句話、用畫面上看得到的字（「Click **New Project**」，不是「click the button」）。
- `show_step` 回來之後才決定下一步；不要一次呼叫多個 `show_step`。
- 畫面出現成功訊號（新項目出現、成功訊息）才呼叫 `end_tutorial`；不要提早宣告完成。
- 使用者卡住：同一個 `uid`、更白話的說明。使用者跑去別頁：依新 `page` 重新規劃剩下的步驟。

### 7.6 一個 session 的呼叫序列

```text
Qoder Agent                      ShowMe MCP                           Chrome / overlay.js
   │ start_tutorial(url, goal)      │                                       │
   ├───────────────────────────────▶│ launch → goto → inject → snapshot     │
   │◀── {session_id, page} ─────────┤                                       │
   │ (plan outline in reasoning)    │                                       │
   │ show_step(uid=s1-4, "Click New Project", click, 1, 4)                  │
   ├───────────────────────────────▶│ validate uid → evaluate(show) ───────▶│ draw
   │                                │ wait ◀──── __showme_emit(step_done) ──┤ user clicks; observer fires
   │◀── {event, page(s2)} ──────────┤ snapshot                              │
   │ show_step(uid=s2-9, "Type a project name", input, 2, 4)                │
   ├───────────────────────────────▶│ …                                     │
   │   … repeat …                   │                                       │
   │ end_tutorial(session_id, "…")  │                                       │
   ├───────────────────────────────▶│ clear + banner                        │
```

模型呼叫次數：1（start）+ N（show_step）+ 1（end）+ 偶爾的 `inspect_page` / 重試。N 步 = N 次 reasoning，其餘全是程式碼。

### 7.6.1 偏離腳本（stretch）

```text
偏離腳本
  使用者點錯連結
       │
       ▼
  overlay: URL 不在預期 → __showme_emit(off_script)
       │
       ▼
  show_step 回傳 {event: "off_script", page: 新頁}
       │
       ▼
  Qoder Agent: 不重開 tutorial
       ├─ 先對新頁挑同一 intent 的 uid → show_step
       └─ 找不到 → 依新 page 重新規劃剩餘步驟 → show_step
            overlay notice: "You're on a different page — recalculating."
```

MVP 沒做 off-script 時，同樣情況會落到 `timeout` 或下一步 `uid_not_in_snapshot`；agent 仍依回傳的新 `page` 重選。

### 7.7 後備：非阻塞模式

若 Qoder 對長時間阻塞的 tool call 有不可調的 timeout（§14 Q1），`show_step` 改為立即回傳，另加 `wait_for_user(session_id, timeout_s=25) → StepResult | {event: "pending"}`，由 agent 重複呼叫直到非 `pending`。介面其餘不變。

---

## 8. 核心迴圈

### 8.1 狀態（ShowMe server 端，每個 session）

```text
IDLE ──start_tutorial──▶ READY ──show_step──▶ SHOWING ──event──▶ READY ──…──▶ end_tutorial ──▶ DONE
                                                  │ timeout / steps > max_steps
                                                  ▼
                                               READY（回傳 timeout 事件；agent 決定重畫或結束）
```

Server 端硬限制：`max_steps = 12`、`step_timeout = 120 s`、`session_ttl = 30 min`。「規劃」與「replan」不是 server 狀態 — 那是 agent 的 reasoning。

### 8.2 `show_step` 內部（偽碼）

```python
@mcp.tool()
async def show_step(session_id: str, uid: str, instruction: str, kind: Kind,
                    step_index: int, step_total: int, expect_text: str | None = None,
                    timeout_s: int = 120) -> StepResult:
    s = sessions[session_id]
    if s.steps_shown >= MAX_STEPS: raise ToolError("max_steps_exceeded")
    if uid not in s.latest_snapshot.uids:                       # cheap hallucination guard
        s.latest_snapshot = await snapshot(s.page)
        raise ToolError("uid_not_in_snapshot", page=s.latest_snapshot)

    await s.page.evaluate(SHOW_JS, {"uid": uid, "instruction": instruction, "kind": kind,
                                    "index": step_index, "total": step_total, "expect": expect_text})
    s.steps_shown += 1
    ev = await s.wait_event(timeout=timeout_s)                  # set by __showme_emit (expose_function)
    s.latest_snapshot = await snapshot(s.page)
    return StepResult(event=ev.kind, signal=ev.signal, page=s.latest_snapshot, next_action=hint(ev))
```

### 8.3 Agent 端迴圈（由 instructions 引導，不是我們的程式碼）

```text
1. start_tutorial → 看 page → 心中列出 3–8 步意圖（可參考 repo）
2. 對第 k 步：從最新 page 挑 uid → show_step
3. 依 event：
   step_done  → k+1（若目標已達成 → end_tutorial）
   stuck      → 同 uid、更白話的說明 → show_step
   off_script → 依新 page 重新規劃剩餘步驟 → show_step（stretch）
   timeout    → 重畫同一步或 end_tutorial 並說明
```

---

## 9. 資料模型

### 9.1 Page（ShowMe → agent，濃縮 snapshot）

```json
{
  "url": "http://localhost:3000/projects/new",
  "title": "New Project",
  "elements": [
    { "uid": "s2-3",  "role": "textbox", "name": "Project name", "testid": "project-name" },
    { "uid": "s2-4",  "role": "button",  "name": "Create" },
    { "uid": "s2-h1", "role": "heading", "name": "New Project" }
  ],
  "truncated": false
}
```

- 只保留互動角色（button、link、textbox、checkbox、radio、combobox、menuitem、tab）+ heading + alert；上限約 150 個 node，viewport 內優先；`truncated: true` 時 agent 可用 `inspect_page` 要求再看。
- `uid` 格式 `s{snapshot#}-{index}`：帶 snapshot 世代，陳舊 `uid` 一眼可辨。overlay.js 走訪 DOM 時把 `data-showme-uid` 寫到元素上，`show` 靠它解析回真實 DOM 元素。
- `name` 來自 a11y name（aria-label、label、文字內容）；沒有 name 的互動元素照樣列出但標 `"name": ""`。

### 9.2 Step（agent → ShowMe）

即 `show_step` 的參數：`uid`、`instruction`（第二人稱一句話）、`kind`、`step_index / step_total`、`expect_text`。

### 9.3 完成規則（程式碼，不是模型）

| `kind` | 完成訊號（任一即可） |
|---|---|
| `click` | 目標元素被移除或隱藏 · URL 變更 · 目標被點擊後 500 ms 內 ≥ N 次 DOM mutation |
| `input` | 目標的 `value.length > 0` 且觸發 `blur` / `change` · 或使用者按 Next |
| `select` | 目標觸發 `change` |
| `observe` | 出現 `expect_text` · 或使用者按 Next |
| 任何 | 使用者按 **Next**（明確）· 使用者按 **I'm stuck**（→ `stuck` 事件） |

### 9.4 Event（overlay.js → ShowMe，透過 `window.__showme_emit`）

```json
{ "kind": "step_done", "signal": "input_filled", "url": "http://localhost:3000/projects/new", "ts": 1756400000 }
```

`kind ∈ {step_done, stuck, off_script}`。`off_script`（stretch）：URL 變到當前步驟未預期的路徑，或目標元素在沒有完成訊號的情況下消失。

---

## 10. Overlay runtime（`overlay.js`）

由 ShowMe 以 `page.add_init_script(path="overlay.js")` 注入：每次導航（SPA 或完整 reload）都會在頁面 script 之前重新執行，所以**不需要**偵測「overlay 還在嗎」。Session 狀態在 server，不在頁面。

```text
add_init_script(overlay.js) ──▶ window.__showme
                                ├── snapshot()         走訪 DOM → uid + data-showme-uid
                                ├── show({uid, …})     Driver.js + popover
                                ├── clear()
                                ├── done(text)         完成 banner
                                └── observe(kind)
                                      ├── click/input/change/blur
                                      ├── MutationObserver（debounce）
                                      ├── URL watcher（popstate + pushState wrap）
                                      └── 每步恰好一次 __showme_emit

SPA 導航 / 完整 reload：add_init_script 都會再跑一遍，__showme 重新出現
```

職責：

- **Snapshot walker。** `__showme.snapshot()`：走訪 DOM，對互動元素／heading／alert 產生 `uid`、寫入 `data-showme-uid`，回傳 §9.1 的濃縮清單（含 `data-testid`）。
- **顯示一步。** `__showme.show({uid, instruction, kind, index, total, expect})`：先 `clear()`，用 `[data-showme-uid]` 找到元素、捲進可視範圍，呼叫 Driver.js `highlight()`，popover 含說明、「Step k / N」、**Next**、**I'm stuck**。
- **觀察完成。** 依 `kind`（§9.3）掛 listener（`click`、`input`、`change`、`blur`）、`document.body` 上 debounce 的 `MutationObserver`、URL watcher（`popstate` + wrap `pushState`）。每步恰好發出一次事件。
- **回報。** `window.__showme_emit(event)` — 由 Playwright `expose_function` 提供；頁面呼叫它就等於呼叫 server 端 Python。
- **拆卸。** `__showme.clear()` 銷毀 Driver instance 與 listeners。
- **完成 banner。** `__showme.done(text)`。
- （stretch）**偏離腳本偵測** → `off_script` 事件；**「Not this one?」** 切到 `alternatives`。

---

## 11. 關鍵設計決策

**D1 — 做成 MCP server，不做 agent、不做 LLM。** *否決：* 自己的 controller 呼叫 Qoder Agent SDK（v0.1）— 使用者離開 Qoder 對話、我們得維護一整層 orchestration，而且「教」跟「建」變成兩個 agent。*否決：* ShowMe 內建自己的模型 — 多一份 API key、多一套 prompt，也失去 Qoder 的 repo context。MCP 讓 ShowMe 成為 Qoder 的能力，而不是旁邊另一個東西。

**D2 — 思考在 agent，執行 / 等待 / 驗證在 ShowMe。** 模型擅長讀頁面、把意圖對到元素；不擅長等待與判定。所以 ShowMe 的每個 tool 都是決定性的，而 `show_step` 把「畫 + 等 + 看」包成一次呼叫，agent 每輪只需回答「下一步指哪裡」。

**D3 — ShowMe 沒有操作類工具。** 「agent 從不替你做」在 MVP 是**結構性**的：tool 清單裡沒有 click / type / navigate，不需要 hook 或 deny list 就成立。（Qoder 自己的 Bash 等工具理論上仍可繞過 — 這是 §15 的 runtime mode 題目，不是 MVP 的。）

**D4 — 綁到 `uid`，從不使用模型寫的 selector。** 模型只能在 snapshot 裡實際存在的東西中選擇；ShowMe 驗證 `uid` 在最新 snapshot。幻覺步驟（按鈕寫 Register 卻要「click Sign up」）在結構上不可能。

**D5 — 完成由程式碼偵測。** 問模型「使用者做完了嗎？」每步多一次呼叫，而且不可靠。DOM / URL 訊號便宜且決定性；**Next** 是逃生口。

**D6 — 大綱一次規劃（在 agent 心中），元素逐步綁定。** 步驟 2–5 的元素通常還不存在（表單在點擊後才出現）、路徑依狀態分叉、使用者會偏離腳本。大綱給「Step 2 / 5」與目標感；綁定只在元素真正出現時發生。與 v0.1 相同，只是大綱不再是 JSON 交換物，而是 agent 的 reasoning。

**D7 — ShowMe 自己控瀏覽器（Playwright），不串 chrome-devtools-mcp。** 見 §6.4。`expose_function` 取代 sidecar，`add_init_script` 取代重注入邏輯，自製 `uid` 消滅 v0.1 的四個未決問題。

**D8 — `show_step` 阻塞到人做完。** 一步一次 tool call，agent 迴圈最短、最不會「忘了等」。風險是 MCP client 的 request timeout — Qoder IDE 的 MCP 設定有可調的 Request Timeout；CLI 端 workshop 時驗證；不行就切 §7.7 的非阻塞模式。

**D9 — Localhost + ShowMe 啟動的 Chrome。** 在自己的瀏覽器、自己的 app 注入 script，避開 CSP、extension 與權限問題。正式站點是之後的問題（extension），不需要用來證明這個能力。

**D10 — Snapshot 送到模型前先濃縮。** 只留互動角色 + heading + alert，上限約 150 node。Context 變大時元素選擇準確率急降；snapshot 是每一步唯一的 context。

---

## 12. 失敗模式與處理

| 失敗 | 偵測 | 處理 |
|---|---|---|
| 模型傳來不在最新 snapshot 的 `uid` | ShowMe 驗證 | 回 `uid_not_in_snapshot` + 新鮮 `page`；agent 重選 |
| 目標不在畫面上（例如要先進另一頁） | agent 在 `page` 找不到 | agent 先指向能到達那頁的元素（nav link）；這本來就是大綱的一步 |
| 兩個都合理的元素 | 模型判斷 | 指主要那個；（stretch）popover「Not this one?」切替代 |
| 使用者做了別的事 | MVP：`timeout` / stretch：`off_script` | agent 依回傳的新 `page` 重新規劃剩餘步驟 |
| 完整頁面 reload | — | `add_init_script` 自動重注入；session 在 server；下一次 `show_step` 正常 |
| 完成偵測誤觸／漏觸 | observer | 漏觸 → 使用者按 Next；誤觸 → 下一步 `uid` 仍要通過驗證，最壞多畫一步 |
| Agent 提早宣告完成／跳步／一次叫多個 `show_step` | 人看得到 | instructions + `next_action` 提示；server 對同一 session 的並發 `show_step` 拒絕 |
| Qoder 對每次 tool call 都要求確認 | 設定 | 把 `mcp__showme__*` 加進 allow list（附錄 A） |
| `show_step` 阻塞超過 client timeout | Qoder 回錯 | IDE：調高 Request Timeout；否則 §7.7 非阻塞模式 |
| Snapshot 太大 | node 數 | 更狠地濃縮（只留互動、viewport 優先）；上限 150 |
| 只有圖示、沒有 a11y name 的按鈕 | `name` 為空 | 說明改用位置語言；demo app 補 `aria-label` — 這是 app 的問題，順便示範 ShowMe 會暴露 a11y 缺陷 |

---

## 13. Hackathon 計畫

### 13.1 活動前檢查清單（9:00 前）

- [ ] 用 Qoder build 好 demo app（project management），跑在 `localhost:3000`：sign up、create project、invite member、settings；關鍵元素有 `data-testid` 與 a11y name；假資料。保留 Qoder 的建置對話截圖／錄影（demo 用）。
- [ ] ShowMe repo 骨架：`mcp` Python SDK + Playwright 裝好；`playwright install chrome` 後能啟動 headed Chrome。
- [ ] Qoder（IDE 或 CLI，擇一為 demo 主場）能載入一個 stdio MCP server 並列出 tools（先用 hello-world tool 測）。
- [ ] 用一個 `sleep(90)` 的測試 tool 確認 Qoder 對長時間阻塞 tool call 的容忍度；IDE 端記下 Request Timeout 的最大值。
- [ ] `page.add_init_script` + `page.expose_function` 在 SPA 導航與完整 reload 後都還能動。
- [ ] Driver.js 以 `[data-showme-uid]` 高亮一個元素的最小 demo。

### 13.2 建置時程（11:15 → 17:00）

| 時間 | Person A（ShowMe MCP server） | Person B（overlay.js + demo app + Qoder 接線） |
|---|---|---|
| 11:15–11:30 | `MCPServer` 骨架；`start_tutorial` 啟動 Chrome、開 url、回假 snapshot | 在 demo app 上手動注入 overlay.js；Driver.js 依 `uid` 高亮 |
| 13:00–13:45 | overlay 的 `snapshot()` 接進 `start_tutorial` / `inspect_page`；`uid` 驗證 | 完成 observer（`click` / `input`）；`__showme_emit` 事件 |
| 13:45–14:30 | `show_step` 阻塞等待 + timeout；`end_tutorial`；`max_steps` guard | Next / I'm stuck；reload 後自動重注入驗證 |
| 14:30–15:15 | Server instructions + tool docstring 調整；`next_action` 提示 | Qoder 設定 + allow list；**第一次端到端跑「create a project」** |
| 15:15–16:00 | 跑 5 題 sanity set；修 instructions | 修 observer 誤觸；（若穩定）`off_script` 事件 |
| 16:00–16:30 | Demo 彩排 ×3（A 主導） | 錄製完整 session 的後備影片 |
| 16:30–17:00 | Buffer / freeze | Buffer / freeze |

### 13.3 Sanity set 與指標

**5 題（demo app）：** 建立帳號 · 建立專案 · 邀請成員 · 重新命名專案 · 找到設定頁。

| 指標 | 目標 |
|---|---|
| `uid` 第一次就選對 | ≥ 85% 的步驟 |
| 完成率（session 到 `end_tutorial` 且人真的完成） | ≥ 4 / 5 題 |
| 每 session 的 tool call 次數 | ≤ 2 + 步數 + 2 |
| 每步牆鐘時間（不含人操作） | ≤ 6 s |

同一題跑兩次；步數與說明應大致一致（不是逐字相同 — 大綱在模型心中，不再是決定性輸出）。

### 13.4 Demo 腳本（4 分鐘）

1. **定調（20 秒）。** *「Coding agents can build software in minutes. But sometimes even the developer doesn't know how the generated product works. ShowMe lets the app teach you itself.」*
2. **這個 app 是 Qoder 做的（20 秒）。** 秀 Qoder 對話「Build me a project management website」與跑在 `localhost:3000` 的結果。
3. **問（90 秒）。** 在 Qoder 打「Use ShowMe to teach me how to create a project.」箭頭直接出現在剛生成的網站上；presenter 現場做每一步；完成 banner。
4. **換一題（40 秒）。** 「How do I invite a teammate?」— 不改任何東西、箭頭走另一條路。證明不是預寫腳本。（若 off-script 做好了：故意點錯 → 箭頭在新頁面出現。）
5. **收尾（20 秒）。** *「Browser agents act for you. ShowMe teaches you. ShowMe is onboarding for software that didn't exist five minutes ago.」*

### 13.5 完成定義

1. 從 Qoder 聊天視窗問一句，能在 Qoder build 的 app 上產出人類從頭走到尾完成的導覽。
2. 整條流程只靠標準 MCP 設定接上 Qoder；沒有改 Qoder、沒有自己的 agent 或 LLM。
3. 換一個不同的問題，不改程式碼也能跑。

### 13.6 後備方案

- Qoder 對阻塞的 `show_step` timeout 且不可調 → §7.7 非阻塞 + `wait_for_user` polling。
- Qoder agent 迴圈不穩（提早結束、順序錯）→ 把 SHOW protocol 另外放進專案 rules / 一個 MCP prompt；最後手段是 server 端 `run_tutorial(goal)` 內部自帶 LLM 跑迴圈（違反 D1，只作救援）。
- Overlay 注入被 demo app 的 CSP 擋 → demo app dev mode 直接加 `<script>` tag；能力不變。
- 全部壞掉 → 播錄好的 session。

---

## 14. 未決問題（10:00 workshop 時驗證）

1. **阻塞 tool call 的上限。** Qoder IDE 的 MCP 設定有 Request Timeout 下拉選單 — 最大值多少？CLI 有沒有對應設定？決定 D8 還是 §7.7。
2. **Tool 確認。** Qoder 預設每次 MCP tool call 都要確認；CLI 的 `permissions.allow: ["mcp__showme__*"]` 與 IDE 的自動執行設定，哪個在 demo 機器上真的不跳確認？
3. **迴圈穩定度。** Qoder agent 連續 5–8 次阻塞呼叫後，會不會開始摘要、跳步或提早 `end_tutorial`？需要多強的 instructions？
4. **Demo 主場：IDE 還是 CLI？** 兩者都支援 stdio MCP。IDE 觀眾看得到對話與工具呼叫；CLI 設定較單純。Workshop 後定一個。
5. **Chrome 來源。** Playwright `channel="chrome"` 在 demo 機器可用？不行就用 Playwright 的 Chromium（外觀差異可接受）。

---

## 15. 後續方向

- **SHOW 作為 runtime 的一等 permission mode。** v0.1 的核心論述：allow / ask / deny 之外的第四種 — 當政策拒絕某個操作時，runtime 自動降級成引導而不是報錯。MVP 的「ShowMe 沒有操作類工具」是這個想法的種子；完整版需要 agent runtime 的 hook / deny list 與 evidence log。圖與權限編譯層見下方與附錄 C。
- **「just do it for me」時刻。** 使用者要求代勞 → agent 嘗試操作 → 被拒 → 降級成 SHOW，並附證據面板。是 pitch 用的好場景，但依賴上一點。
- **Off-script recovery 正式化**（若 hackathon 沒做完）與「Not this one?」替代切換。
- **Repo hints 正式化。** `start_tutorial(…, hints={routes, components})` 讓 agent 把它的 repo 知識結構化地交給 ShowMe，用於大綱詞彙與 `expect_text`。
- **教學副產品 = 文件。** 每次 tutorial 結束輸出一份 markdown how-to（步驟 + 截圖）；「自己教人用」的軟體順便「自己寫文件」。
- **任意網站的 extension**（content script 取代注入；同一套 tool 契約）；附掛使用者自己的 Chrome（`connect_over_cdp`）。
- **無障礙模式：** 同一套步驟，作為對螢幕閱讀器友善的播報。
- **Session 收據：** 簽署的 tool log，讓「agent 從未操作」能被第三方驗證。

### 15.1 SHOW 權限編譯層（後續，不是 MVP）

Agent 沒有「決定去點擊」的地位。拒絕發生在 runtime，不是 prompt。完整圖（含 chrome-devtools-mcp / sidecar）在附錄 C；這裡只保留權限編譯的形狀，之後接到 Qoder 自己的 tool 政策：

```text
                    QoderAgentOptions / permissions
                    ┌─────────────────────────────────────────┐
                    │ tools / allowed_tools（窄可見集合）     │
                    │   ShowMe 的 start / inspect / show / end│
                    │                                         │
                    │ disallowed_tools（deny 優先於 allow）   │
                    │   全部 acting + Bash/Write/Edit         │
                    │                                         │
                    │ permission_mode = "dontAsk"             │
                    │   未預授權 → 直接 deny，不問人          │
                    └──────────────────┬──────────────────────┘
                                       │
                                       ▼
                    PreToolUse hooks（每一呼叫都看得到）
                    ┌─────────────────────────────────────────┐
                    │ 1. evidence_logger  matcher=*           │
                    │    {tool, decision} → evidence store    │
                    │                                         │
                    │ 2. 若仍走 evaluate_script：模板圍欄     │
                    │    只准 show / clear / probe / inject   │
                    └─────────────────────────────────────────┘

    官方補充（查證 2026-08-29）：
    - MCP tool 全名格式：mcp__<server>__<tool>
      例：mcp__showme__show_step
    - can_use_tool 看不到已被 allow/deny 的呼叫
      → 證據 log 必須用 hook，不能只靠 can_use_tool
    - 同一 tool 同時命中 allow 與 deny 時，deny 勝出
```

```text
  使用者：「just do it for me.」
                 │
                 ▼
        Agent 嘗試 click
                 │
                 ▼
        ┌────────────────┐
        │ disallowed +   │
        │ dontAsk        │── deny ──▶ PermissionDenied
        └────────────────┘              │
                                        ▼
                          evidence: acting_calls_executed: 0
                          overlay:  「I can't click — here's your next step」
                          runtime:  繼續 SHOW（bind + draw）
```

---

## 附錄 A — 把 ShowMe 接上 Qoder

**Qoder CLI**（stdio 為預設 transport；設定落在 `~/.qoder/settings.json`、`${project}/.qoder/settings.local.json` 或 `${project}/.mcp.json`）：

```bash
qoder mcp add showme -- uv run --directory /path/to/showme python -m showme
```

免逐次確認（CLI permissions）：

```json
{ "permissions": { "allow": ["mcp__showme__*"], "deny": [] } }
```

**Qoder IDE**（Settings → MCP → 以 JSON 新增；同一頁可調 Request Timeout）：

```json
{
  "mcpServers": {
    "showme": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/showme", "python", "-m", "showme"],
      "env": { "SHOWME_BROWSER": "chrome" }
    }
  }
}
```

Tools 在 Qoder 內的名稱：`mcp__showme__start_tutorial`、`mcp__showme__inspect_page`、`mcp__showme__show_step`、`mcp__showme__end_tutorial`。

**Server 骨架（Python）：**

```python
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("showme", instructions=SHOW_PROTOCOL)   # §7.5

@mcp.tool()
async def start_tutorial(url: str, goal: str) -> TutorialStart:
    """Open the running app in ShowMe's browser and return its current page structure. Call this first."""
    ...

if __name__ == "__main__":
    mcp.run()   # stdio
```

## 附錄 B — 參考資料

- Qoder — MCP Servers（CLI：`qoder mcp add`、設定檔位置、`mcp__<server>__<tool>` 命名、permissions）— https://docs.qoder.com/cli/mcp-servers
- Qoder — Model Context Protocol（IDE：`mcpServers` JSON、STDIO / SSE / Streamable HTTP、Request Timeout、tool 確認）— https://docs.qoder.com/user-guide/chat/model-context-protocol
- Qoder — Agent Mode（Agent 依工具回傳規劃下一步；可設定自動執行清單）— https://docs.qoder.com/user-guide/chat/agent
- MCP Python SDK（`MCPServer`、`@mcp.tool()`、`instructions`、stdio）— https://github.com/modelcontextprotocol/python-sdk
- Playwright for Python — `page.add_init_script`、`page.expose_function` — https://playwright.dev/python/docs/api/class-page
- Driver.js — https://driverjs.com
- Frigade AI（最接近的既有方案）— https://www.ycombinator.com/launches/O1Z-frigade-ai-in-app-support-agent-that-adapts-to-your-product-automatically
- WalkMe 使用者對 selector 損壞的評論 — https://aws.amazon.com/marketplace/reviews/reviews-list/prodview-warthuc74jc6e?page=1
- chrome-devtools-mcp tools 與 `uid`（v0.1 路徑；v0.2 已改自製 walker）— https://github.com/ChromeDevTools/chrome-devtools-mcp · https://github.com/ChromeDevTools/chrome-devtools-mcp/blob/main/docs/tool-reference.md
- Qoder permission：`allowed_tools` / `disallowed_tools` / `dontAsk` / `PreToolUse`；deny 優先 — https://docs.qoder.com/en/cli/sdk/python/permissions · https://docs.qoder.com/en/cli/sdk/python/tools
- ShowMe v0.1 架構 ASCII（controller + Agent SDK + chrome-devtools-mcp + sidecar）— 已併入本文件附錄 C；§15 回收其 SHOW runtime 設計

## 附錄 C — v0.1 架構 ASCII（已 superseded，供 §15 回收）

**狀態：** 規格推導，不是 MVP 實作圖。v0.2 改成「一個 MCP server + Playwright」，見 §6。  
**為什麼還留：** SHOW 作為 runtime 一等 permission、evidence log、sidecar / chrome-devtools-mcp 路徑，hackathon 之後會回收。

### C.1 系統情境（v0.1）

```text
                 「How do I create an account?」
                                 │
                                 ▼
┌──────────┐   自己點、自己打字    ┌──────────────────────────────────┐
│  Developer│ ──────────────────▶ │  Demo app  :3000                  │
│  / Demo   │                     │  + overlay.js（高亮 / 箭頭 / Next）│
│  使用者   │ ◀── 下一步箭頭 ──── │                                    │
└──────────┘                     └──────────────────────────────────┘
                                 ▲ 注入 / snapshot          │ POST events
                                 │ READ + DRAW only         ▼
                         ┌───────┴────────┐        ┌────────────────┐
                         │ chrome-devtools│        │ Sidecar :7777  │
                         │ MCP            │        │ overlay / event│
                         └───────┬────────┘        │ evidence       │
                                 │ MCP tools       └────────┬───────┘
                                 ▼                          │ wake-up
                         ┌────────────────┐                 │
                         │ Qoder Agent    │◀────────────────┘
                         │ (query 有界)   │
                         └───────┬────────┘
                                 │ 何時呼叫、呼叫什麼
                                 ▼
                         ┌────────────────┐
                         │ Controller     │
                         │ (決定性迴圈)   │
                         └────────────────┘
```

**信任邊界（v0.1）**

| 區域 | 信任等級 | 可做 | 不可做 |
|---|---|---|---|
| 使用者 + Demo app | 操作主體 | 點擊、輸入、導航 | — |
| overlay.js | 本機注入、只畫 / 只觀察 | highlight、POST event | 替使用者 submit |
| chrome-devtools-mcp | 瀏覽器橋 | snapshot、核准過的 evaluate_script | acting tools |
| Qoder Agent | 不可信輸出 | 選 uid、寫說明 | 驅動迴圈、操作頁面 |
| Controller | 可信控制面 | 狀態機、預算、uid 驗證 | 猜元素 |
| Sidecar | 本機狀態店 | 事件、證據、overlay 靜態檔 | 呼叫模型 |

### C.2 程序拓樸（v0.1：五個 process）

```text
localhost
│
├── :3000   Demo app（Vite/React 或 Express+HTML）
│              關鍵元素有 data-testid
│
├── Chrome（我們啟動；可 --wsEndpoint attach）
│      └── tab = Demo app
│             └── window.__showme  ← overlay.js（從 :7777 注入）
│                    ├── Driver.js highlight
│                    ├── MutationObserver / URL watcher
│                    └── fetch() → Sidecar
│
├── :7777   Sidecar（FastAPI + uvicorn）
│              GET  /overlay.js
│              POST /event
│              GET  /session
│              POST /evidence
│              GET  /evidence  （demo 證據面板）
│
├── stdio   chrome-devtools-mcp（npx chrome-devtools-mcp@latest）
│              take_snapshot / evaluate_script / list_pages / wait_for
│
└── py      Controller + Qoder Agent SDK
               query() × 有界次數（outline / bind / replan / rephrase）
```

### C.3 元件與責任（v0.1）

```text
┌─────────────────────────────────────────────────────────────────────┐
│                         Controller（Python 3.12）                     │
│  擁有 Session 狀態機 · 預算 · uid 驗證 · 從不讓模型驅動迴圈           │
│                                                                     │
│   IDLE → PLANNING → BINDING → SHOWING → WAITING ⇄ REPLAN → COMPLETE │
│                          │ fail budget / timeout                    │
│                          ▼                                          │
│                       FAILED                                        │
└───────────────┬───────────────────────────────┬─────────────────────┘
                │ query(phase)                  │ wait_event()
                ▼                               ▼
┌───────────────────────────────┐  ┌──────────────────────────────────┐
│ Qoder Agent                   │  │ Sidecar                          │
│                               │  │                                  │
│  只做 2+2 件事：              │  │  GET  /overlay.js                │
│   1. outline  意圖大綱        │  │  POST /event  step_done /        │
│   2. bind     uid + draw      │  │             off_script / stuck / │
│   3. replan   剩餘大綱        │  │             question             │
│   4. rephrase 同一 uid        │  │  POST /evidence  hook log        │
│                               │  │  記憶體 session + 每場 JSON      │
│  tools 可見集合極窄           │  │                                  │
└───────────────┬───────────────┘  └──────────────────▲───────────────┘
                │ MCP                                   │
                ▼                                       │ fetch()
┌───────────────────────────────┐  ┌──────────────────┴───────────────┐
│ chrome-devtools-mcp           │  │ Page + overlay.js                │
│                               │  │                                  │
│  ALLOW                        │  │  問題輸入框                      │
│   take_snapshot → a11y + uid  │  │  __showme.show(el, opts)         │
│   evaluate_script（模板圍欄） │──│  __showme.clear()                │
│   list_pages / wait_for       │  │  observer → 恰好一次 step_done   │
│                               │  │  URL / 元素消失 → off_script     │
│  DENY                         │  │  Next / I'm stuck                │
│   click fill type hover drag  │  │                                  │
│   press_key upload handle_    │  └──────────────────────────────────┘
│   dialog navigate new/close   │
│   fill_form type_text click_at│   ← 官方還有這三個 acting tools
│   network / perf / lighthouse │
└───────────────────────────────┘
```

官方 acting tools 比早期稿子多：`fill_form`、`type_text`、`click_at`。若走回這條路徑，SHOW 政策應一併 DENY。

### C.4 狀態機與資料契約（v0.1）

```text
                         question
            IDLE ──────────────────▶ PLANNING
                                        │ outline
                                        ▼
                                     BINDING
                                  ┌─────┴─────┐
                         uid 找到 │           │ uid 不在畫面 / 幻覺 uid
                                  ▼           ▼
                               SHOWING      REPLAN
                                  │ drawn      │
                                  ▼            │ replans ≤ 3
                               WAITING ────────┤
                                  │            │
                    step_done     │            │ budget 用盡
                    還有下一步    │            ▼
                                  │          FAILED
                                  ▼
                           下一 BINDING
                                  │
                    沒有下一步    │
                                  ▼
                               COMPLETE
```

硬預算（只存在 Controller）：`max_steps=12` · `max_replans=3` · `step_timeout=120s` · `max_model_calls=20`

```text
  question ──▶ Outline ──▶ Binding ──▶ Event ──▶ Evidence
                 │            │           │          │
                 │            │           │          └─ hook → sidecar
                 │            │           └─ page → sidecar
                 │            └─ agent 逐步，controller 驗證 uid
                 └─ agent 一次，只有 intent，沒有 selector
```

Session 結束證據摘要：`{ snapshots, draws, acting_calls_attempted, acting_calls_executed: 0 }`

### C.5 時序（v0.1 happy path）

```text
Controller          Qoder Agent         chrome-devtools-mcp      Page/overlay         Sidecar
    │  outline()         │                      │                     │                  │
    ├───────────────────▶│ take_snapshot        │                     │                  │
    │                    ├─────────────────────▶│                     │                  │
    │                    │◀── 濃縮 a11y+uids ───┤                     │                  │
    │◀── Outline JSON ───┤                      │                     │                  │
    │                    │                      │                     │                  │
    │  bind(step k)      │                      │                     │                  │
    ├───────────────────▶│ take_snapshot        │                     │                  │
    │                    ├─────────────────────▶│                     │                  │
    │                    │ pick uid ∈ snapshot  │                     │                  │
    │                    │ evaluate_script(show)│                     │                  │
    │                    ├─────────────────────▶│── el ─▶ __showme.show                  │
    │◀── {uid,text} ─────┤                      │                     │                  │
    │  wait_event()      │                      │                     │ 使用者操作       │
    │                    │                      │                     │ observer 觸發    │
    │                    │                      │                     ├── POST step_done ▶│
    │◀──────────────────────────────────────────── wake-up ──────────────────────────────┤
    │  k+1               │                      │                     │                  │
```

### C.6 overlay 注入（v0.1：evaluate_script + sidecar）

```text
evaluate_script(inject) ──▶ <script src="http://localhost:7777/overlay.js">
                                      │
                                      ▼
                            window.__showme
                            ├── show(el, opts)   Driver.js + popover
                            ├── clear()
                            ├── notice(text)     被拒操作 banner
                            ├── ask(question)    右下角輸入 → kind:question
                            └── observe(kind)    每步恰好一次 step_done

SPA 導航：__showme 還在
完整 reload：__showme === undefined → probe → 再注入再 show
```

核准模板（hook 空白正規化後比對原始碼，這是 `evaluate_script` 的圍欄）：

```text
(el, opts) => window.__showme.show(el, opts)
() => window.__showme.clear()
() => Boolean(window.__showme)
() => { /* 注入 overlay.js */ }
```

### C.7 v0.1 repo 切分

```text
hackathonQoder/
├── docs/spec/draft/
├── controller/               狀態機、預算、濃縮 snapshot、uid 驗證
├── agent/                    QoderAgentOptions、SHOW tool 政策、hooks
├── sidecar/                  FastAPI :7777
├── overlay/                  overlay.js + Driver.js
├── demo-app/                 :3000
└── evidence/                 每 session 一份 JSON
```

### C.8 v0.1 未決項（v0.2 已消滅）

這些是串 chrome-devtools-mcp 時的接線風險；改自製 Playwright walker 後不再擋路：

1. Qoder 對 MCP tool 的實際字串是否真是 `mcp__chrome-devtools__*`
2. MCP 模式下 `evaluate_script` 的 `args: [{uid}]` 是否與 CLI 一樣解成 DOM 元素
3. `pageId`：DeepWiki 標成 `--experimentalPageIdRouting`；舊稿寫 `--pageIdRouting`
4. `PreToolUse` 對 MCP tools 是否與 built-in 相同觸發
5. `dontAsk` + hook 沒回傳時，已在 `allowed_tools` 的 `evaluate_script` 會不會被誤拒

若 §15 走回 Qoder Agent SDK + chrome-devtools-mcp，這些要重新驗證。
