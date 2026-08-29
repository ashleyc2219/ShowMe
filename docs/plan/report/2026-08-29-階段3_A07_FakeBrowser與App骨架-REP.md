# A07｜FakeBrowser 與 App 骨架 — 實作報告

- 日期：2026-08-29
- 對應計劃：`docs/plan/unfinish/A07_FakeBrowser與App骨架.md`
- 狀態：**驗收全過**（Step 8 的 commit 依指示不做，由主控統一 commit）

---

## 實作邏輯

A07 把「MCP 這一層」與「教學邏輯這一層」切開，讓邏輯測試不必啟動 MCP、也不必開瀏覽器。

```text
   MCP Client（Qoder / tests 的 in-memory Client）
        │ stdio
        ▼
   showme/server.py            ← 薄殼：MCPServer + 四個 @mcp.tool()
        │                         每個 tool 本體只有一行 return await get_app().<同名>(...)
        ▼
   showme/app.py  ShowMeApp    ← 全部邏輯：Session、snapshot#、emit 收件、瀏覽器生命週期
        │ 只認得 BrowserLike 這個介面
        ▼
   ┌──────────────────────┬──────────────────────────┐
   │ showme/browser.py    │ tests/fakes.py           │
   │ PlaywrightBrowser    │ FakeBrowser              │
   │ 真的開 Chrome        │ 只有一個 dict，不開瀏覽器 │
   └──────────────────────┴──────────────────────────┘
        正式跑用左邊              A08–A13 測試用右邊
   ※ 換哪一個由 ShowMeApp(browser_factory=...) 決定。
```

三個內部方法**完整實作**，四個 tool 方法先回 `{"error": "not_implemented"}` 佔位：

```text
_ensure_browser   沒有瀏覽器或 is_alive() 是 False → factory 建一顆 → launch()
                  → set_emit_handler(self._on_emit) → 存起來重用

_take_snapshot    session.snapshot_no += 1 → browser.snapshot(n)
                  → build_page(raw, current_url(), title()) → 存進 session.latest_page

_on_emit（同步）  三道門，任何一道沒過就 return、不丟例外：
                  ① store.current() is None ？
                  ② session.state != SHOWING ？
                  ③ pending is None or pending.done() ？
                  三道都過才 pending.set_result(event)  ← 每步只取第一筆事件

shutdown          有瀏覽器才 close()，然後把握把清成 None
```

`FakeBrowser` 的關鍵設計：`snapshot(n)` 用 `dict(element, uid=f"s{n}-{i+1}")` **依 n 重編 uid**（複製再覆蓋，不污染 `self.pages`），跟真 overlay 的分工一致（A 給 `n`、B 組字串）；`calls` 只記「ShowMe 對瀏覽器做了什麼」，所以模擬使用者換頁的 `navigate()` 刻意不記；`open()` 失敗時 `raise` 在 `append` 之前，A08 才能斷言「navigation_failed 沒留下 open 記錄」。

---

## 步驟

| Step | 做了什麼 | 結果 |
|---|---|---|
| 0 | 先記下基準：`uv run pytest -m "not browser" -q` | `53 passed, 18 deselected` |
| 1 | 新增 `tests/fakes.py`（`FakeBrowser`） | 11 個 BrowserLike 方法 + `emit` / `navigate` / `add_page` |
| 2 | `tests/conftest.py` 加 `fake_browser` / `app` / `started` | 保留原有 `anyio_backend` / `static_server`，共五個 fixture |
| 3 | 新增 `tests/test_fakes.py`，先跑看紅 | **紅**：`ModuleNotFoundError: No module named 'showme.app'` |
| 4 | 新增 `showme/app.py` 骨架 | 三個內部方法 + `shutdown` 完整；四個 tool 佔位 |
| 5 | `showme/server.py` 改薄殼 | `INSTRUCTIONS` / `mcp` / `get_app` / `set_app` / 四個 tool |
| 6 | 跑測試看綠 | `21 passed`；全體 `74 passed` = 53 + 21 |
| 7 | 驗 `uv run showme` 還起得來 | 起得來、阻塞等 stdin、SIGTERM 收得掉（exit 143） |
| 8 | commit | **依指示不做**，留給主控 |

### 動到的檔案

