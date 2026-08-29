# A07｜FakeBrowser 與 App 骨架

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：`A06_瀏覽器層_JS呼叫與假overlay.md` ｜ 下一篇：`A08_start_tutorial.md`
> 對應設計：`docs/design/showme.md` §5（相依方向）、§7（tool 契約）、§9（資料模型）、§13（錯誤語意）、§14（測試策略） ｜ 對應切片：S5 的前置
> 預估時間：70 分鐘

---

## 1. 這一篇要做什麼

把「真正的 tool 邏輯」搬出 `server.py`，並且讓它**不用開瀏覽器也能測**。三件事：

1. `tests/fakes.py` 的 `FakeBrowser`：一個實作 `BrowserLike`、但完全不開瀏覽器的假貨。之後 A08–A13 的所有 tool 測試都靠它，跑起來只要幾毫秒。
2. `showme/app.py` 的 `ShowMeApp` 骨架：把 Session、瀏覽器、snapshot 計數、emit 收件都放在這裡。本篇把三個內部方法（`_ensure_browser`、`_on_emit`、`_take_snapshot`）與 `shutdown` **完整寫好**；四個 tool 方法先回一個佔位值，A08–A13 一篇換掉一個。
3. `showme/server.py` 改成薄殼：只留 `MCPServer`、`INSTRUCTIONS`、四個 `@mcp.tool()`，每個 tool 一行轉呼叫 `app`。

做完之後，「MCP 這一層」與「教學邏輯這一層」就分開了：想測邏輯不必啟動 MCP，想測 MCP 契約（A14）也不必開瀏覽器。

---

## 2. 做完會看到什麼

### 2.1 分層與相依方向

```text
   Qoder / MCP Client
        │  stdio
        ▼
   showme/server.py           ← 薄殼：MCPServer + 四個 @mcp.tool()
        │                        每個 tool 只有一行：return await get_app().<同名方法>(...)
        ▼
   showme/app.py  ShowMeApp   ← 全部邏輯：Session、snapshot#、等待、錯誤欄
        │  只認得 BrowserLike 這個介面
        ▼
   ┌──────────────────────┬──────────────────────────┐
   │ showme/browser.py    │ tests/fakes.py           │
   │ PlaywrightBrowser    │ FakeBrowser              │
   │ 真的開 Chrome        │ 只有一個 dict，不開瀏覽器 │
   └──────────────────────┴──────────────────────────┘
        正式跑用左邊              A08–A13 測試用右邊

   ※ 換哪一個由 ShowMeApp(browser_factory=...) 決定。
     server.py 不傳 → 預設 PlaywrightBrowser。
     測試傳 lambda: fake_browser → 拿到假的。
```

### 2.2 兩個實作，同一個介面

```text
                 BrowserLike（showme/browser.py 的 Protocol）
                 launch · is_alive · open · current_url · title
                 snapshot · show · clear · done · set_emit_handler · close
                        ▲                              ▲
        「結構相符就算數，不用繼承」                     │
                        │                              │
   ┌────────────────────┴───────┐      ┌───────────────┴──────────────────┐
   │ PlaywrightBrowser          │      │ FakeBrowser                      │
   │  open()  → page.goto       │      │  open()  → 檢查 fail_urls，       │
   │  snapshot(n) → evaluate    │      │            記一筆 ("open", url)   │
   │  show()  → evaluate        │      │  snapshot(n) → 從 self.pages 拿， │
   │  ...                       │      │            把 uid 重編成 s{n}-{i} │
   │                            │      │  show()  → 記一筆 ("show", opts)  │
   │  頁面呼叫 __showme_emit    │      │  emit()  → 測試自己手動叫，       │
   │  → _on_emit → handler      │      │            直接呼叫 handler       │
   └────────────────────────────┘      └──────────────────────────────────┘
```

### 2.3 `_take_snapshot` 的資料流

```text
   session.snapshot_no  0 ──────┐
                                ▼  +1
                          snapshot_no = 1
                                │
       browser.snapshot(1) ─────┤────▶ {"elements": [{uid:"s1-1", role, name, testid}, ...],
                                │       "truncated": false}          ← raw，沒有 url/title
       browser.current_url() ───┤────▶ "http://localhost:3000/"
       browser.title() ─────────┤────▶ "Dashboard"
                                ▼
       build_page(raw, url, title)   ← A03 的純函數：補鍵、砍到 150、算 truncated
                                │
                                ▼
       {"url": ..., "title": ..., "elements": [...], "truncated": false}
                                │
                                ├──▶ session.latest_page = page   （之後 uid 驗證要用）
                                └──▶ return page
```

### 2.4 `_on_emit` 的三道門（每步只取第一筆）

```text
   頁面 emit（或 FakeBrowser.emit）
            │
            ▼
   ┌────────────────────────────────┐
   │ 有 current session 嗎？         │── 沒有 ──▶ 忽略（回 None）
   └───────────┬────────────────────┘
               │ 有
               ▼
   ┌────────────────────────────────┐
   │ state 是 SHOWING 嗎？           │── 不是 ──▶ 忽略（READY 時的雜訊）
   └───────────┬────────────────────┘
               │ 是
               ▼
   ┌────────────────────────────────┐
   │ pending 存在且還沒 done()？     │── 否 ────▶ 忽略（第二筆事件丟棄）
   └───────────┬────────────────────┘
               │ 是
               ▼
        pending.set_result(event)   ← 卡在 show_step 的 await 醒來（A12）
```

### 2.5 這一篇做完的檔案樹（★ = 本篇新增／修改）

```text
hackathonQoder/
├── showme/
│   ├── server.py             ★ 改成薄殼
│   ├── app.py                ★ 新增（骨架）
│   ├── session.py            A02
│   ├── rules.py              A03
│   └── browser.py            A04–A06，已完成
└── tests/
    ├── conftest.py           ★ 修改（加 fake_browser / app / started）
    ├── fakes.py              ★ 新增
    ├── test_fakes.py         ★ 新增（FakeBrowser + App 骨架）
    └── ...（A02–A06 的測試不動）
```

---

## 3. 開始前先確認

- [ ] **A06 的驗收都打勾**：
  ```bash
  cd /Users/linjunting/hackathonQoder
  uv run pytest -m browser -q
  ```
  預期最後一行：`18 passed in 1x.xxs`

- [ ] **`showme/browser.py` 已經完成**（13 個成員）：
  ```bash
  grep -c "    async def \|    def " showme/browser.py
  ```
  預期輸出：`24`（`BrowserLike` 的 11 行宣告 + `PlaywrightBrowser` 的 13 個成員）

