# A08｜start_tutorial（新建場次）

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：`A07_FakeBrowser與App骨架.md` ｜ 下一篇：`A09_start_tutorial覆蓋場次.md`
> 對應設計：`docs/design/showme.md` §6（端到端流程）、§7.1（tool 契約）、§10（snapshot 與 uid）、§13（錯誤語意）｜ 對應切片：S5
> 預估時間：45–60 分鐘

---

## 1. 這一篇要做什麼

把 `ShowMeApp.start_tutorial()` 從 A07 的佔位 `{"error": "not_implemented"}` 改成真的會做事：**開瀏覽器 → 開網址 → 建立 Session → 拍第一份濃縮 page（uid 是 `s1-*`）→ 回傳 TutorialStart 形狀的 dict**。

這一篇只做「**目前沒有 Session**」的新建路徑，以及「網址開不起來」的失敗路徑。「Session 還在時再呼叫一次 start_tutorial」的覆蓋行為留給 A09。

全部測試都用 `FakeBrowser`，**不會開任何瀏覽器視窗**。

---

## 2. 做完會看到什麼

### 2.1 一次 `start_tutorial` 呼叫的資料流

```text
Qoder Agent
   │  MCP stdio：call_tool("start_tutorial", {"url": ..., "goal": ...})
   ▼
showme/server.py   @mcp.tool() async def start_tutorial(url, goal)      ← A07 已寫好的薄殼
   │  return await get_app().start_tutorial(url, goal)
   ▼
showme/app.py      ShowMeApp.start_tutorial(url, goal)                  ← 本篇要寫的
   │
   ├─(1) browser = await self._ensure_browser()   沒有瀏覽器或已死才新建 + launch()
   ├─(2) await browser.open(url)                  開不了 → 丟 NavigationFailed
   ├─(3) session = self.store.create(goal)        Session(state=READY, steps_shown=0, snapshot_no=0)
   └─(4) page = await self._take_snapshot(session) snapshot_no 0 → 1，uid 變成 s1-*
   ▼
{"session_id": "s_8f2a", "goal": "create a project",
 "page": {"url": ..., "title": ..., "elements": [...], "truncated": False},
 "next_action": START_NEXT_ACTION, "error": ""}
```

### 2.2 回傳形狀（鍵永遠都在，只有值會變）

```text
result
├── session_id : "s_8f2a"                成功才有值；失敗時是 ""
├── goal       : "create a project"      原樣回傳（可為空字串，不 trim）
├── page       : {...} 或 None
│      ├── url       : "http://localhost:3000/"
│      ├── title     : "Dashboard"
│      ├── elements  : [{uid, role, name, testid}, ...]   最多 150 筆
│      └── truncated : False
├── next_action: START_NEXT_ACTION       失敗時是 ""
└── error      : ""  或  "navigation_failed"
```

### 2.3 兩條路，只有兩條

```text
start_tutorial(url, goal)
        │
        ├── open(url) 成功 ──▶ store.create(goal) ──▶ 拍 snapshot #1 ──▶ error=""
        │                                                              state=READY
        │                                                              steps_shown=0
        │
        └── open(url) 丟 NavigationFailed ──▶ store.delete() ──────────▶ error="navigation_failed"
                                                                        session_id=""
                                                                        page=None
                                                                        store.current() is None
```

> 「導航失敗就不留 Session」是 **A 的設計決定（可改）**，不是規格。規格只寫「操作失敗且錯誤為 `navigation_failed`」，沒有寫 Session 要不要留。我們選「不留」，因為這樣 `session_id=""` 才不會誤導 agent 去用一個沒有頁面的場次。

---

## 3. 開始前先確認

