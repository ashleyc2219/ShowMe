# 階段 5-Q｜A14 MCP 契約測試與 stdio 接線 — 實作報告

> 日期：2026-08-29　｜　計劃：`docs/plan/unfinish/A14_MCP契約測試與stdio.md`
> 與階段 1-P（A11–A13，另一個 agent）**平行**執行，兩邊改的檔案不重疊。
> 依指示**不 commit**，由主控統一處理。

---

## 實作邏輯

前面十三篇都是「直接呼叫 `ShowMeApp` 的方法」，這一篇第一次**從 MCP client 的角度**看 ShowMe。

```text
  (A) 契約測試：in-memory，沒有 subprocess、沒有 stdio
  ┌────────────────────────────┐        ┌────────────────────────────┐
  │ tests/test_mcp_contract.py │        │ showme/server.py（薄殼）    │
  │   async with Client(mcp)   │<======>│   MCPServer("showme",       │
  │     list_tools()           │ 直接    │     instructions=...)       │
  │     call_tool(...)         │ 函數    │   @mcp.tool() x 4           │
  └────────────────────────────┘ 呼叫    │   → get_app() → ShowMeApp   │
             ▲                           └────────────────────────────┘
             │ conftest 的 mcp_client fixture 先 set_app(用 FakeBrowser 的 app)
             │ 測完 finally: set_app(None) 還原 → 不開瀏覽器、不污染其他測試

  (B) stdio 手動驗證：真的開一個子行程，一行一個 JSON-RPC
  ┌────────────┐ stdin  ┌───────────────────────┐
  │ 假的 client │ ─────> │ uv run showme          │
  │ (subprocess)│ <───── │  = mcp.run("stdio")    │
  └────────────┘ stdout └───────────────────────┘
```

契約要鎖的四件事：**恰好四個 tool、沒有 `wait_for_user`、失敗走 `error` 欄不變成 `is_error`、`show_step` 的參數 schema 正確且 `instructions` 有帶上**。

錯誤通道的差別（規格明訂只准用左邊那條）：

```text
   ① 規格上的操作失敗（我們用這種）        ② protocol error（絕不用）
   return {"error": "session_not_found"}   raise SomethingError
        │                                       │
   is_error = False                        is_error = True
   structured_content = {...}              structured_content = None
   agent 讀得懂、知道怎麼補救               agent 只拿到一段英文字串
```

---

## 步驟

### Step 1：Context7 查證官方 API（不憑記憶猜）

查 `/websites/py_sdk_modelcontextprotocol_io_v2`，確認：

| 問題 | 查到的答案 | 來源 |
|---|---|---|
| in-memory 測試怎麼寫 | `from mcp import Client`；`async with Client(mcp) as c:`；搭 `@pytest.mark.anyio` + 回 `"asyncio"` 的 `anyio_backend` fixture | <https://py.sdk.modelcontextprotocol.io/v2/get-started/testing> |
| `list_tools()` 回什麼 | `ListToolsResult`（`tools: list[Tool]`）；每個 tool 有 `.name` / `.title` / `.description` | <https://py.sdk.modelcontextprotocol.io/v2/api/mcp_types>、<https://py.sdk.modelcontextprotocol.io/v2/client> |
| `call_tool()` 回什麼 | `CallToolResult`：`.content`（給模型看的區塊）、`.structured_content`（JSON）、`.is_error` | <https://py.sdk.modelcontextprotocol.io/v2/client> |
| 丟例外會怎樣 | `is_error=True`、`content=[TextContent("Error executing tool ...")]`、`structured_content=None` | <https://py.sdk.modelcontextprotocol.io/v2/llms-full.txt> |

`payload()` helper 依計劃保留（裸 dict / 被包一層兩種形狀都能過），但文件裡把**實測結論寫死**：本專案的 `structured_content` **就是裸 dict**，因為 A07 已把四個 tool 的回傳註記寫成 `dict[str, object]`。實地再驗一次 `output_schema`：