```text
新增   tests/fakes.py
新增   tests/test_fakes.py
新增   showme/app.py
修改   showme/server.py                 （整檔換成薄殼）
修改   tests/conftest.py                （只加三個 fixture，原有兩個一字沒動）
修改   docs/plan/unfinish/A07_FakeBrowser與App骨架.md   （回傳註記修正，見下方）
新增   docs/plan/report/2026-08-29-階段3_A07_FakeBrowser與App骨架-REP.md   （本檔）

沒動   overlay/**、showme/browser.py、showme/session.py、showme/rules.py、showme/__main__.py
      A02–A06 的測試檔（test_session / test_rules / test_browser_*）
```

---

## 測試方式

**TDD 節奏：**

```text
寫 fakes.py + conftest fixture + test_fakes.py
      │
      ▼
uv run pytest tests/test_fakes.py -q  →  ModuleNotFoundError: showme.app（紅）★
      │                                   conftest 最上面就 import 不到，整包收集不了
      ▼
寫 showme/app.py                      →  21 passed（綠）
      ▼
server.py 改薄殼                       →  再跑一次確認 A01 smoke test 沒被打壞
```

紅燈是**預期中的**：`conftest.py` 開頭 `from showme.app import ShowMeApp`，模組不存在時整個 `tests/` 都收集不了，所以是 collection error 而不是一堆 F。

**跑的指令：**

```bash
uv run pytest tests/test_fakes.py -q      # 本篇 21 條
uv run pytest -m "not browser" -q         # 最重要：A01 smoke test 在薄殼改寫後仍要綠
uv run pytest -m browser -q               # 確認 A04–A06 的 18 條瀏覽器測試沒被弄壞
```

**額外做的兩項人工驗證：**

1. **`uv run showme` 起得來**——這台 macOS 沒有 `timeout` 指令（A01 已記錄），改用 Python supervisor：`subprocess.Popen(["uv","run","showme"])` → 等 5 秒 → `poll() is None` → `terminate()`。
2. **`started` fixture 真的解得開**——A07 的 `start_tutorial` 還是佔位，文件說這個 fixture 「A08 之後才有用」，但我還是丟一支拋棄式測試進去驗它在 anyio 下作為 async fixture 能正常解析（`1 passed`），驗完就刪掉。這樣 A08 不會被「fixture 本身寫壞」浪費時間。

---

## 遇到的問題與怎麼解決

### 1. 四個 tool 的回傳註記要用 `dict[str, object]`，不能用裸 `dict`（已修正 A07 文件）

A07 文件裡 `server.py` 與 `app.py` 的四個方法都寫 `-> dict`。但 **A01 實測**（`docs/plan/report/2026-08-29-階段1_A01環境建置-REP.md`「遇到的問題與怎麼解決」第 1 點）已經發現：mcp 2.1.1 是**從回傳型別註記推導 output schema** 的，沒有參數的裸 `dict` 推不出 schema，`structured_content` 就會是 `None`（dict 內容只會以 JSON 字串塞在 `content[0].text`）。

所以本篇實作時直接照 A01 的結論寫成 `dict[str, object]`，並把 A07 文件那 12 行（§6 介面表 4 行、Step 4 的 `app.py` 4 行、Step 5 的 `server.py` 4 行）一併改掉，Step 5 的注意事項也加了一條說明原因、指回 A01 報告。

改完實測（in-memory `Client(mcp)` 呼叫 `inspect_page`）：

```text
output_schema      = {'additionalProperties': True, 'title': 'inspect_pageDictOutput', 'type': 'object'}
is_error           = False
structured_content = {'error': 'not_implemented'}     ← 裸 dict，不是 None、也不是 {"result": ...}
```

A14 寫契約測試時可以直接靠 `structured_content` 了。

### 2. `_take_snapshot` 的註記維持 `-> dict`

只有**經過 MCP 曝光**的四個方法需要 `dict[str, object]`（那是 schema 推導的輸入）。`_take_snapshot` 是內部方法，不會被 mcp 看到，維持文件原本的 `-> dict`，避免無謂的差異。

### 3. `git status` 有兩個不是我動的檔案

跑驗收時看到 `docs/plan/dev-prompts/phase0829.md`（M）與 `CLAUDE.md`（??）出現在 `git status` 裡。**這兩個都不是 A07 動的**（本篇只碰 §5 那五個檔案 + A07 計劃文件 + 本報告），推測是主控或平行作業留下的。我沒有去改也沒有還原，留給主控判斷。