- [ ] A01–A07 的驗收都打勾了。
- [ ] `showme/session.py` 存在，裡面有 `MAX_STEPS`、`DEFAULT_TIMEOUT_S`、`DONE_BANNER_TEXT`、`START_NEXT_ACTION`、`STEP_NEXT_ACTION`、`State`、`Session`、`SessionStore`、`new_session_id`。
- [ ] `showme/rules.py` 存在，裡面有 `normalize_timeout_s`、`normalize_kind`、`expect_text_missing`、`build_page`、`uid_in_page`、`empty_page`。
- [ ] `showme/browser.py` 存在，裡面有 `NavigationFailed`、`BrowserLike`、`PlaywrightBrowser`。
- [ ] `showme/app.py` 存在，`ShowMeApp` 已經有 `__init__`、`_ensure_browser`、`_on_emit`、`_take_snapshot`、`shutdown`；四個 tool 方法目前都只 `return {"error": "not_implemented"}`。
- [ ] `showme/server.py` 是薄殼（`INSTRUCTIONS`、`get_app()`、`set_app()`、四個 `@mcp.tool()` 各自轉呼叫 `get_app()` 的同名方法）。
- [ ] `tests/fakes.py` 有 `FakeBrowser`，它有 `emit()`、`navigate()`、`add_page()` 三個測試用方法。
- [ ] `tests/conftest.py` 有 `anyio_backend`、`fake_browser`、`app`、`started` 四個 fixture。
- [ ] 這個指令可以跑而且全綠：

```bash
uv run pytest -m "not browser" -q
```

預期輸出最後一行類似（數字會因為你前面寫了幾條測試而不同）：

```text
74 passed, 18 deselected in 0.58s
```

如果這裡不是全綠，**先回去修 A01–A07，不要往下做**。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| Session（場次） | 一次教學的記事本：誰在教（`session_id`）、教什麼（`goal`）、現在是等待中還是畫箭頭中（`state`）、已經畫了幾步（`steps_shown`）、最新一份頁面清單（`latest_page`）。整個 process 最多只有一份。 |
| `SessionStore` | 放那一份 Session 的抽屜。`create()` 放新的（舊的直接被取代）、`current()` 看現在有沒有、`get(id)` 用 id 拿（對不上就 `None`）、`delete()` 清空。 |
| snapshot（快照） | 「現在這一頁上有哪些可以點的東西」的清單，不是螢幕截圖。是一個 list，每筆有 `uid`、`role`、`name`、`testid`。 |
| snapshot#（世代編號） | 第幾份快照。`start_tutorial` 成功時是 1，之後每重拍一次就 +1。它被寫進 uid 前綴，所以 `s1-4` 和 `s2-4` 是不同世代的同一個位置。 |
| `uid` | 元素的暫時代號，格式 `s{snapshot#}-{index}`。agent 只能用最新一份清單裡的 uid，這樣就不會拿舊清單亂指。 |
| `FakeBrowser` | 測試替身：長得跟真的瀏覽器一樣（同樣的方法名），但什麼都不開，只把被呼叫的動作記在 `calls` 裡。跑得快、不閃視窗。 |
| fixture | pytest 幫你事先準備好的東西。測試函數的參數名寫成 fixture 的名字，pytest 就會自動把它塞進來。 |
| `pytestmark = pytest.mark.anyio` | 寫在測試檔最上面的一行，意思是「這個檔案裡的 `async def` 測試請用 anyio 幫我跑起來」。沒有這行，async 測試會被跳過。 |
| `NavigationFailed` | 我們自己定義的例外（exception）。`PlaywrightBrowser.open()` 遇到 `page.goto` 出錯時丟出來，`start_tutorial` 接住它、轉成 `error="navigation_failed"`。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 修改 | `showme/app.py` | 只改 `ShowMeApp.start_tutorial()` 一個方法。其他方法一律不動。 |
| 新增 | `tests/test_tool_start.py` | `start_tutorial` 的行為測試（不開瀏覽器）。A09 會在同一個檔案後面繼續加測試。 |
| 修改 | `tests/test_fakes.py` | 只刪掉最後那個 parametrize 裡 `start_tutorial` 那一行（它已經不是佔位了）。 |

**不要動**：`showme/server.py`、`showme/session.py`、`showme/rules.py`、`showme/browser.py`、`tests/fakes.py`、`tests/conftest.py`、`overlay/**`。

---

## 6. 介面約定

### 6.1 用到（來自前面幾篇，這裡重述精確簽名，不用回頭翻）

`showme/session.py`：

