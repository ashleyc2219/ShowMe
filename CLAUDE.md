# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 這是什麼

**ShowMe**：給 Qoder Coding Agent 用的 **stdio MCP server**。Agent 呼叫四個 tool，ShowMe 用 Playwright 開 headed Chrome、把 `overlay/overlay.js` 注入本機 web app（通常 `localhost:3000`），在真實頁面上畫箭頭教人操作。**人自己點／打字，ShowMe 只教不代做**；ShowMe 內沒有 LLM。這是 5 小時 hackathon 專案——**不要鑽牛角尖、不要為 MVP 以外的規模預留架構**。

## 目前狀態（2026-08-29）

- `showme/server.py` 是骨架：四個 `@mcp.tool()` 都回 `{"error": "not_implemented"}`。`overlay/overlay.js` 是 10 行 stub。
- `tests/` 是空的；`pyproject.toml` 還沒有 dev 依賴與 pytest 設定，也沒有 `uv.lock`——這些由 `docs/plan/unfinish/A01` 補上。
- 實作照 `docs/plan/unfinish/A00_導讀與總覽.md` → A16 的順序做（A00 有依賴圖）。完成的篇章從 `docs/plan/unfinish/` 搬到 `docs/plan/finish/`。

## 常用指令

全部在 repo 根目錄、以 `uv run` 開頭（不用 activate venv）。Python 釘在 **3.12**（`uv python pin 3.12`），`mcp` 必須是 **2.x**（`from mcp.server import MCPServer`；1.x 沒有這個 API）。

```bash
uv sync                                   # 建 .venv、裝依賴、產生 uv.lock（uv.lock 要進版控）
uv run playwright install chromium        # headless 測試用；demo 走 channel="chrome" 用本機 Chrome

uv run pytest                             # 全部
uv run pytest -m "not browser"            # 平常用：跳過會開瀏覽器的測試（最快）
uv run pytest -m browser                  # 只跑會開 headless Chromium 的測試
uv run pytest tests/test_rules.py         # 單一檔
uv run pytest tests/test_rules.py::test_timeout_zero_becomes_the_default   # 單一測試
uv run pytest -k timeout -x               # 關鍵字篩選、第一個紅燈就停

uv run showme                             # 手動啟動 MCP stdio server（Ctrl-C 結束）
uv run python scripts/dev_open.py <url>   # （A04 之後）headed 開一個網址、停 10 秒，用眼睛驗 Chrome 能開

./scripts/setup-sample-app.sh             # 拉 refine finefoods-antd 到 sample-app/（不進版控）
cd sample-app/finefoods-antd && npm run dev   # 示範站 → http://localhost:3000（腳本故意不幫你跑）
```

Qoder 接法（絕對路徑、一定要 `--directory`）：`{"mcpServers": {"showme": {"command": "uv", "args": ["--directory", "/Users/linjunting/hackathonQoder", "run", "showme"]}}}`；allow list 加 `mcp__showme__*`；IDE 的 Request Timeout 要調高，因為 `show_step` 會阻塞最長 120 秒。

## 架構

```text
Qoder Agent
    │  MCP stdio（server 名稱 "showme"；tool 全名 mcp__showme__<tool>）
    ▼
showme/（Python，工程師 A）      process 記憶體：至多一個 Session
    │  Playwright async：launch / goto / add_init_script / expose_function / evaluate
    ▼
Chrome（headed）
    ├── 產品頁 :3000                人自己操作
    └── overlay/overlay.js（B）     window.__showme.snapshot / show / clear / done
                                      └── window.__showme_emit(...) ──▶ 叫醒阻塞中的 show_step
```

單向相依，沒有反向呼叫、沒有頁面打 HTTP 回 Python、沒有 sidecar。

**A/B 分工（不要搶檔）：** A 改 `showme/**`、`tests/**`、`pyproject.toml`；B 改 `overlay/**`。A 只呼叫 overlay 不改它——要測 JS 呼叫，用 A 自己的 `tests/fixtures/fake_overlay.js` 測試替身，不是 B 的產品 overlay。`sample-app/` 是外部 example，不改。

**A/B 之間鎖死的名字**（`docs/handoff.md`，任何人都不准改）：

```text
A 呼叫：__showme.snapshot(n) → {elements:[{uid,role,name,testid}], truncated}
        __showme.show({uid, instruction, kind, index, total, expect})
        __showme.clear()   __showme.done(text)
B 呼叫：__showme_emit({kind: "step_done" | "stuck", url, ts})   每步恰好一次；B 不發 timeout
uid 格式 s{n}-{index}：n（snapshot#）由 Python 決定並傳進去，B 只組字串
```

### 規劃中的 Python 模組（A02–A07 建立；名字已鎖定，計劃文件都靠它們接）

```text
server.py ──▶ app.py ──▶ session.py      server.py：薄殼，MCPServer + 四個 tool 各 return await get_app().<同名>(...)
                 ├──▶ rules.py          app.py：ShowMeApp，真正的 tool 邏輯，透過 browser_factory 注入 BrowserLike
                 └──▶ browser.py ──▶ Playwright   session.py：Session / State / SessionStore / MAX_STEPS=12 / DEFAULT_TIMEOUT_S=120 / DONE_BANNER_TEXT
                                                  rules.py：純函數（normalize_timeout_s, normalize_kind, expect_text_missing, build_page, uid_in_page），不 import 專案內其他模組
                                                  browser.py：BrowserLike Protocol / PlaywrightBrowser / NavigationFailed；不知道 Session 與錯誤碼
tests/fakes.py：FakeBrowser（實作 BrowserLike、不開瀏覽器）；A07 之後的 tool 測試全靠它
```