- [ ] **A02 的 `session.py` 有這些名字**：
  ```bash
  grep -n "^MAX_STEPS\|^DEFAULT_TIMEOUT_S\|^DONE_BANNER_TEXT\|^START_NEXT_ACTION\|^STEP_NEXT_ACTION\|^class State\|^class Session\|^class SessionStore\|^def new_session_id" showme/session.py
  ```
  預期看到九行，缺任何一個就回頭補 A02。

- [ ] **A03 的 `rules.py` 有這些名字**：
  ```bash
  grep -n "^def " showme/rules.py
  ```
  預期看到 `normalize_timeout_s`、`normalize_kind`、`expect_text_missing`、`build_page`、`uid_in_page`、`empty_page` 六個。

- [ ] **A01 的 smoke test 現在是綠的**（本篇改 `server.py`，改完要再確認它還綠）：
  ```bash
  uv run pytest -m "not browser" -q
  ```
  預期：全綠。先把「目前有幾個 passed」記下來，等一下要比對。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| 假貨 / fake | 一種測試替身：有真的（但很簡化的）實作。`FakeBrowser` 真的會記住現在在哪一頁、真的會回元素清單，只是資料放在 dict 裡而不是瀏覽器裡。 |
| factory（工廠） | 「一個會生出物件的函式」。`ShowMeApp(browser_factory=lambda: fake_browser)` 就是告訴 App：需要瀏覽器時，叫這個函式要。 |
| 依賴注入 | 把「要用哪個實作」從外面傳進來，而不是在裡面寫死。這樣測試才換得掉。 |
| Future | 「一個之後才會有答案的信箱」。`asyncio.Future` 建立時是空的；有人 `set_result(x)` 之後，`await` 它的人就會醒來拿到 `x`。 |
| `future.done()` | 問信箱「有答案了嗎？」。已經 `set_result` 過就是 `True`。對同一個 Future `set_result` 兩次會丟 `InvalidStateError`，所以放之前一定要先問。 |
| 薄殼 / thin shell | 一層幾乎沒有邏輯的轉接層。`server.py` 只負責「把 MCP 的呼叫轉給 app」，這樣邏輯測試不用啟動 MCP。 |
| 模組層級的單例 | `server.py` 用一個模組變數 `_app` 存唯一那個 `ShowMeApp`。`get_app()` 第一次被叫時才建立（lazy），`set_app()` 讓測試換掉它。 |
| `not_implemented` | **本篇的臨時佔位字串，不是規格的錯誤碼。** 規格只承認六個錯誤碼（見 §10）。A08–A13 會把四個方法逐一換掉，A13 之後 `showme/` 底下不該再有這個字串。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 新增 | `tests/fakes.py` | `FakeBrowser`：不開瀏覽器的 `BrowserLike` 實作，另有 `emit()`／`navigate()`／`add_page()` 三個測試專用的操控方法 |
| 新增 | `showme/app.py` | `ShowMeApp`：`__init__`／`_ensure_browser`／`_on_emit`／`_take_snapshot`／`shutdown` 完整實作；四個 tool 方法先回佔位值 |
| 修改 | `showme/server.py` | 改成薄殼：`INSTRUCTIONS`、`mcp`、`get_app`／`set_app`、四個 `@mcp.tool()` |
| 修改 | `tests/conftest.py` | 加 `fake_browser`／`app`／`started` 三個 fixture |
| 新增（測試） | `tests/test_fakes.py` | 上半：`FakeBrowser` 的行為；下半：`ShowMeApp` 骨架（`_take_snapshot`、`_on_emit`、`shutdown`） |

**不要動**：`showme/browser.py`（A06 已完成）、`showme/session.py`、`showme/rules.py`、`showme/__main__.py`、`overlay/**`。

---

## 6. 介面約定

### 用到（來自 A02／A03／A04–A06）

```python
# showme/session.py（A02）
MAX_STEPS = 12
DEFAULT_TIMEOUT_S = 120.0
DONE_BANNER_TEXT = "✅ Done — you created a project"
START_NEXT_ACTION = "Plan 3–8 steps in your head, then call show_step for the FIRST step using a uid from page.elements."
STEP_NEXT_ACTION = "If the goal is not yet achieved, call show_step for the next step using a uid from page.elements. If the page shows the goal is achieved, call end_tutorial."

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
    def create(self, goal: str) -> Session: ...
    def delete(self) -> None: ...

# showme/rules.py（A03）
def build_page(raw: dict, url: str, title: str) -> dict: ...
def uid_in_page(uid: str, page: dict | None) -> bool: ...
def normalize_kind(kind: str | None) -> str: ...
def normalize_timeout_s(value: float | int | None) -> float: ...
def expect_text_missing(kind: str, expect_text: str | None) -> bool: ...

# showme/browser.py（A04–A06）
class BrowserLike(Protocol): ...      # 11 個方法
class NavigationFailed(Exception): ...
class PlaywrightBrowser: ...
EmitHandler = Callable[[dict], None]
```

### 提供（給後面幾篇）

```python
# showme/app.py
BrowserFactory = Callable[[], BrowserLike]

class ShowMeApp:
    def __init__(self, browser_factory: BrowserFactory = PlaywrightBrowser) -> None: ...
    async def _ensure_browser(self) -> BrowserLike: ...
    def _on_emit(self, event: dict) -> None: ...
    async def _take_snapshot(self, session: Session) -> dict: ...
    async def start_tutorial(self, url: str, goal: str) -> dict[str, object]: ...              # A08、A09
    async def inspect_page(self, session_id: str) -> dict[str, object]: ...                    # A10
    async def show_step(self, session_id: str, uid: str, instruction: str, kind: str,
                        step_index: int, step_total: int, expect_text: str = "",
                        timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, object]: ...        # A11、A12
    async def end_tutorial(self, session_id: str, summary: str) -> dict[str, object]: ...      # A13
    async def shutdown(self) -> None: ...

# showme/server.py
mcp: MCPServer
def get_app() -> ShowMeApp: ...
def set_app(app: ShowMeApp | None) -> None: ...     # A14 的 mcp_client fixture 會用

# tests/fakes.py
class FakeBrowser:
    def __init__(self, *, fail_urls: set[str] | None = None) -> None: ...
    def emit(self, kind: str, url: str | None = None, ts: int = 0) -> None: ...
    def navigate(self, url: str) -> None: ...
    def add_page(self, url: str, title: str, elements: list[dict], truncated: bool = False) -> None: ...
    self.calls: list[tuple]     # ("open", url) / ("snapshot", n) / ("show", opts) / ("clear",) / ("done", text) / ("close",)
```