```text
start_tutorial | output_schema: {'additionalProperties': True, 'title': 'start_tutorialDictOutput', 'type': 'object'}
inspect_page   | output_schema: {'additionalProperties': True, 'title': 'inspect_pageDictOutput',   'type': 'object'}
show_step      | output_schema: {'additionalProperties': True, 'title': 'show_stepDictOutput',      'type': 'object'}
end_tutorial   | output_schema: {'additionalProperties': True, 'title': 'end_tutorialDictOutput',   'type': 'object'}
```

四個都推得出 schema ✅（若寫成裸 `-> dict` 這四行會全是 `None`，`structured_content` 也會跟著變 `None`）。

### Step 2：`tests/conftest.py` 加 `mcp_client` fixture

**只加這一個 fixture，既有的 `anyio_backend` / `static_server` / `fake_browser` / `app` / `started` 一個字都沒動。**
另外在檔頭 import 區加了三行：`from mcp import Client`、`from showme.server import mcp as server_mcp`、`from showme.server import set_app`。

```python
@pytest.fixture
async def mcp_client(app: ShowMeApp):
    set_app(app)                     # 換成用 FakeBrowser 的 app → 契約測試不開瀏覽器
    try:
        async with Client(server_mcp) as client:
            yield client
    finally:
        set_app(None)                # 還原，免得污染其他測試
```

### Step 3：`tests/test_mcp_contract.py`（新增，10 條）

| 分組 | 測試 |
|---|---|
| 有哪些 tool | `test_server_exposes_exactly_the_four_tools`、`test_there_is_no_wait_for_user_tool`、`test_every_tool_has_a_description` |
| 錯誤通道 | `test_unknown_session_is_a_normal_result_not_a_protocol_error`、`test_end_tutorial_with_unknown_session_also_returns_an_error_field` |
| show_step schema | `test_show_step_input_schema_has_all_eight_parameters`、`test_show_step_expect_text_and_timeout_s_are_optional`、`test_other_tools_have_the_expected_parameters` |
| instructions | `test_server_instructions_are_not_empty` |
| 端到端一次 | `test_start_tutorial_through_the_mcp_layer` |

### Step 4：stdio 手動驗證（做法改了，見「遇到的問題」）

用 Python `subprocess` 起 `uv run showme`，寫入三則 JSON-RPC（`initialize` → `notifications/initialized` → `tools/list`），逐行讀 stdout，讀完 `terminate()`。

### Step 5／6：Qoder 設定與 allow list（寫進文件）

```json
{
  "mcpServers": {
    "showme": {
      "command": "uv",
      "args": ["--directory", "/Users/linjunting/hackathonQoder", "run", "showme"]
    }
  }
}
```

allow list 加 `mcp__showme__*`；四個 tool 在 Qoder 的全名是 `mcp__showme__start_tutorial` / `_inspect_page` / `_show_step` / `_end_tutorial`。
IDE 找不到 `uv` 時的備援：`"command": "/opt/homebrew/bin/uv"`（本機 `command -v uv` 實測值，uv 0.11.32）。
**設定檔路徑沒有杜撰**，文件維持「以 Qoder 官方文件為準」。

### Step 7：Request Timeout — **留給使用者手動**

需要開著的 Qoder IDE ＋ 真人看時鐘、刻意什麼都不點，agent 做不了。已在 A14 Step 7 開頭加方框標明，量測步驟原文保留：

1. 讓 agent 呼叫 `start_tutorial(url=..., goal=...)`，記下 `session_id` 與任一 `uid`。
2. 讓它呼叫 `show_step(..., timeout_s=60)`，然後**什麼都不要做**，開始看時鐘。
3. 判讀：60 秒後正常回 `event="timeout"` → IDE 肯等 ≥60 秒，再用 `timeout_s=120` 測一次；不到 60 秒就中斷 → 記下秒數 `T`，把 IDE 的 Request Timeout 調到 ≥180 秒，調不了就 demo 時每步明確傳小於 `T` 的 `timeout_s`。
4. 數字抄進 `A16_與B合流與Demo演練.md` 的「demo 前一天 checklist」。

### Step 8：commit — 依指示不做

---

## 測試方式