```python
MAX_STEPS = 12
DEFAULT_TIMEOUT_S = 120.0
DONE_BANNER_TEXT = "✅ Done — you created a project"
START_NEXT_ACTION = (
    "Plan 3–8 steps in your head, then call show_step for the FIRST step "
    "using a uid from page.elements."
)

class State(str, Enum):
    READY = "READY"
    SHOWING = "SHOWING"

@dataclass
class Session:
    session_id: str
    goal: str
    state: State = State.READY
    steps_shown: int = 0
    snapshot_no: int = 0
    latest_page: dict | None = None
    pending: asyncio.Future | None = None
    def uids(self) -> set[str]: ...

class SessionStore:
    def current(self) -> Session | None: ...
    def get(self, session_id: str) -> Session | None: ...
    def create(self, goal: str) -> Session: ...   # 新 id、READY、steps_shown=0、snapshot_no=0，並取代舊的
    def delete(self) -> None: ...                 # 沒有 Session 時呼叫也不會爆
```

`showme/browser.py`：

```python
class NavigationFailed(Exception): ...

class BrowserLike(Protocol):
    async def launch(self) -> None: ...
    async def is_alive(self) -> bool: ...
    async def open(self, url: str) -> None: ...   # 開不了就 raise NavigationFailed
    async def current_url(self) -> str: ...
    async def title(self) -> str: ...
    async def snapshot(self, n: int) -> dict: ...
    async def show(self, opts: dict) -> None: ...
    async def clear(self) -> None: ...
    async def done(self, text: str) -> None: ...
    def set_emit_handler(self, handler) -> None: ...
    async def close(self) -> None: ...
```

`showme/app.py`（A07 已完成的部分）：

```python
class ShowMeApp:
    def __init__(self, browser_factory: BrowserFactory = PlaywrightBrowser) -> None: ...
    async def _ensure_browser(self) -> BrowserLike:
        """沒有瀏覽器或已死 → factory() 建一個並 launch()；並 set_emit_handler(self._on_emit)。"""
    async def _take_snapshot(self, session: Session) -> dict:
        """session.snapshot_no += 1 → raw = browser.snapshot(n) → page = build_page(raw, url, title)
        → session.latest_page = page → return page"""
```

`showme/app.py` 檔頭應該已經有這些 import（A07 寫的）；少了哪一行就補上：

```python
from __future__ import annotations

import asyncio
from typing import Callable

from showme.browser import BrowserLike, NavigationFailed, PlaywrightBrowser
from showme.rules import build_page, expect_text_missing, normalize_kind, normalize_timeout_s, uid_in_page
from showme.session import (DEFAULT_TIMEOUT_S, DONE_BANNER_TEXT, MAX_STEPS, START_NEXT_ACTION,
                            STEP_NEXT_ACTION, Session, SessionStore, State)
```

`tests/conftest.py` 的 fixture：

```python
fake_browser  # FakeBrowser()，已經 add_page 兩頁：
              #   "http://localhost:3000/"             title "Dashboard"
              #       [{"role":"button","name":"New Project","testid":"new-project"},
              #        {"role":"link","name":"Settings","testid":""}]
              #   "http://localhost:3000/projects/new" title "New Project"
              #       [{"role":"heading","name":"New Project","testid":""},
              #        {"role":"textbox","name":"Project name","testid":"project-name"},
              #        {"role":"button","name":"Create","testid":"create"}]
app           # ShowMeApp(browser_factory=lambda: fake_browser)
started       # 已呼叫 await app.start_tutorial("http://localhost:3000/", "create a project")
              # 回傳 tuple (app, fake_browser, result)
```

### 6.2 提供（給後面幾篇）

```python
async def start_tutorial(self, url: str, goal: str) -> dict[str, object]
# 成功：{"session_id": str, "goal": str, "page": dict, "next_action": START_NEXT_ACTION, "error": ""}
# 失敗：{"session_id": "",  "goal": str, "page": None, "next_action": "",                "error": "navigation_failed"}
```

A09 會在同一個方法裡加「覆蓋既有場次」；A10–A13 會依賴「start 之後 `store.current()` 一定有一個 READY 的 Session，而且 `latest_page` 的 uid 是 `s1-*`」。

---

## 7. 步驟

### Step 1：建立測試檔，寫第一個測試（先看它紅）

建立 `tests/test_tool_start.py`，內容如下（整檔貼上）：