---

## 7. 步驟

### Step 1：寫 `tests/fakes.py`（12 分鐘）

新增 `tests/fakes.py`：

```python
"""測試替身：不開瀏覽器的 BrowserLike 實作。

A08–A13 的所有 tool 測試都用它，所以那些測試不需要 browser marker，
跑一輪只要幾毫秒。真的瀏覽器測試在 tests/test_browser_*.py 與
tests/test_e2e_fake_overlay.py。
"""

from __future__ import annotations

from showme.browser import EmitHandler, NavigationFailed


class FakeBrowser:
    def __init__(self, *, fail_urls: set[str] | None = None) -> None:
        self.launched = False
        self.alive = True
        self.url = "about:blank"
        self.page_title = ""
        self.fail_urls = fail_urls or set()   # open() 遇到這些 url 就 raise NavigationFailed
        self.pages: dict[str, dict] = {}      # url → {"title": str, "raw": {"elements": [...], "truncated": bool}}
        self.calls: list[tuple] = []          # ("open", url) / ("snapshot", n) / ("show", opts) / ("clear",) / ("done", text) / ("close",)
        self._handler: EmitHandler | None = None

    # ---- BrowserLike ----

    async def launch(self) -> None:
        self.launched = True

    async def is_alive(self) -> bool:
        return self.alive

    async def open(self, url: str) -> None:
        if url in self.fail_urls:
            raise NavigationFailed(f"cannot open {url}")
        self.calls.append(("open", url))
        self.url = url

    async def current_url(self) -> str:
        return self.url

    async def title(self) -> str:
        return self.pages.get(self.url, {}).get("title", "")

    async def snapshot(self, n: int) -> dict:
        self.calls.append(("snapshot", n))
        raw = self.pages.get(self.url, {}).get("raw", {"elements": [], "truncated": False})
        elements = [dict(element, uid=f"s{n}-{i + 1}") for i, element in enumerate(raw["elements"])]
        return {"elements": elements, "truncated": raw.get("truncated", False)}

    async def show(self, opts: dict) -> None:
        self.calls.append(("show", opts))

    async def clear(self) -> None:
        self.calls.append(("clear",))

    async def done(self, text: str) -> None:
        self.calls.append(("done", text))

    def set_emit_handler(self, handler: EmitHandler | None) -> None:
        self._handler = handler

    async def close(self) -> None:
        self.calls.append(("close",))
        self.alive = False

    # ---- 測試專用的操控方法（BrowserLike 沒有這些，正式程式碼不會呼叫）----

    def emit(self, kind: str, url: str | None = None, ts: int = 0) -> None:
        """模擬頁面呼叫 window.__showme_emit({...})。"""
        if self._handler:
            self._handler({"kind": kind, "url": url or self.url, "ts": ts})

    def navigate(self, url: str) -> None:
        """模擬使用者自己點了什麼、頁面換了。不記進 calls（不是 ShowMe 做的）。"""
        self.url = url

    def add_page(self, url: str, title: str, elements: list[dict], truncated: bool = False) -> None:
        """登記一個假頁面。elements 只要 role/name/testid，uid 由 snapshot(n) 依 n 重編。"""
        self.pages[url] = {"title": title, "raw": {"elements": elements, "truncated": truncated}}
```

幾個設計要點：

- **`snapshot(n)` 會依 `n` 重編 uid**：`dict(element, uid=f"s{n}-{i+1}")`。`dict(x, key=v)` 是「複製 x 再覆蓋一個鍵」，所以不會改到 `self.pages` 裡原本那份。這讓 `add_page` 傳進來的資料只要寫 `role`／`name`／`testid`，世代交給呼叫端決定 —— 跟真 overlay 的分工一模一樣（`docs/handoff.md`：A 給 `n`，B 組字串）。
- **`calls` 記的是「ShowMe 對瀏覽器做了什麼」**：測試靠它斷言「有沒有呼叫 `show`」「`clear` 有沒有在 `done` 之前」。`navigate()` 刻意不記，因為那是模擬使用者的動作，不是 ShowMe 做的。
- **`open` 失敗時不記 `calls`**：`raise` 在 `append` 之前。這樣 A08 的 `navigation_failed` 測試可以順便斷言「沒有留下 open 記錄」。
- **`emit()` 是同步的**：跟 `PlaywrightBrowser._on_emit` 一樣同步呼叫 handler。A12 的測試會在 `asyncio.create_task(app.show_step(...))` 之後呼叫 `fake.emit("step_done")`，直接把卡住的 Future 解掉。
- **`close()` 之後 `alive` 變 `False`**：A09 要測「瀏覽器死掉就重新 launch」，測試可以直接寫 `fake.alive = False`。

### Step 2：conftest 加三個 fixture（8 分鐘）

把 `tests/conftest.py` 換成下面這份完整內容（前面 `anyio_backend` 與 `static_server` 是 A01／A04 就有的，保留）：

```python
"""所有測試共用的 fixture。"""

from __future__ import annotations

import http.server
import threading
from functools import partial
from pathlib import Path

import pytest

from fakes import FakeBrowser
from showme.app import ShowMeApp

PAGES_DIR = Path(__file__).parent / "fixtures" / "pages"

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"


@pytest.fixture
def anyio_backend() -> str:
    """anyio 的 pytest plugin 要靠這個 fixture 決定用哪個 async 後端。"""
    return "asyncio"


@pytest.fixture(scope="session")
def static_server():
    """在 127.0.0.1 的隨機 port 上，用一條背景執行緒送出 tests/fixtures/pages/ 底下的檔案。"""
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(PAGES_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def fake_browser() -> FakeBrowser:
    """預先放好兩個假頁面：Dashboard 與 New Project。

    元素只寫 role / name / testid；uid 由 FakeBrowser.snapshot(n) 依 n 重編。
    """
    browser = FakeBrowser()
    browser.add_page(
        DASHBOARD_URL,
        "Dashboard",
        [
            {"role": "button", "name": "New Project", "testid": "new-project"},
            {"role": "link", "name": "Settings", "testid": ""},
        ],
    )
    browser.add_page(
        NEW_PROJECT_URL,
        "New Project",
        [
            {"role": "heading", "name": "New Project", "testid": ""},
            {"role": "textbox", "name": "Project name", "testid": "project-name"},
            {"role": "button", "name": "Create", "testid": "create"},
        ],
    )
    return browser


@pytest.fixture
def app(fake_browser: FakeBrowser) -> ShowMeApp:
    """一個用 FakeBrowser 的 ShowMeApp。factory 每次都回同一顆假瀏覽器，

    所以測試可以直接對 fake_browser 下指令（emit / navigate），
    也可以讀它的 calls。
    """
    return ShowMeApp(browser_factory=lambda: fake_browser)


@pytest.fixture
async def started(app: ShowMeApp, fake_browser: FakeBrowser):
    """已經 start_tutorial 過的 (app, fake_browser, result)。

    注意：A07 的 start_tutorial 還是佔位版本（回 {"error": "not_implemented"}），
    所以這個 fixture 要到 A08 之後才真的有用。先建好，A08 起就直接拿來用。
    """
    result = await app.start_tutorial(DASHBOARD_URL, "create a project")
    return app, fake_browser, result
```