---

## 測試結果

### `uv run pytest tests/test_fakes.py -q`

```text
.....................                                                    [100%]
21 passed in 0.03s
```

21 = 17 條 + 4 個 parametrize，跟文件預期一致。

### `uv run pytest -m "not browser" -q`

```text
........................................................................ [ 97%]
..                                                                       [100%]
74 passed, 18 deselected in 0.77s
```

74 = 基準 53 + 本篇 21 ✅。**A01 的兩條 smoke test（恰好四個 tool、沒有 `wait_for_user`）在 `server.py` 被整個換掉之後仍然綠**——這是本篇最重要的驗收。

### `uv run pytest -m browser -q`

```text
..................                                                       [100%]
18 passed, 74 deselected in 21.51s
```

A04–A06 的瀏覽器測試沒被影響 ✅

### `uv run showme`

```text
still running after 5s = True
exit = 143
stdout = b''
stderr = b''
```

沒有任何輸出、5 秒後還活著（阻塞等 stdin）、SIGTERM 收得掉 ✅

### 驗收清單

| 項目 | 結果 |
|---|---|
| `FakeBrowser` 有 BrowserLike 全部 11 個方法 + `emit` / `navigate` / `add_page` | ✅（`test_fake_browser_has_every_browser_like_method`） |
| `_ensure_browser` / `_on_emit` / `_take_snapshot` / `shutdown` 完整實作 | ✅ |
| 四個 tool 方法都回 `{"error": "not_implemented"}`、簽名與 §6 一致 | ✅（`show_step` 八個參數、兩個預設值） |
| `server.py` 是薄殼，每個 tool 本體只有一行 | ✅ |
| `conftest.py` 有五個 fixture | ✅ `anyio_backend` / `static_server` / `fake_browser` / `app` / `started` |
| `uv run pytest tests/test_fakes.py -q` → 21 passed | ✅ |
| `uv run pytest -m "not browser" -q` 全綠、A01 smoke 仍過 | ✅ 74 passed |
| `uv run pytest -m browser -q` 全綠 | ✅ 18 passed |
| `uv run showme` 起得來、收得掉 | ✅ |
| `grep -rn "not_implemented" showme/` 只在 `app.py` 出現四次 | ✅（`server.py` 已無） |
| `overlay/**`、`browser.py`、`session.py`、`rules.py`、`__main__.py` 沒被改 | ✅ |
| commit | ⏸️ 依指示不做，由主控統一處理 |

---

## 給下一篇（A08）的交接

1. **`app` / `fake_browser` fixture 直接用**：`app` 的 factory 每次都回同一顆 `fake_browser`，所以測試可以對 `fake_browser` 下 `emit()` / `navigate()`、也可以讀 `calls`。**不要自己 `ShowMeApp()`**，那會用預設的 `PlaywrightBrowser`、真的跳一顆 Chrome 出來。
2. **`started` fixture 機制上已經可用**（async fixture 在 anyio 下解得開，我驗過），但它的 `result` 現在是 `{"error": "not_implemented"}`——A08 把 `start_tutorial` 實作完，它就自動變成真的了，fixture 本身不用改。
3. **A08 要順手刪掉** `tests/test_fakes.py` 最後那個 parametrize 的第一行（`start_tutorial` 那條），否則它會紅。A10 刪 `inspect_page`、A12 刪 `show_step`、A13 刪 `end_tutorial`，A13 之後整個 `test_tool_methods_are_placeholders_for_now` 就沒了。
4. **`app.py` 有一批目前沒用到的 import**（`NavigationFailed`、`normalize_kind`、`normalize_timeout_s`、`expect_text_missing`、`uid_in_page`、`MAX_STEPS`、`START_NEXT_ACTION`、`STEP_NEXT_ACTION`、`DONE_BANNER_TEXT`、`asyncio`）——這是刻意的，A08–A13 只要動函式本體，不用回頭改 import 區塊。
5. **`DASHBOARD_URL` 結尾有斜線**（`http://localhost:3000/`）。`FakeBrowser` 是用字串精確比對查頁面的，測試裡請用 `conftest` 的常數，不要手打。
6. **回傳註記一律 `dict[str, object]`**（原因見上方問題 1）。A08 之後新增／改寫 tool 方法時不要退回裸 `dict`。