```python
"""start_tutorial 的行為測試。全部用 FakeBrowser，不開瀏覽器。"""

from __future__ import annotations

import pytest

from fakes import FakeBrowser
from showme.app import ShowMeApp
from showme.session import START_NEXT_ACTION, State

pytestmark = pytest.mark.anyio

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"
BAD_URL = "http://localhost:1/"


# Rule: 成功開始後回傳的 goal 等於傳入的 goal
async def test_start_returns_the_same_goal(app):
    result = await app.start_tutorial(DASHBOARD_URL, "create a project")

    assert result["goal"] == "create a project"
    assert result["error"] == ""
    assert result["session_id"] != ""
```

兩件事先講清楚，免得你卡住：

1. **`from fakes import FakeBrowser`，不是 `from tests.fakes import ...`。** `tests/` 資料夾裡沒有 `__init__.py`，pytest 會把 `tests/` 這個資料夾本身放進 `sys.path`，所以模組名就是 `fakes`。
2. **網址結尾要有斜線。** `FakeBrowser.open(url)` 是「你給什麼就記什麼」，不會像真瀏覽器那樣把 `http://localhost:3000` 補成 `http://localhost:3000/`。conftest 註冊的頁面 key 是 `http://localhost:3000/`，所以測試一律傳結尾有斜線的網址。（真的 Playwright 會自己補，A15 的真瀏覽器測試會看到。）

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期看到紅燈，重點行是：

```text
E       KeyError: 'goal'
...
1 failed in 0.09s
```

（`KeyError` 是因為 A07 的佔位只回 `{"error": "not_implemented"}`，裡面沒有 `goal` 這個鍵。看到紅燈就是對的。）

---

### Step 2：寫最小實作（讓它綠）

打開 `showme/app.py`，把 `start_tutorial` 整個換掉：

```python
    async def start_tutorial(self, url: str, goal: str) -> dict[str, object]:
        browser = await self._ensure_browser()
        await browser.open(url)
        session = self.store.create(goal)
        page = await self._take_snapshot(session)
        return {
            "session_id": session.session_id,
            "goal": session.goal,
            "page": page,
            "next_action": START_NEXT_ACTION,
            "error": "",
        }
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
1 passed in 0.09s
```

**這段做了什麼（逐行）：**

- `await self._ensure_browser()`：第一次呼叫會用 `browser_factory()` 造一個瀏覽器並 `launch()`；之後只要它還活著就沿用同一個。測試裡 factory 回的是 `FakeBrowser`。
- `await browser.open(url)`：`FakeBrowser` 會把 `("open", url)` 記進 `calls`，並把 `self.url` 換成這個網址。
- `self.store.create(goal)`：產生新的 `session_id`、`state=READY`、`steps_shown=0`、`snapshot_no=0`，並取代抽屜裡舊的那份。
- `self._take_snapshot(session)`：把 `snapshot_no` 從 0 加到 1、呼叫 `browser.snapshot(1)`、用 `build_page()` 補上 `url`/`title` 並套 150 上限、把結果存進 `session.latest_page` 再回傳。

---

### Step 3：補「回傳的 page 長什麼樣」的測試

在 `tests/test_tool_start.py` 最後加上：

```python
# Rule: 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1
async def test_start_returns_the_first_page(started):
    app, fake, result = started

    page = result["page"]
    assert page["url"] == DASHBOARD_URL
    assert page["title"] == "Dashboard"
    assert page["truncated"] is False
    assert page["elements"] == [
        {"uid": "s1-1", "role": "button", "name": "New Project", "testid": "new-project"},
        {"uid": "s1-2", "role": "link", "name": "Settings", "testid": ""},
    ]


# Rule: 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1
async def test_start_uids_are_the_first_generation(started):
    app, fake, result = started

    uids = [element["uid"] for element in result["page"]["elements"]]
    assert uids != []
    assert all(uid.startswith("s1-") for uid in uids)


# Rule: page.elements 的 testid 鍵永遠存在，沒有 data-testid 時為空字串
async def test_start_elements_always_have_a_testid_key(started):
    app, fake, result = started

    settings = [e for e in result["page"]["elements"] if e["name"] == "Settings"][0]
    assert "testid" in settings
    assert settings["testid"] == ""
    for element in result["page"]["elements"]:
        assert set(element) == {"uid", "role", "name", "testid"}


# Rule: 成功開始後回傳的 next_action 與 error（回傳形狀固定）
async def test_start_result_has_all_five_keys(started):
    app, fake, result = started

    assert set(result) == {"session_id", "goal", "page", "next_action", "error"}
    assert result["next_action"] == START_NEXT_ACTION
    assert result["error"] == ""
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
5 passed in 0.10s
```