**`from fakes import FakeBrowser` 為什麼不是 `from tests.fakes import ...`？**

`tests/` 底下沒有 `__init__.py`，所以它不是一個 Python 套件。pytest 用預設的 `prepend` import mode 收集測試時，會把 `tests/` 這個資料夾本身加進 `sys.path`，於是 `fakes` 就是一個可以直接 import 的頂層模組。`conftest.py` 也住在 `tests/`，所以同樣寫得出來。

（若看到 `ModuleNotFoundError: No module named 'fakes'`，先確認你在 repo 根目錄執行 `uv run pytest`，而且**沒有**幫 `tests/` 加 `__init__.py`。）

`DASHBOARD_URL` 用 `http://localhost:3000/`（**結尾有斜線**），跟 `開始教學.feature` 的 `page.url` Example 一致。`FakeBrowser` 是用字串當 key 查頁面的，少一個斜線就查不到 —— 之後寫測試時要用這個常數，不要手打。

### Step 3：先寫測試，看它紅（12 分鐘）

新增 `tests/test_fakes.py`：

```python
"""A07：FakeBrowser 的行為，以及 ShowMeApp 骨架的三個內部方法。

這些測試不開瀏覽器，所以沒有 browser marker：
    uv run pytest tests/test_fakes.py -q
"""

from __future__ import annotations

import asyncio

import pytest

from fakes import FakeBrowser
from showme.browser import BrowserLike, NavigationFailed
from showme.session import State

pytestmark = pytest.mark.anyio

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"

# BrowserLike 要求的方法（showme/browser.py 的 Protocol），照抄一份在這裡當檢查表。
BROWSER_LIKE_METHODS = (
    "launch",
    "is_alive",
    "open",
    "current_url",
    "title",
    "snapshot",
    "show",
    "clear",
    "done",
    "set_emit_handler",
    "close",
)


# ---------------------------------------------------------------- FakeBrowser


def test_fake_browser_has_every_browser_like_method():
    browser: BrowserLike = FakeBrowser()   # 型別註記：讓型別檢查器也幫忙盯

    missing = [name for name in BROWSER_LIKE_METHODS if not callable(getattr(browser, name, None))]

    assert missing == []


async def test_open_records_the_call_and_updates_url(fake_browser):
    await fake_browser.open(DASHBOARD_URL)

    assert fake_browser.calls == [("open", DASHBOARD_URL)]
    assert await fake_browser.current_url() == DASHBOARD_URL
    assert await fake_browser.title() == "Dashboard"


async def test_open_raises_navigation_failed_for_fail_urls():
    browser = FakeBrowser(fail_urls={"http://localhost:1"})

    with pytest.raises(NavigationFailed):
        await browser.open("http://localhost:1")

    assert browser.calls == []
    assert await browser.current_url() == "about:blank"


async def test_snapshot_numbers_uids_by_n(fake_browser):
    await fake_browser.open(DASHBOARD_URL)

    first = await fake_browser.snapshot(1)
    second = await fake_browser.snapshot(2)

    assert [element["uid"] for element in first["elements"]] == ["s1-1", "s1-2"]
    assert [element["uid"] for element in second["elements"]] == ["s2-1", "s2-2"]
    assert first["elements"][0] == {
        "uid": "s1-1",
        "role": "button",
        "name": "New Project",
        "testid": "new-project",
    }
    assert first["truncated"] is False
    assert fake_browser.calls == [("open", DASHBOARD_URL), ("snapshot", 1), ("snapshot", 2)]


async def test_snapshot_on_unknown_url_returns_empty(fake_browser):
    result = await fake_browser.snapshot(1)   # 還停在 about:blank

    assert result == {"elements": [], "truncated": False}


async def test_navigate_switches_the_page_without_recording_a_call(fake_browser):
    await fake_browser.open(DASHBOARD_URL)
    fake_browser.navigate(NEW_PROJECT_URL)

    result = await fake_browser.snapshot(2)

    assert await fake_browser.title() == "New Project"
    assert [element["name"] for element in result["elements"]] == [
        "New Project",
        "Project name",
        "Create",
    ]
    assert ("open", NEW_PROJECT_URL) not in fake_browser.calls


def test_emit_forwards_to_the_handler(fake_browser):
    received: list[dict] = []
    fake_browser.set_emit_handler(received.append)

    fake_browser.emit("step_done", ts=1756400000)

    assert received == [{"kind": "step_done", "url": "about:blank", "ts": 1756400000}]


def test_emit_without_handler_does_nothing(fake_browser):
    fake_browser.emit("stuck")   # 不該丟例外


async def test_close_records_the_call_and_marks_it_dead(fake_browser):
    await fake_browser.close()

    assert fake_browser.calls == [("close",)]
    assert await fake_browser.is_alive() is False


# ------------------------------------------------------- ShowMeApp 骨架


async def test_ensure_browser_launches_once_and_registers_the_handler(app, fake_browser):
    first = await app._ensure_browser()
    second = await app._ensure_browser()

    assert first is fake_browser
    assert second is fake_browser
    assert fake_browser.launched is True
    assert fake_browser._handler == app._on_emit


async def test_take_snapshot_bumps_snapshot_no_and_stores_latest_page(app, fake_browser):
    session = app.store.create("create a project")
    fake_browser.navigate(DASHBOARD_URL)

    page = await app._take_snapshot(session)

    assert session.snapshot_no == 1
    assert page["url"] == DASHBOARD_URL
    assert page["title"] == "Dashboard"
    assert page["truncated"] is False
    assert [element["uid"] for element in page["elements"]] == ["s1-1", "s1-2"]
    assert session.latest_page == page


async def test_take_snapshot_twice_goes_from_s1_to_s2(app, fake_browser):
    session = app.store.create("create a project")
    fake_browser.navigate(DASHBOARD_URL)

    await app._take_snapshot(session)
    fake_browser.navigate(NEW_PROJECT_URL)
    page = await app._take_snapshot(session)

    assert session.snapshot_no == 2
    assert page["title"] == "New Project"
    assert [element["uid"] for element in page["elements"]] == ["s2-1", "s2-2", "s2-3"]
    assert session.latest_page == page


async def test_on_emit_sets_the_result_only_while_showing(app):
    session = app.store.create("create a project")
    session.pending = asyncio.get_running_loop().create_future()

    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})
    assert session.pending.done() is False       # state 還是 READY → 忽略

    session.state = State.SHOWING
    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})

    assert session.pending.done() is True
    assert session.pending.result() == {"kind": "step_done", "url": DASHBOARD_URL, "ts": 1}


async def test_on_emit_ignores_the_second_event(app):
    session = app.store.create("create a project")
    session.state = State.SHOWING
    session.pending = asyncio.get_running_loop().create_future()

    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})
    app._on_emit({"kind": "stuck", "url": DASHBOARD_URL, "ts": 1})

    assert session.pending.result()["kind"] == "step_done"


async def test_on_emit_without_session_or_pending_does_nothing(app):
    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})   # 沒有 session

    session = app.store.create("create a project")
    session.state = State.SHOWING
    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 2})   # 有 session、沒有 pending

    assert session.pending is None


async def test_shutdown_closes_the_browser(app, fake_browser):
    await app._ensure_browser()

    await app.shutdown()

    assert ("close",) in fake_browser.calls
    assert await fake_browser.is_alive() is False
    assert app._browser is None


async def test_shutdown_without_browser_does_nothing(app):
    await app.shutdown()   # 不該丟例外


@pytest.mark.parametrize(
    "call",
    [
        lambda app: app.start_tutorial("http://localhost:3000/", "create a project"),
        lambda app: app.inspect_page("s_8f2a"),
        lambda app: app.show_step("s_8f2a", "s1-1", "Click New Project", "click", 1, 4),
        lambda app: app.end_tutorial("s_8f2a", "done"),
    ],
)
async def test_tool_methods_are_placeholders_for_now(app, call):
    """A08–A13 會一個一個換掉；換掉之後這個測試會被那一篇刪掉對應的那一行。"""
    assert await call(app) == {"error": "not_implemented"}
```