```text
TDD 節奏：
  寫 conftest 的 mcp_client + test_mcp_contract.py（10 條）
        ↓
  uv run pytest tests/test_mcp_contract.py -q   →  1 failed, 9 passed   ★ 紅
        ↓  紅的那條是 end_tutorial（平行 agent 的 A13 還沒落地）
  等 A13 落地後重跑                              →  10 passed           ★ 綠
        ↓
  uv run pytest -m "not browser" -q              →  147 passed
        ↓
  stdio：subprocess 送 JSON-RPC → 比對 serverInfo.name / instructions / tools
```

跑的指令：

```bash
uv run pytest tests/test_mcp_contract.py -q
uv run pytest -m "not browser" -q
uv run python /tmp/stdio_check.py        # 暫存檔，不進版控
```

**這一篇的紅燈是真紅燈、而且不是我造成的**：`test_end_tutorial_with_unknown_session_also_returns_an_error_field` 斷言的 `{"ok": False, "error": "session_not_found"}` 是 A13 才實作的形狀，我寫測試時 `app.end_tutorial()` 還回 `{"error": "not_implemented"}`。這正好是「測試先於實作」的樣子，所以**沒有改測試去遷就它**，等平行 agent 的 A13 落地就自己綠了。

---

## 遇到的問題與怎麼解決

### 1.（主要）計劃 Step 4「做法 A」的 `printf | uv run showme` 拿不到 `tools/list` 的回應

計劃寫「預期會看到**兩行**很長的 JSON」，**實測只有一行**——只有 `id:1` 的 `initialize` 回應，`id:2` 的 `tools/list` 回應永遠拿不到。連跑三次結果一模一樣（每次都是 1021 bytes、只有 `"id":1`）：

```text
run 1: exit=0 ids="id":1  bytes=1021
run 2: exit=0 ids="id":1  bytes=1021
run 3: exit=0 ids="id":1  bytes=1021
```

**原因**：`printf` 一口氣寫完三行就關掉 stdin，server 讀到 EOF 就開始收攤，`tools/list` 還沒處理完 process 就結束了。這是 EOF 跟請求處理在搶時間，不是 server 壞掉。

**怎麼解決**：新增**做法 A′**——用 Python `subprocess.Popen` 開子行程、**把 stdin 留著**、背景執行緒逐行讀 stdout、讀完才 `terminate()`。三則訊息全部驗得到。已把整段寫回 A14 Step 4，並在 §9 排錯表加一條對應症狀，驗收清單也改成指向做法 A′。

### 2. 這台 macOS 沒有 `timeout` 指令（沿用 A01 的發現）

`command -v timeout gtimeout` 兩個都空（macOS 預設不帶 GNU coreutils），所以不能用 `timeout 30 uv run showme` 保底。**超時控制寫在 Python 裡**（做法 A′ 的 `t.join(timeout=30)` + `proc.wait(timeout=10)`）。已在 A14 Step 4 與 §9 排錯表註明。

### 3. `uv run mcp dev`（Inspector）：有 Node 但還是跳過

本機 **Node v22.22.3 / npx 10.9.8 有裝**，但 `uv run mcp dev showme/server.py:mcp` 會先讓 npx 下載 `@modelcontextprotocol/inspector@2.4.0`（本機沒快取），**35 秒還在裝**，Inspector 的網址一直沒印出來：

```text
npm warn exec The following package was not found and will be installed: @modelcontextprotocol/inspector@2.4.0
npm warn deprecated @modelcontextprotocol/server-legacy@2.0.0: ...
```

Inspector 是「用滑鼠玩玩看」的便利工具、不是驗收條件，做法 A′ 已經把驗收清單每一項都驗完，所以**依指示 30 秒起不來就略過**，並在 A14 文件註明（原文只寫「沒有 Node 就跳過」，已補上「有 Node 但要等 npm 裝很久」這個實際情況）。

### 4. 計劃裡關於「裸 `dict`」的敘述已經過時