**為什麼這幾條不需要改實作就綠？** 因為它們驗的是 A03 的 `build_page()` 與 A07 的 `_take_snapshot()` 已經處理好的事情。它們的價值是**回歸測試**：A09、A12 之後還會改 `start_tutorial`，這幾條會替你守住回傳形狀不被改壞。TDD 不是「每條測試都必須先紅」，而是「不能有沒被測試守住的行為」。

**關於規格例子裡的 `s1-4` 與 `s1-7`：** `開始教學.feature` 的 Example 寫的是

```gherkin
| uid  | role   | name        | testid      |
| s1-4 | button | New Project | new-project |
| s1-7 | link   | Settings    |             |
```

那是真實 Dashboard 頁上，New Project 剛好排在第 4 個、Settings 排在第 7 個。我們的 `FakeBrowser` 只放了兩個元素，所以是 `s1-1`、`s1-2`。**這條 Rule 要驗的是「snapshot# 為 1」，不是「index 一定是 4 和 7」**，所以 `test_start_uids_are_the_first_generation` 才是對這條 Rule 的正面驗收。真實頁面的 index 由 overlay（B）決定，A15 會在真瀏覽器上再看一次。

---

### Step 4：補「Session 狀態」的測試

在檔案最後加上：

```python
# Rule: 成功開始後 session 狀態為 READY
async def test_start_leaves_the_session_ready(started):
    app, fake, result = started

    session = app.store.current()
    assert session is not None
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 1
    assert session.session_id == result["session_id"]
    assert session.session_id.startswith("s_")
    assert session.goal == "create a project"
    assert session.latest_page == result["page"]
    assert session.pending is None
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
6 passed in 0.10s
```

`snapshot_no == 1` 這行就是規格「snapshot# 從 1 起算」的直接驗收；`state is State.READY` 是「成功開始後 session 狀態為 READY」。

---

### Step 5：空 goal 也要成功

在檔案最後加上：

```python
# Rule: goal 為空字串時仍成功開始
async def test_start_accepts_an_empty_goal(app):
    result = await app.start_tutorial(DASHBOARD_URL, "")

    assert result["error"] == ""
    assert result["goal"] == ""
    assert app.store.current().state is State.READY
    assert app.store.current().goal == ""
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
7 passed in 0.10s
```

規格（`開始教學_goal為空字串時是否操作失敗.md`，答案 B）寫得很清楚：**空字串不是錯誤，而且不 trim**。所以實作裡不可以偷加 `if not goal: return ...`，也不可以 `goal.strip()`。

---

### Step 6：網址開不起來 → `navigation_failed`（這一步會先紅）

在檔案最後加上：