兩個小地方值得說明：

- `test_on_emit_sets_the_result_only_while_showing` 用 `asyncio.get_running_loop().create_future()` 自己造一個 Future。這只是為了單獨測 `_on_emit` 的三道門；真正建立 Future 的地方在 A12 的 `show_step`。
- 最後那個 `parametrize` 測試把「四個 tool 現在都是佔位」寫成一條。A08 換掉 `start_tutorial` 時，會從清單裡刪掉第一行；A13 之後整個測試都會被刪掉。**這是刻意的暫時性測試**，用來保證「骨架真的接起來了、呼叫得動」。

跑一次看紅：

```bash
uv run pytest tests/test_fakes.py -q
```

預期輸出：

```text
ERROR tests/test_fakes.py
E   ModuleNotFoundError: No module named 'showme.app'
...
1 error in 0.3s
```

（`conftest.py` 最上面 `from showme.app import ShowMeApp` 就先炸了，所以是 collection error 而不是一堆 F。這也代表整個 `tests/` 目前都收集不了 —— 等 Step 4 建好 `app.py` 就恢復。）

### Step 4：寫 `showme/app.py` 骨架（12 分鐘）

新增 `showme/app.py`，完整內容：

```python
"""ShowMe 的教學邏輯：Session、瀏覽器生命週期、snapshot 世代、等待完成訊號。

showme/server.py 只是把 MCP 的四個 tool 轉呼叫到這裡。
本檔在 A07 建立骨架（內部方法完整、四個 tool 方法先佔位），
A08–A13 一篇換掉一個 tool 方法。
"""

from __future__ import annotations

import asyncio
from typing import Callable

from showme.browser import BrowserLike, NavigationFailed, PlaywrightBrowser
from showme.rules import (
    build_page,
    expect_text_missing,
    normalize_kind,
    normalize_timeout_s,
    uid_in_page,
)
from showme.session import (
    DEFAULT_TIMEOUT_S,
    DONE_BANNER_TEXT,
    MAX_STEPS,
    START_NEXT_ACTION,
    STEP_NEXT_ACTION,
    Session,
    SessionStore,
    State,
)

BrowserFactory = Callable[[], BrowserLike]


class ShowMeApp:
    def __init__(self, browser_factory: BrowserFactory = PlaywrightBrowser) -> None:
        self.store = SessionStore()
        self._browser_factory = browser_factory
        self._browser: BrowserLike | None = None

    # ---- 內部：瀏覽器、事件、snapshot ----

    async def _ensure_browser(self) -> BrowserLike:
        """沒有瀏覽器或已死 → 用 factory 建一個、launch()、登記 emit handler。"""
        if self._browser is not None and await self._browser.is_alive():
            return self._browser
        browser = self._browser_factory()
        await browser.launch()
        browser.set_emit_handler(self._on_emit)
        self._browser = browser
        return browser

    def _on_emit(self, event: dict) -> None:
        """只有 current session 在 SHOWING 且 pending 未 done 時才 set_result；

        其他一律忽略（= 每步只取第一筆事件）。
        """
        session = self.store.current()
        if session is None or session.state != State.SHOWING:
            return
        pending = session.pending
        if pending is None or pending.done():
            return
        pending.set_result(event)

    async def _take_snapshot(self, session: Session) -> dict:
        """世代 +1 → 請瀏覽器掃一次 → 組成 Page → 存進 session.latest_page。"""
        browser = await self._ensure_browser()
        session.snapshot_no += 1
        raw = await browser.snapshot(session.snapshot_no)
        page = build_page(raw, await browser.current_url(), await browser.title())
        session.latest_page = page
        return page

    # ---- 四個 MCP tool（A08–A13 逐一實作）----

    async def start_tutorial(self, url: str, goal: str) -> dict[str, object]:
        return {"error": "not_implemented"}

    async def inspect_page(self, session_id: str) -> dict[str, object]:
        return {"error": "not_implemented"}

    async def show_step(
        self,
        session_id: str,
        uid: str,
        instruction: str,
        kind: str,
        step_index: int,
        step_total: int,
        expect_text: str = "",
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> dict[str, object]:
        return {"error": "not_implemented"}

    async def end_tutorial(self, session_id: str, summary: str) -> dict[str, object]:
        return {"error": "not_implemented"}

    # ---- 收尾 ----

    async def shutdown(self) -> None:
        """關瀏覽器（process 結束時用）。"""
        if self._browser is None:
            return
        await self._browser.close()
        self._browser = None
```