A14 Step 1 原本寫「我們四個 tool 的註記是沒有型別參數的裸 `dict`，A01 Step 10 預期印出 `{'error': 'not_implemented'}`」。實際上 A01 實測到的是**第三種：`None`**，而 A07 已經據此把註記改成 `dict[str, object]`。已把那一格與底下的方框改寫成實測結論（含 A01 的三行對照表），`payload()` helper 依指示保留兩種形狀都能接。

### 5. `Client` 沒有 `initialize_result` 屬性

`test_server_instructions_are_not_empty` 尾巴用 `getattr(mcp_client, "initialize_result", None)` 探測 initialize 結果。實測 mcp 2.1.1 的 `Client` **沒有**這個屬性（`[a for a in dir(c) if 'init' in a.lower()]` 只有 dunder），所以那段 if 直接跳過——這正是計劃設計的行為（「探不到就跳過」），不需要改。`instructions` 真的有送出去這件事，改由 stdio 驗證直接證明（見下方輸出）。

---

## 測試結果

### `uv run pytest tests/test_mcp_contract.py -q`

第一次跑（A13 尚未落地，正確的紅燈）：

```text
....F.....                                                               [100%]
>       assert data["ok"] is False
E       KeyError: 'ok'
tests/test_mcp_contract.py:107: KeyError
=========================== short test summary info ============================
FAILED tests/test_mcp_contract.py::test_end_tutorial_with_unknown_session_also_returns_an_error_field
1 failed, 9 passed in 0.13s
```

A13 落地後重跑：

```text
..........                                                               [100%]
10 passed in 0.09s
```

### `uv run pytest -m "not browser" -q`

```text
........................................................................ [ 48%]
........................................................................ [ 97%]
...                                                                      [100%]
147 passed, 18 deselected in 1.57s
```

全綠、0 skipped。`mcp_client` fixture 的 `finally: set_app(None)` 有效，沒有污染其他測試。

### stdio `initialize` 手動驗證（做法 A′）

```text
--- 收到 2 行 stdout ---
server name   : showme
server version:
protocolVer   : 2025-06-18
instructions? : True
instructions[0:60] : You are TEACHING the user how to use the app; you never act
tools         : ['start_tutorial', 'inspect_page', 'show_step', 'end_tutorial']
--- stderr（前 500 字）---

--- exit code: 143
```

`initialize` 回應的原始 JSON 片段（做法 A 直接 `printf` 抓到的第一行，前 700 字）：

```json
{"jsonrpc":"2.0","id":1,"result":{"capabilities":{"experimental":{},"prompts":{"listChanged":false},
"resources":{"listChanged":false,"subscribe":false},"tools":{"listChanged":false}},
"instructions":"You are TEACHING the user how to use the app; you never act for them.\n
- You have no click/type/navigate tools. You only look (start_tutorial / inspect_page) and point (show_step).\n
- Plan 3-8 steps in your head, but pick each step's uid from the LATEST page.elements only. Never reuse a uid from an older snapshot.\n
- One show_step at a time; wait for it to return before deciding the next step.\n
- instruction: second person, one sentence, use the words visible on screen (e.g. \"Click New Project\"...
```

判讀：

| 檢查點 | 結果 |
|---|---|
| `result.serverInfo.name == "showme"` | ✅ |
| `result.instructions` 存在且是 SHOW protocol 原文 | ✅ |
| `tools/list` 恰好四個名字、沒有 `wait_for_user` | ✅ |
| stdout 只有 JSON-RPC（沒有雜訊 `print`） | ✅ |
| **stderr 全空** | ✅ |
| `protocolVersion` 協商結果 | `2025-06-18`（送什麼回什麼） |
| `serverInfo.version` | 空字串（`MCPServer` 沒收到版本；不影響接線） |
| 結束方式 | exit 143 = 128+15，SIGTERM 收得掉 |

### 驗收清單