```python
# Rule: 目標 url 無法開啟時操作失敗且錯誤為 navigation_failed
async def test_start_returns_navigation_failed_when_the_url_cannot_open():
    browser = FakeBrowser(fail_urls={BAD_URL})
    app = ShowMeApp(browser_factory=lambda: browser)

    result = await app.start_tutorial(BAD_URL, "create a project")

    assert result["error"] == "navigation_failed"
    assert result["session_id"] == ""
    assert result["page"] is None
    assert result["next_action"] == ""
    assert result["goal"] == "create a project"
    # A 的設計決定（可改）：導航失敗不留下 Session
    assert app.store.current() is None


# Rule: 目標 url 無法開啟時操作失敗且錯誤為 navigation_failed
async def test_start_failure_does_not_take_a_snapshot():
    browser = FakeBrowser(fail_urls={BAD_URL})
    app = ShowMeApp(browser_factory=lambda: browser)

    await app.start_tutorial(BAD_URL, "create a project")

    assert not any(call[0] == "snapshot" for call in browser.calls)
    assert not any(call[0] == "show" for call in browser.calls)
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期紅燈，重點行是：

```text
E       showme.browser.NavigationFailed: cannot open http://localhost:1/
...
2 failed, 7 passed in 0.11s
```

例外直接炸出來，因為現在的實作沒有接住它。**這正是我們要修的**：MCP tool 不可以丟例外（丟了 client 會收到 `is_error=True` 的結果，規格要求「操作失敗寫在回傳的 error」，見 <https://py.sdk.modelcontextprotocol.io/v2/servers/handling-errors>）。

把 `showme/app.py` 的 `start_tutorial` 整個換成這一版：

```python
    async def start_tutorial(self, url: str, goal: str) -> dict[str, object]:
        browser = await self._ensure_browser()
        try:
            await browser.open(url)
        except NavigationFailed:
            # A 的設計決定（可改）：開不了頁就不留下 Session，回傳空的 session_id。
            self.store.delete()
            return {
                "session_id": "",
                "goal": goal,
                "page": None,
                "next_action": "",
                "error": "navigation_failed",
            }
        session = self.store.create(goal)
        page = await self._take_snapshot(session)
        return {
            "session_id": session.session_id,
            "goal": session.goal,
            "page": page,
            "next_action": START_NEXT_ACTION,
            "error": "",
        }
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
9 passed in 0.11s
```

注意兩點：

- `except NavigationFailed:` 只接住**這一種**例外。不要寫成 `except Exception:` —— 那會把 `_take_snapshot` 裡真正的程式錯誤（例如打錯字造成的 `AttributeError`）也偽裝成 `navigation_failed`，你會 debug 到天亮。
- 失敗時 `goal` 還是原樣回傳。這樣 agent 才知道是哪一次呼叫失敗。

---

### Step 7：瀏覽器只 launch 一次

在檔案最後加上：

```python
# Rule: 啟動或重用 Chrome 並開啟傳入的 url（feature 只有 #TODO，這裡測不變條件）
async def test_start_twice_reuses_the_same_browser(app, fake_browser):
    launches: list[str] = []
    original_launch = fake_browser.launch

    async def counting_launch() -> None:
        launches.append("launch")
        await original_launch()

    fake_browser.launch = counting_launch

    await app.start_tutorial(DASHBOARD_URL, "create a project")
    await app.start_tutorial(DASHBOARD_URL, "create a project")

    assert launches == ["launch"]
    assert fake_browser.calls.count(("open", DASHBOARD_URL)) == 2
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
10 passed in 0.12s
```

**`fake_browser.launch = counting_launch` 在做什麼？** Python 找方法時先看實體（instance）身上有沒有同名屬性，有就用那個。所以把一個 async 函數指派給 `fake_browser.launch`，之後 `await fake_browser.launch()` 就會跑我們這個會計數的版本，而它裡面再去 `await original_launch()` 呼叫原本的。這叫 monkeypatch，是在**不改 `tests/fakes.py`** 的前提下數次數最省事的方法。

這條測試守住的是設計 §7.1 的「啟動或**重用**」：`_ensure_browser()` 看到瀏覽器還活著就不會再開一個。第二次 start 目前會建立一個新的 Session（因為現在只有新建路徑），A09 會把它改成覆蓋；這條測試看的是瀏覽器，不看 Session，所以 A09 之後仍然會綠。

---

### Step 8：非 localhost 的網址也照開

在檔案最後加上：

```python
# Rule: 開始教學不因 url 不是 localhost 而操作失敗（feature 只有 #TODO，這裡測不變條件）
async def test_start_does_not_check_the_host(app, fake_browser):
    result = await app.start_tutorial("http://example.test/", "create a project")

    assert result["error"] == ""
    assert result["page"]["url"] == "http://example.test/"
    assert result["page"]["title"] == ""
    assert result["page"]["elements"] == []
    assert result["page"]["truncated"] is False
    assert ("open", "http://example.test/") in fake_browser.calls
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
11 passed in 0.12s
```

`http://example.test/` 沒有被 `add_page()` 註冊，所以 `FakeBrowser` 回一頁空的（title `""`、elements `[]`）。重點是 **`error` 是空字串**：程式裡從頭到尾都不該出現 `if "localhost" not in url` 這種檢查（clarify：`開始教學_url不是localhost時是否操作失敗.md`，答案 B）。