**幾件要說清楚的事：**

1. **`{"error": "not_implemented"}` 是暫時的鷹架，不是規格。**
   規格只承認六個錯誤碼：`navigation_failed`、`session_not_found`、`max_steps_exceeded`、`uid_not_in_snapshot`、`expect_text_required`、`show_step_in_progress`（`docs/design/showme.md` §13）。這裡的 `not_implemented` 只是讓四個方法「呼叫得動、形狀是 dict」的佔位。
   換掉的順序：A08／A09 換 `start_tutorial`、A10 換 `inspect_page`、A11／A12 換 `show_step`、A13 換 `end_tutorial`。**A13 做完後**，用 `grep -rn "not_implemented" showme/` 應該找不到任何一行。

2. **本篇有幾個 import 目前還沒用到**（`NavigationFailed`、`expect_text_missing`、`normalize_kind`、`normalize_timeout_s`、`uid_in_page`、`MAX_STEPS`、`START_NEXT_ACTION`、`STEP_NEXT_ACTION`、`DONE_BANNER_TEXT`、`asyncio`）。這是刻意的：import 區塊一次寫好，A08–A13 就只要動函式本體，不必每篇都回頭改最上面。若你的編輯器對「未使用的 import」畫黃線，忽略即可（我們沒有把 lint 設成 CI 檻）。

3. **`_ensure_browser` 為什麼要 `await self._browser.is_alive()`？**
   A 的設計決定 A-2（可改）：`end_tutorial` 之後**不關**瀏覽器（人要看到完成 banner），下次 `start_tutorial` 重用同一個。但人可能自己把視窗按叉叉關掉，這時 `is_alive()` 會是 `False`，就重開一個。這裡沒有先把舊的關掉才換新的 —— 舊的既然已經死了，關它沒有意義，而且 `close()` 失敗會讓 `start_tutorial` 平白多一條錯誤路徑。

4. **`_take_snapshot` 為什麼自己叫 `_ensure_browser`？**
   因為 `inspect_page`（A10）與 `show_step`（A12）都會用它，這樣它們不必各自把 browser 傳進來。呼叫成本是一次 `is_alive()`，很便宜。

5. **`_on_emit` 為什麼是同步？**
   因為 `PlaywrightBrowser._on_emit` 是同步呼叫它的（A05）。同步保證了「檢查 `pending.done()` 到 `set_result()` 之間不會被別的 task 插隊」，也就是規格說的「同一 session 同一 ts 後至的事件丟棄」。
   注意判斷順序：先 `session is None`、再 `state != SHOWING`、再 `pending is None or pending.done()`。三道門任何一道沒過就 `return`，**不丟例外** —— 因為這個函式是被瀏覽器叫的，丟例外只會讓頁面上的 Promise reject，Python 這邊什麼也看不到。

6. **`shutdown` 誰來叫？**
   目前只有測試會叫。`showme/__main__.py` 依照模組地圖**不動**（`mcp.run(transport="stdio")` 結束時，Playwright 起的子行程會跟著 process 一起收掉）。留這個方法是為了讓測試能明確關掉假瀏覽器，也讓之後真的需要優雅關閉時有現成的入口。

### Step 5：`server.py` 改成薄殼（8 分鐘）

把 `showme/server.py` 整個換成：

```python
"""MCP stdio 進入點：只做轉接，邏輯全在 showme/app.py。"""

from mcp.server import MCPServer

from showme.app import ShowMeApp

INSTRUCTIONS = """You are TEACHING the user how to use the app; you never act for them.
- You have no click/type/navigate tools. You only look (start_tutorial / inspect_page) and point (show_step).
- Plan 3-8 steps in your head, but pick each step's uid from the LATEST page.elements only. Never reuse a uid from an older snapshot.
- One show_step at a time; wait for it to return before deciding the next step.
- instruction: second person, one sentence, use the words visible on screen (e.g. "Click New Project").
- If event is "stuck": call show_step again with the SAME uid and a plainer instruction.
- If error is "uid_not_in_snapshot": re-pick a uid from the returned page.
- Call end_tutorial only when the page shows the goal is achieved.
"""

mcp = MCPServer("showme", instructions=INSTRUCTIONS)

_app: ShowMeApp | None = None


def get_app() -> ShowMeApp:
    global _app
    if _app is None:
        _app = ShowMeApp()
    return _app


def set_app(app: ShowMeApp | None) -> None:   # 測試用：換成用 FakeBrowser 的 app
    global _app
    _app = app


@mcp.tool()
async def start_tutorial(url: str, goal: str) -> dict[str, object]:
    """Open the app in a headed browser, inject the overlay, start (or restart) the single tutorial session, and return the first condensed page snapshot (uids s1-*)."""
    return await get_app().start_tutorial(url, goal)


@mcp.tool()
async def inspect_page(session_id: str) -> dict[str, object]:
    """Re-snapshot the current page (snapshot# +1) without drawing anything. Use it when a uid was rejected or the page changed."""
    return await get_app().inspect_page(session_id)


@mcp.tool()
async def show_step(session_id: str, uid: str, instruction: str, kind: str, step_index: int, step_total: int,
                    expect_text: str = "", timeout_s: float = 120) -> dict[str, object]:
    """Highlight one uid from the latest page and BLOCK until the user finishes the step (event=step_done), presses I'm stuck (stuck), or timeout_s elapses (timeout). Returns a fresh page. kind: click|input|select|observe (observe needs expect_text)."""
    return await get_app().show_step(session_id, uid, instruction, kind, step_index, step_total, expect_text, timeout_s)


@mcp.tool()
async def end_tutorial(session_id: str, summary: str) -> dict[str, object]:
    """Clear the overlay, show the fixed done banner, and delete the session."""
    return await get_app().end_tutorial(session_id, summary)
```

**要注意的地方：**