| 項目 | 結果 |
|---|---|
| `uv run pytest tests/test_mcp_contract.py -q` → 10 passed | ✅ |
| `uv run pytest -m "not browser" -q` 全綠、0 skipped | ✅ 147 passed |
| `list_tools()` 恰好 `{start_tutorial, inspect_page, show_step, end_tutorial}`、數量 4 | ✅ |
| 沒有 `wait_for_user` | ✅ |
| 四個 tool 都有非空 `description` | ✅ |
| `inspect_page` 假 session → `is_error` 不是 True、`error="session_not_found"`、`page=None` | ✅ |
| `show_step` schema 恰好 8 個參數；`required` 不含 `expect_text` / `timeout_s` | ✅ |
| 其他三個 tool 的參數也對 | ✅ |
| `INSTRUCTIONS` 含「you never act for them」「One show_step at a time」「LATEST page.elements」 | ✅ |
| 透過 MCP 層真呼叫一次 `start_tutorial`，uid 是 `s1-*` | ✅ |
| 手動 stdio 驗證 | ✅（做法 A′；做法 A 的限制已寫回文件） |
| Qoder MCP 設定 JSON 已寫好 | ✅ 文件已寫；**貼進 Qoder 需使用者手動** |
| allow list `mcp__showme__*` | ✅ 文件已寫；**設定需使用者手動** |
| Request Timeout 實測 | 🙋 **留給使用者手動**（需 Qoder IDE ＋ 真人） |
| `showme/**`、`overlay/**` 一行都沒改 | ✅ |
| commit | ⏸️ 依指示不做，主控統一處理 |

---

## 動到的檔案

```text
新增   tests/test_mcp_contract.py                        （10 條契約測試）
修改   tests/conftest.py                                  （只加 mcp_client fixture + 3 行 import）
修改   docs/plan/unfinish/A14_MCP契約測試與stdio.md        （見下方修正清單）
新增   docs/plan/report/2026-08-29-階段5Q_A14_MCP契約與stdio-REP.md（本檔）

沒動   showme/**、overlay/**、tests/ 其他檔（平行 agent 的地盤）
```

### 對 A14 文件做的修正

1. **Step 1 的 `structured_content` 那一格 + 底下方框**：改寫成 A01 的實測結論（裸 `dict` → `structured_content` 是 `None`；`dict[str, object]` → 裸 dict），附三行對照表，並說明 A07 已經改好、本篇不必碰產品程式碼。
2. **Step 3 的 `payload()` docstring**：同步成實際檔案的內容，assert 訊息加上「或回傳註記推不出 schema」。
3. **Step 3 的預期輸出**：加方框說明與 A11–A13 平行時 `end_tutorial` 那條會紅，是正確的紅燈，不要改測試。
4. **Step 4 做法 A**：標明實測只印得出 `initialize` 一行、原因是 EOF 搶時間；新增**做法 A′**（Python subprocess，附完整可跑腳本與實測輸出），並註明本機沒有 `timeout` / `gtimeout`。
5. **Step 4 做法 C**：補上「有 Node 但 npx 要現載 Inspector、35 秒沒起來所以跳過」的實況。
6. **Step 5**：補上 `command -v uv` 的實測絕對路徑備援 JSON。
7. **Step 7**：開頭加方框標「留給使用者手動」，量測步驟原文保留。
8. **Step 8**：註明平行執行時由主控統一 commit。
9. **§6.2、§8 驗收清單**：需要 Qoder IDE 的三項標上 🙋；stdio 那項改指向做法 A′。
10. **§9 排錯表**：新增 4 條（`structured_content is None` 但 `is_error` 是 False、A13 未完成的 `KeyError: 'ok'`、做法 A 只印一行、沒有 `timeout` 指令），並修正原本「改成 `dict[str, object]`」那條的敘述（A07 已經改過了）。

---

## 給下一篇的交接

1. **A15**：`mcp_client` fixture 可以直接用（已在 `tests/conftest.py`），要透過 MCP 層做端到端就 `async with` 它。
2. **A16**：Qoder 設定 JSON、allow list、Request Timeout 量測步驟都在 A14 Step 5–7；**Request Timeout 的數字還是空的，要使用者開 Qoder 量完才能填進 A16 的 demo checklist**。
3. `uv run mcp dev` 想用的話，先在終端機單獨跑一次等 npm 把 Inspector 裝完（第一次可能要好幾分鐘），之後有快取就快。