---

### Step 9：跑完整套件並 commit

```bash
uv run pytest -m "not browser" -q
```

預期最後一行類似：

```text
84 passed, 18 deselected in 0.58s
```

只把這一篇動到的兩個檔加進 commit：

```bash
git add showme/app.py tests/test_tool_start.py
git commit -m "feat: start_tutorial opens the url and returns the first snapshot"
```

預期輸出類似：

```text
[main 1a2b3c4] feat: start_tutorial opens the url and returns the first snapshot
 2 files changed, 118 insertions(+), 2 deletions(-)
 create mode 100644 tests/test_tool_start.py
```

---

## 8. 驗收清單

- [ ] `uv run pytest tests/test_tool_start.py -q` 全綠，且有 11 條測試。
- [ ] `uv run pytest -m "not browser" -q` 全綠（前面幾篇的測試沒有被弄壞）。
- [ ] `showme/app.py` 的 `start_tutorial` 只有一個 `try/except`，而且 `except` 後面是 `NavigationFailed`，不是 `Exception`。
- [ ] 成功時回傳的五個鍵是 `session_id`、`goal`、`page`、`next_action`、`error`，一個不多一個不少。
- [ ] 失敗時 `session_id == ""`、`page is None`、`next_action == ""`、`error == "navigation_failed"`，而且 `app.store.current() is None`。
- [ ] 程式裡沒有任何 host 檢查、沒有 `goal.strip()`、沒有 `if not goal`。
- [ ] `start_tutorial` 沒有呼叫 `browser.show()`（第一次 start 不畫任何箭頭）。
- [ ] `inspect_page`、`show_step`、`end_tutorial` 三個方法還是原封不動的佔位。
- [ ] commit 只包含 `showme/app.py`、`tests/test_tool_start.py` 與 `tests/test_fakes.py`（刪掉 `start_tutorial` 那一行佔位測試）。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `ModuleNotFoundError: No module named 'fakes'` | 你在 `tests/` 裡放了 `__init__.py`，或不是從 repo 根目錄跑 pytest | 刪掉 `tests/__init__.py`；`cd` 回 repo 根目錄再跑 `uv run pytest` |
| `ModuleNotFoundError: No module named 'showme'` | 沒有 `uv sync`，或 venv 沒被用到 | 在 repo 根目錄跑 `uv sync`，然後所有指令都加 `uv run` 前綴 |
| 測試被跳過，顯示 `skipped: async def function and no async plugin installed` | 檔案最上面漏了 `pytestmark = pytest.mark.anyio`，或 `conftest.py` 少了 `anyio_backend` fixture | 補上那一行；`anyio_backend` 要 `return "asyncio"` |
| `assert page["title"] == "Dashboard"` 失敗，實際是 `""` | 你傳的網址少了結尾斜線（`http://localhost:3000`），FakeBrowser 找不到那一頁 | 測試裡一律用 `DASHBOARD_URL`（結尾有 `/`） |
| uid 是 `s2-1` 而不是 `s1-1` | 同一個測試裡呼叫了兩次會拍快照的方法，或 fixture 用了 `started` 之後又自己 start 一次 | 一個測試只做一件事；要從乾淨狀態開始就用 `app`，要用已開好的場次就用 `started` |
| `NavigationFailed` 直接炸出測試外 | `try/except` 沒有包住 `browser.open(url)`，或 `except` 寫成別的例外類別 | 照 Step 6 的完整方法重貼一次 |
| `test_start_twice_reuses_the_same_browser` 失敗，`launches` 有兩筆 | `_ensure_browser()` 沒有先檢查 `self._browser` 與 `is_alive()` | 回 A07 檢查 `_ensure_browser` 的實作 |
| 回傳裡多了 `session` 或 `state` 之類的鍵 | 自己加料 | 回傳形狀是契約，多的鍵會讓 A14 的 MCP 契約測試變複雜；照 §6.2 的形狀 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/features/開始教學.feature` | Rule：成功開始後回傳的 goal 等於傳入的 goal（Example：開始 create a project） | `test_start_returns_the_same_goal` |
| 同上 | Rule：成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1（Example：Dashboard 的第一份 snapshot） | `test_start_returns_the_first_page`、`test_start_uids_are_the_first_generation` |
| 同上 | Rule：成功開始後 session 狀態為 READY（Example：start_tutorial 之後狀態） | `test_start_leaves_the_session_ready` |
| 同上 | Rule：goal 為空字串時仍成功開始（Example：空目標照常開頁） | `test_start_accepts_an_empty_goal` |
| 同上 | Rule：開始教學不因 url 不是 localhost 而操作失敗（只有 `#TODO`） | `test_start_does_not_check_the_host`（測不變條件：程式裡沒有 host 檢查） |
| 同上 | Rule：目標 url 無法開啟時操作失敗且錯誤為 navigation_failed（Example：打不開的網址） | `test_start_returns_navigation_failed_when_the_url_cannot_open`、`test_start_failure_does_not_take_a_snapshot` |
| 同上 | Rule：page.elements 硬上限 150（Example：不多於 150 個時 truncated 為 false） | `test_start_returns_the_first_page` 的 `truncated is False`；151 個的截斷在 A03（`build_page`）、A06（真 overlay）、A10（`inspect_page`）驗 |
| 同上 | Rule：page.elements 的 testid 鍵永遠存在（Example：Settings 沒有 testid） | `test_start_elements_always_have_a_testid_key` |
| 同上 | Rule：啟動或重用 Chrome 並開啟傳入的 url（只有 `#TODO`） | `test_start_twice_reuses_the_same_browser`（測不變條件：只 launch 一次、open 兩次） |
| 同上 | Rule：注入 overlay.js（只有 `#TODO`） | 不在本篇：注入發生在 `PlaywrightBrowser.launch()`（A05 已測）；`FakeBrowser` 不注入 |
| 同上 | Rule：page.elements 只含互動角色與 heading 與 alert／沒有 a11y name 的元素仍列出（只有 `#TODO`） | 不在本篇：走訪與角色白名單是 overlay（B）的責任（design §10、§15.1） |
| 同上 | Rule：同一時間只允許一個教學場次，再次開始教學時場次識別不變並覆蓋目標與網址 | 不在本篇，A09 負責 |
| `docs/spec/.clarify/resolved/features/開始教學_goal為空字串時是否操作失敗.md` | 答案 B：允許空 goal，不 trim | `test_start_accepts_an_empty_goal`；實作沒有 `strip()` |
| `docs/spec/.clarify/resolved/features/開始教學_url不是localhost時是否操作失敗.md` | 答案 B：不檢查 host | `test_start_does_not_check_the_host` |
| `docs/spec/.clarify/resolved/features/開始教學_目標url無法開啟時是否操作失敗.md` | 答案 A：`navigation_failed` | Step 6 的 `try/except NavigationFailed` |
| `docs/spec/.clarify/resolved/data/PageElement_uid的snapshot編號何時遞增.md` | 答案 A：start 從 1 起算 | `session.snapshot_no == 1`、uid 前綴 `s1-` |
| `docs/spec/.clarify/resolved/data/PageElement_元素沒有data-testid時testid欄位如何表示.md` | 答案 B：鍵永遠在，值為 `""` | `test_start_elements_always_have_a_testid_key` |
| `docs/spec/erm.dbml` | `Session`（session_id/goal/state/steps_shown）、`TutorialStart`（session_id/goal/next_action/error）、`Page`（url/title/truncated） | 回傳形狀與 `SessionStore.create()` 的初值 |
| `docs/design/showme.md` §7.1 | 前置無、成功欄位、失敗 `navigation_failed`、snapshot# 從 1 | 整篇 |
| `docs/design/showme.md` §13 | 錯誤碼只有六個；成功時 `error` 為空字串 | 本篇只用到 `navigation_failed` |
| `docs/design/showme.md` §5 | `next_action` 沿用 draft 舉例字串，不是 `.feature` 驗收字 | 用常數 `START_NEXT_ACTION`，測試比對常數本身而不是硬寫字串 |
| MCP SDK 官方文件 <https://py.sdk.modelcontextprotocol.io/v2/servers/handling-errors> | handler 丟例外 → client 收到 `is_error=True` | 所以 `NavigationFailed` 一定要在 `app.py` 接住，永遠 `return dict` |