- `MCPServer("showme", instructions=INSTRUCTIONS)`：第一個位置參數是 `name`，其餘**一律用關鍵字**。MCP Python SDK v2 在位置參數裡插了 `title`／`description`／`version`，不用關鍵字會把 `instructions` 塞進錯的欄位。來源：https://py.sdk.modelcontextprotocol.io/v2/migration
- `@mcp.tool()` 裝飾 async 函式即註冊：**函式名 = tool 名，docstring = 描述，type hints = 參數 schema**。所以 docstring 要寫給模型看（它會出現在 Qoder 的 tool 列表裡），四個 docstring 的內容不要隨手改。來源：https://py.sdk.modelcontextprotocol.io/v2/get-started/first-steps
- **四個 tool 都 `return dict`，永遠不 `raise`。** SDK 對「handler 丟例外」的處理是把 tool result 標成 `is_error=True`，而規格要的是「操作失敗寫在回傳的 `error` 欄，MCP 呼叫仍成功」。來源：https://py.sdk.modelcontextprotocol.io/v2/servers/handling-errors
- `get_app()` 是 lazy 的：只有**真的呼叫 tool** 時才會建立 `ShowMeApp`（也才會在第一次用到時開瀏覽器）。所以 A01／A14 的「列出四個 tool」測試不會意外開一顆 Chrome。
- `set_app()` 只給測試用（A14 的 `mcp_client` fixture 會 `set_app(app)` 塞一個用 `FakeBrowser` 的 app，結束再 `set_app(None)` 還原）。正式程式碼不要呼叫它。
- `timeout_s: float = 120`（不是 `DEFAULT_TIMEOUT_S`）：這裡是**給模型看的 schema 預設值**，寫成字面數字比較直觀；`app.show_step` 那邊才用常數，兩邊值一樣。
- **回傳註記一律寫 `-> dict[str, object]`，不能寫裸 `-> dict`。** mcp 2.1.1 是從回傳型別註記推導 output schema 的，沒有參數的裸 `dict` 推不出 schema，`structured_content` 會一直是 `None`（dict 內容只會以 JSON 字串塞在 `content[0].text`）。寫成 `dict[str, object]` 才會拿到**裸 dict**（不是包一層的 `{"result": ...}`）。這是 A01 的實測結論，對照表見 `docs/plan/report/2026-08-29-階段1_A01環境建置-REP.md`「遇到的問題與怎麼解決」第 1 點。`app.py` 的四個方法跟著用同樣註記，保持一致。

### Step 6：跑測試看它綠（5 分鐘）

```bash
uv run pytest tests/test_fakes.py -q
```

預期輸出：

```text
.....................                                               [100%]
21 passed in 0.13s
```

再確認 **A01 的 smoke test 在 `server.py` 改薄殼之後仍然過**，以及 A02–A06 都沒被影響：

```bash
uv run pytest -m "not browser" -q
```

預期：全綠，`passed` 的數字 = Step 3 之前記下的數字 + 21。**這一步是本篇最重要的驗收**：`server.py` 被整個換掉，四個 tool 名稱、參數、無 `wait_for_user` 這些契約必須完全沒變。

如果 A01 的 smoke test 紅了，最可能的原因是 tool 的**函式名**或**參數名**打錯了（tool 名就是函式名，schema 就是參數名）。逐字對一次 Step 5 那份。

順便跑一次全部（含瀏覽器）：

```bash
uv run pytest -q
```

預期：全綠，總數 = 上面那個數字 + 18。

### Step 7：確認 MCP server 還啟動得起來（3 分鐘）

```bash
uv run showme
```

預期：**沒有任何輸出**，游標停住（它在等 stdin 的 JSON-RPC）。按 `Ctrl+C` 結束。

看到 traceback 就是薄殼寫壞了；最常見是 `ImportError: cannot import name 'ShowMeApp' from 'showme.app'`（`app.py` 沒存到）或 `TypeError: MCPServer.__init__() ...`（`instructions` 沒用關鍵字傳）。

### Step 8：commit（2 分鐘）

```bash
git add showme/app.py showme/server.py tests/fakes.py tests/test_fakes.py tests/conftest.py
git commit -m "feat(app): add ShowMeApp skeleton and FakeBrowser; make server.py a thin shell"
```

預期輸出：

```text
[main xxxxxxx] feat(app): add ShowMeApp skeleton and FakeBrowser; make server.py a thin shell
 5 files changed, 3xx insertions(+), 3x deletions(-)
```

---

## 8. 驗收清單