## 不可違反的契約（來自已 clarified 的規格）

- **只有四個 tool**：`start_tutorial`、`inspect_page`、`show_step`、`end_tutorial`。不加第五個；`wait_for_user`、`off_script`、非阻塞輪詢是 Non-Goal。
- **tool 永遠 `return` dict、絕不 `raise`**：例外會讓 MCP 標 `is_error`。失敗寫在 `error` 欄；成功時 `error=""`（不是 `None`）。回傳的鍵永遠都在。
- **只准這六個錯誤碼**：`navigation_failed`、`session_not_found`、`max_steps_exceeded`、`uid_not_in_snapshot`（仍附新鮮 page）、`expect_text_required`、`show_step_in_progress`。`step_done` / `stuck` / `timeout` 是 `event`，不是錯誤。
- **Session**：同 process 至多一個；狀態只有 READY / SHOWING（沒有 IDLE 物件、沒有 DONE；`end_tutorial` 成功就刪除）；沒有 ttl。`start_tutorial` 任何時候可呼叫（有 Session 則覆蓋：同 `session_id`、新 goal、`steps_shown=0`、snapshot# 重回 1）。
- **show_step**：uid 必須在**最新** page.elements；通過才 `steps_shown+1`（含 stuck 後同 uid 重畫）；`steps_shown >= 12` 拒絕；畫出後**阻塞**直到 emit 或 Python 本地 timer（`elapsed_s >= timeout_s` 即 timeout，含剛好相等）；SHOWING 時第二個 show_step 回 `show_step_in_progress`，第一個繼續等。`kind` 不在 click/input/select/observe 內視為 observe；observe 且 `expect_text` 空 → `expect_text_required`（不畫、不加步數）。`timeout_s` 未傳/0/負 → 120。
- **snapshot**：角色白名單（button, link, textbox, checkbox, radio, combobox, menuitem, tab, heading, alert）、DOM 順序硬上限 150（超過 → 丟棄、`truncated=true`），`testid` 鍵永遠存在（沒有就 `""`）。每次產生 snapshot 時 snapshot# +1（start=1、inspect +1、show_step 回傳附 page 時 +1，含 `uid_not_in_snapshot`）。
- **完成判定在 overlay**，Python 只等第一個 emit 或 timer。click 只認「目標移除／隱藏、URL 變更、按 Next」；**不**數 DOM mutation、**不**等 HTTP。
- `end_tutorial` 的 banner 文案固定 `✅ Done — you created a project`，**忽略 summary**。
- 技術選擇已否決：sync Playwright（會卡 asyncio）、`src/` 佈局、FastAPI/HTTP sidecar、資料庫、chrome-devtools-mcp、headless 當 demo（人要看到箭頭）。

A 側對規格空隙的決定（可改，不是驗收條件；改了要同步 A00 §10.2）：SHOWING 時 `inspect_page`/`end_tutorial` 回 `show_step_in_progress`；SHOWING 時被 `start_tutorial` 覆蓋，卡住的 show_step 回 `event="timeout"`、`page=None`；導航失敗不建立 Session；`end_tutorial` 不關瀏覽器；timeout 後 `clear()`；`elapsed_s` 取一位小數；`expose_function` 掛在 context 層。

## 文件的優先序（衝突時上面贏）

1. `docs/spec/.clarify/resolved/**`（26 份解決記錄）
2. `docs/spec/erm.dbml` + `docs/spec/features/*.feature`（Gherkin 驗收；只有 `#TODO` 的 Rule 不要自己發明例子當需求）
3. `docs/design/showme.md`（canonical design；`design-draft.md` 早於 clarify，其中被推翻的敘述列在 §2，不得回流）
4. `docs/plan/unfinish/A00–A16`（A 側逐步實作計劃）

`docs/handoff.md` 是 A/B 接縫一頁版。**`docs/plan/dev-prompts/phase0829.md` 是別的專案殘留，不要讀、不要當需求。**

## 開發節奏

- 一篇一篇照 A00 的依賴圖做，不跳篇；每篇做完要 `uv run pytest -m "not browser"` 全綠、`git status` 乾淨。
- TDD：先寫測試看它紅，再寫最小實作看它綠；沒紅過的測試不算數。
- 測試慣例：async 測試檔開頭 `pytestmark = pytest.mark.anyio`（`conftest.py` 的 `anyio_backend` 固定回 `"asyncio"`）；會開瀏覽器的加 `@pytest.mark.browser`；in-memory MCP 測試用 `from mcp import Client` + `async with Client(mcp) as client`；tool 回傳 dict 時 `structured_content` 就是那個 dict。
- Commit 用 conventional commits（`chore:` / `test:` / `feat:` / `docs:`），只 `git add` 本篇動到的檔案，不要 `git add -A`。
- 使用者是 A（Python 側）、自述新手：給他的說明用 zh-TW、白話、多 ASCII 圖，範圍只到 `showme/` + `tests/`。