- [ ] `tests/fakes.py` 的 `FakeBrowser` 有 `BrowserLike` 的全部 11 個方法，另有 `emit`／`navigate`／`add_page`。
- [ ] `showme/app.py` 的 `_ensure_browser`／`_on_emit`／`_take_snapshot`／`shutdown` **完整實作**（沒有佔位）。
- [ ] `showme/app.py` 的四個 tool 方法都回 `{"error": "not_implemented"}`，簽名與 §6 完全一致（特別是 `show_step` 的八個參數與兩個預設值）。
- [ ] `showme/server.py` 是薄殼：`INSTRUCTIONS`、`mcp`、`get_app`／`set_app`、四個 `@mcp.tool()`，每個 tool 本體只有一行 `return await get_app().<方法>(...)`。
- [ ] `tests/conftest.py` 有五個 fixture：`anyio_backend`、`static_server`、`fake_browser`、`app`、`started`。
- [ ] `uv run pytest tests/test_fakes.py -q` → `21 passed`（含 4 個 parametrize）。
- [ ] `uv run pytest -m "not browser" -q` → 全綠，**A01 的 smoke test 仍然過**。
- [ ] `uv run pytest -q` → 全綠（含 18 個瀏覽器測試）。
- [ ] `uv run showme` 可以啟動、`Ctrl+C` 可以結束。
- [ ] `grep -rn "not_implemented" showme/` 只在 `app.py` 出現四次（`server.py` 裡**不該**再有）。
- [ ] `overlay/**`、`showme/browser.py`、`showme/session.py`、`showme/rules.py`、`showme/__main__.py` 都沒被改。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `ModuleNotFoundError: No module named 'fakes'` | 不在 repo 根目錄跑，或有人幫 `tests/` 加了 `__init__.py` | 在根目錄執行 `uv run pytest`；`rm tests/__init__.py`（如果存在）。 |
| `ModuleNotFoundError: No module named 'showme.app'`，而且**所有**測試都收集不了 | `conftest.py` 最上面 import 了還不存在的模組 | 先完成 Step 4 建 `app.py`。這是預期的紅→綠順序。 |
| `ImportError: cannot import name 'MAX_STEPS' from 'showme.session'` | A02 的常數名不一致 | 回頭對 A02；名字必須是 `MAX_STEPS`、`DEFAULT_TIMEOUT_S`、`DONE_BANNER_TEXT`、`START_NEXT_ACTION`、`STEP_NEXT_ACTION`。 |
| `fake_browser._handler == app._on_emit` 斷言失敗 | Python 的 bound method 每次取用都是新物件，但 `==` 對 bound method 是比較 `__self__` 與 `__func__`，會相等 | 若真的失敗，代表 `_ensure_browser` 沒有呼叫 `set_emit_handler`，或傳的不是 `self._on_emit`。（注意：這裡要用 `==` 不能用 `is`。） |
| `_take_snapshot` 回的 `page["elements"]` 是空的 | `fake_browser` 還停在 `about:blank` | 測試裡先 `fake_browser.navigate(DASHBOARD_URL)`（或等 A08 之後由 `start_tutorial` 的 `open()` 設定）。 |
| `page["url"]` 少一個結尾斜線 | 手打了 `http://localhost:3000` | 用 conftest 的 `DASHBOARD_URL` 常數；`FakeBrowser` 是用字串精確比對查頁面的。 |
| `asyncio.InvalidStateError: invalid state`（在 `set_result`） | `_on_emit` 沒有先檢查 `pending.done()` | 三道門的順序不能省，特別是第三道。 |
| `RuntimeError: no running event loop`（在 `create_future`） | 測試沒有 `anyio` marker，是在同步環境跑的 | 確認檔案最上面有 `pytestmark = pytest.mark.anyio`，而且該測試是 `async def`。 |
| A01 的 smoke test 紅：「tool 數量不是 4」 | 薄殼漏了一個 `@mcp.tool()`，或多打了一個 | 對 Step 5；四個且僅四個，沒有 `wait_for_user`。 |
| A01 的 smoke test 紅：「找不到 tool `show_step`」 | 函式名打錯（tool 名 = 函式名） | 四個函式名必須是 `start_tutorial`、`inspect_page`、`show_step`、`end_tutorial`。 |
| `uv run showme` 直接跳 traceback | `server.py` 語法錯或 import 迴圈 | 先 `uv run python -c "import showme.server"` 看完整錯誤。注意 `app.py` **不可以** import `server.py`（會變成循環 import）。 |
| 執行測試時真的跳出一顆 Chrome | 某個測試用了預設 factory（`ShowMeApp()`），沒傳 `browser_factory` | 用 `app` fixture，不要自己 `ShowMeApp()`。 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/features/顯示步驟.feature` | Rule：每步恰好回傳一次事件；同一 session 同一 ts 後至的事件丟棄（Example：同 ts 第二筆 `stuck` 不取代第一筆 `step_done`） | `_on_emit` 的第三道門（`pending.done()` 就 return）；`test_on_emit_ignores_the_second_event` 直接照那個 Example 寫。 |
| `docs/spec/features/顯示步驟.feature` | Rule：操作失敗時寫在回傳的 error，不丟例外 | `server.py` 的四個 tool 一律 `return await ...`，`app.py` 的四個方法一律 return dict；全檔沒有 `raise`。 |
| `docs/spec/features/等待使用者.feature` | Rule：MVP 不提供 `wait_for_user`（Example：可呼叫的工具不含 `wait_for_user`） | 薄殼只有四個 `@mcp.tool()`；A01 的 smoke test 與 A14 的契約測試都會再驗一次。 |
| `docs/spec/features/檢查頁面.feature` | Rule：成功時 uid snapshot# 比上一份加一（Example：`s1-4` → `s2-4`） | `_take_snapshot` 先 `session.snapshot_no += 1` 再 `browser.snapshot(n)`；`test_take_snapshot_twice_goes_from_s1_to_s2`。 |
| `docs/spec/features/開始教學.feature` | Rule：成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1 | `_take_snapshot` 從 `snapshot_no = 0` 起算 → 第一次呼叫得到 1。真正在 `start_tutorial` 裡串起來是 A08。 |
| `docs/spec/features/開始教學.feature` | Rule：啟動或重用 Chrome 並開啟傳入的 url | `_ensure_browser` 的重用邏輯（活著就重用、死了才重建）。「開啟 url」在 A08。 |
| `docs/spec/erm.dbml` | `Session`：`session_id`／`goal`／`state`／`steps_shown`，加上「Playwright page 握把 + snapshot# 計數 + 進行中 wait Future」 | `ShowMeApp` 持有 `_browser`，`Session` 持有 `snapshot_no`／`latest_page`／`pending`（A02 定義）。 |
| `docs/spec/erm.dbml` | `Page`：`url`／`title`／`truncated`，1:N `PageElement` | `_take_snapshot` 用 `build_page(raw, url, title)` 組出來，存進 `session.latest_page`（只留最新一份）。 |
| `docs/spec/erm.dbml` | `Event` 主鍵 `(session_id, ts)`；同 ts 後至丟棄；**不落盤** | `_on_emit` 不存任何歷史，只把第一筆放進 Future 就結束。 |
| `docs/spec/.clarify/resolved/data/Event_同一session同一ts出現兩筆事件時如何識別.md` | 回答 A：同 ts 後至事件丟棄，不新增序號欄位 | `_on_emit` 用 `pending.done()` 當「已經收過了」的判斷，沒有序號欄位。 |
| `docs/spec/.clarify/resolved/features/顯示步驟_錯誤是丟出ToolError還是寫在回傳值.md` | 錯誤寫在回傳的 `error` 欄，MCP 呼叫仍成功 | 薄殼與 App 都只 return dict。 |
| `docs/design/showme.md` §5 | 單向相依；`showme/` 不呼叫模型、不操作頁面 | `app.py` 只依賴 `BrowserLike`，`BrowserLike` 沒有 click／fill／type。 |
| `docs/design/showme.md` §7 | `MCPServer(name="showme", instructions=<SHOW protocol>)`；只有四個工具 | Step 5 的 `INSTRUCTIONS` 與四個 tool。 |
| `docs/design/showme.md` §9 | 資料模型在記憶體，不是 DB；只留最新一份 Page；不存歷史步驟 | `SessionStore` 至多一個 Session；`latest_page` 只有一份；沒有任何 list 累積步驟。 |
| `docs/design/showme.md` §13 | 只准用六個錯誤碼；成功時 `error` 為空字串 | `not_implemented` 是本篇的臨時鷹架，A13 之後 `showme/` 不再出現（驗收清單有這一條）。 |
| `docs/design/showme.md` §14 | 測試策略：「不啟動真實 MCP 客戶端也可先測」 | `FakeBrowser` + `app` fixture 讓 A08–A13 的邏輯測試不開瀏覽器、不啟動 MCP。 |
| `docs/design/showme.md` §17 open question（A 的設計決定 A-2，**可改**） | `end_tutorial` 之後瀏覽器不關，下次 `start_tutorial` 重用；被人手動關掉才重 launch | `_ensure_browser` 的 `is_alive()` 判斷；`shutdown()` 只在 process 收尾時用。**這是 A 的設計決定，不是規格。** |
| `docs/handoff.md` | `__showme_emit({ kind, url, ts })` 每步一次 | `FakeBrowser.emit(kind, url, ts)` 產生的就是這三個鍵的 dict，跟 `PlaywrightBrowser` 真的收到的形狀一致。 |
