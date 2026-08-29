# A05｜注入 overlay 與 emit 橋

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：`A04_瀏覽器層_開啟頁面.md` ｜ 下一篇：`A06_瀏覽器層_JS呼叫與假overlay.md`
> 對應設計：`docs/design/showme.md` §5、§12（Overlay 與 `__showme_emit` 邊界）、§15（切片 S2） ｜ 對應切片：**S2**
> 預估時間：45 分鐘

---

## 1. 這一篇要做什麼

在 `PlaywrightBrowser.launch()` 裡加兩行，把兩條線接起來：

1. **Python → 頁面**：`context.add_init_script(path=overlay/overlay.js)`，讓每一頁（含 reload、換頁）一載入就有 `window.__showme`。
2. **頁面 → Python**：`context.expose_function("__showme_emit", self._on_emit)`，讓頁面裡的 JS 可以呼叫一個函式，直接叫醒 Python。

再加 `_on_emit`（收到事件轉交給上層）與 `set_emit_handler`（上層登記自己要收）。

**這一篇是 A 和 B「過了再分頭」的檢查點。** `docs/handoff.md` 最後寫了兩條：

> 1. reload 後仍有 `window.__showme`
> 2. 頁面 `emit`，Python 收得到

這兩條就是本篇的測試。過了以後 A 可以一路做到 A15，不必等 B 的 overlay 寫完。

---

## 2. 做完會看到什麼

### 2.1 兩條線（這一篇補上了回頭的那條）

```text
      Python（asyncio 事件迴圈）                    Chrome 分頁
      ─────────────────────────                    ───────────────────────────
      launch()
        context.add_init_script(overlay.js) ──────▶ 每次建立 document 時先跑
        context.expose_function(                    ┌─────────────────────────┐
            "__showme_emit", self._on_emit) ──────▶ │ window.__showme         │
                                                    │   snapshot/show/clear/  │
                                                    │   done                  │
                                                    │ window.__showme_emit()  │
                                                    └───────────┬─────────────┘
      _on_emit(event)  ◀───── 頁面呼叫 emit ────────────────────┘
        └─▶ self._emit_handler(event)
              （A07 起是 ShowMeApp._on_emit，
                A12 會在裡面 future.set_result）
```

### 2.2 init script 的時間軸（為什麼 reload 之後還在）

```text
  一次導航（goto 或 reload 或使用者點連結）

  時間 ──────────────────────────────────────────────────────────▶

  │ 建立新的 document
  │      │
  │      ├─ [1] add_init_script 的內容在這裡跑   ← window.__showme 建立
  │      │        （頁面自己的 <script> 還沒跑）
  │      │
  │      ├─ [2] 頁面自己的 <script>、框架啟動
  │      │
  │      └─ [3] load 事件 → goto() / reload() 回來
  │
  └─ 之後 Python 才 evaluate("window.__showme.snapshot(1)")

  ※ 一般的 page.evaluate 注入只活到下一次導航；
    add_init_script 是登記在 Context 上，「每次」導航都會再跑一遍。
    這就是「reload 後 window.__showme 仍在」的原因。
```

### 2.3 `expose_function` 的一次呼叫走完

```text
  頁面 JS                     Playwright                 Python
  ────────                    ──────────                 ──────
  window.__showme_emit(ev)
     │ 回一個 Promise
     ├──── 送 binding call ───▶
     │                          asyncio.create_task(
     │                            binding.call(callback))
     │                                  │
     │                                  ├──▶ PlaywrightBrowser._on_emit(ev)
     │                                  │        └─▶ self._emit_handler(ev)
     │                                  │
     │      ◀──── resolve(None) ────────┘
     ▼
  Promise 兌現（await 的人醒來）

  ※ callback 是在「當初 await async_playwright().start() 的那個事件迴圈」上
    以一個 asyncio task 跑的，不是別的執行緒。
    → A12 在 handler 裡直接 future.set_result(...) 是安全的。
```

---

## 3. 開始前先確認

- [ ] **A04 的驗收都打勾**：`showme/browser.py` 存在；`uv run pytest -m browser -q` → `4 passed`。
  ```bash
  cd /Users/linjunting/hackathonQoder
  uv run pytest -m browser -q
  ```
  預期最後一行：`4 passed in 3.xxs`

- [ ] **`tests/conftest.py` 有 `static_server`**（A04 加的）：
  ```bash
  grep -n "def static_server" tests/conftest.py
  ```
  預期輸出（行號可能不同）：`17:def static_server():`

- [ ] **`tests/fixtures/pages/dashboard.html` 存在**：
  ```bash
  ls tests/fixtures/pages/
  ```
  預期輸出：`dashboard.html`

- [ ] **B 目前的 overlay stub 在，而且有 `window.__showme`**：
  ```bash
  cat overlay/overlay.js
  ```
  預期看到（B 已 commit 的骨架，`snapshot` 回空陣列）：
  ```javascript
  (function () {
    window.__showme = {
      snapshot: function (n) {
        return { elements: [], truncated: false };
      },
      show: function (opts) {},
      clear: function () {},
      done: function (text) {},
    };
  })();
  ```
  **這一篇就用這份 stub 測**。它已經定義了 `window.__showme`，足夠驗證「注入成功」與「reload 後還在」，所以 A 不必等 B 把真的高亮寫完。

- [ ] **`OVERLAY_PATH` 指得對**（A04 定義的常數）：
  ```bash
  uv run python -c "from showme.browser import OVERLAY_PATH; print(OVERLAY_PATH, OVERLAY_PATH.exists())"
  ```
  預期輸出：`/Users/<你>/hackathonQoder/overlay/overlay.js True`

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| init script | 「每頁開場白」。登記在 BrowserContext 上的一段 JS，每次建立新 document 時、在頁面自己的 script 之前執行。導航、reload 都會再跑一次。 |
| `expose_function` | 「在頁面上裝一個電話」。在頁面的 `window` 上掛一個函式名稱；頁面呼叫它時，實際執行的是 Python 那邊的 callback，回傳值以 Promise 送回頁面。 |
| binding | Playwright 對「頁面 ↔ 程式」這種函式橋接的內部叫法。`expose_function` 是 `expose_binding` 的簡化版（少一個 `source` 參數）。 |
| Promise | JS 的「之後才會有答案的信箱」。`window.__showme_emit(...)` 立刻回一個 Promise，等 Python callback 跑完才兌現。 |
| callback | 「你先把電話號碼給我，等事情發生我再打給你」。這裡的 `_on_emit` 就是留給頁面的號碼。 |
| handler | 我們自己再加一層轉接：`_on_emit` 收到後轉給 `self._emit_handler`。上層（A07 的 `ShowMeApp`）用 `set_emit_handler` 登記自己。 |
| 事件迴圈（event loop） | asyncio 排程 async 工作的那個東西。同一條執行緒上輪流跑很多 async 函式。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 修改 | `showme/browser.py` | `launch()` 裡加兩行（`add_init_script`、`expose_function`）；新增 `_on_emit`、`set_emit_handler` |
| 新增（測試） | `tests/test_browser_inject.py` | 注入成功、reload 後仍在、emit 收得到、跨 reload 仍收得到、沒 handler 不炸 |

**不要動**：`overlay/overlay.js`（B 的；本篇只是**讀**它當測試素材）、`tests/conftest.py`（本篇不需要改）、`showme/server.py`。

---

## 6. 介面約定

### 用到（來自 A04）

```python
# showme/browser.py（A04 已經有）
OVERLAY_PATH: Path                     # <repo>/overlay/overlay.js
EMIT_FUNCTION_NAME = "__showme_emit"
EmitHandler = Callable[[dict], None]

class PlaywrightBrowser:
    def __init__(self, overlay_path: Path = OVERLAY_PATH, headless: bool = False) -> None: ...
    async def launch(self) -> None: ...      # 本篇在裡面加兩行
    self.page                                # playwright Page，測試會直接拿來 evaluate
    self._context                            # playwright BrowserContext
    self._emit_handler: EmitHandler | None   # A04 已在 __init__ 設成 None
```

### 提供（給後面幾篇）

```python
class PlaywrightBrowser:
    def _on_emit(self, event: dict) -> None:
        """頁面呼叫 window.__showme_emit(event) 時進來；有 handler 就轉交，沒有就忽略。回 None。"""

    def set_emit_handler(self, handler: EmitHandler | None) -> None:
        """上層登記自己要收 emit；傳 None 取消。"""
```

- A07 的 `ShowMeApp._ensure_browser` 會呼叫 `browser.set_emit_handler(self._on_emit)`。
- A12 的 `ShowMeApp._on_emit` 會在裡面 `session.pending.set_result(event)`，把卡在 `show_step` 的那個 await 叫醒。
- **鎖死的事件形狀**（`docs/handoff.md`，不可改）：
  ```text
  window.__showme_emit({ kind: "step_done" | "stuck", url, ts })
  ```
  B 不發 `timeout`；`timeout` 是 A 在 Python 用計時器決定，寫在 `StepResult.event`。

---

## 7. 步驟

### Step 1：先寫測試，看它紅（8 分鐘）

新增 `tests/test_browser_inject.py`：

```python
"""A05：overlay 注入與 emit 橋。用的是 B 目前的 overlay/overlay.js（stub）。

這兩件事過了，A 和 B 才可以分頭做（docs/handoff.md「過了再分頭」）：
1. reload 之後 window.__showme 仍在
2. 頁面呼叫 window.__showme_emit(...)，Python 收得到

    uv run pytest -m browser tests/test_browser_inject.py -q
"""

from __future__ import annotations

import pytest

from showme.browser import PlaywrightBrowser

pytestmark = [pytest.mark.anyio, pytest.mark.browser]


@pytest.fixture
async def browser():
    """用預設的 overlay_path（也就是 B 的 overlay/overlay.js）。"""
    b = PlaywrightBrowser(headless=True)
    await b.launch()
    try:
        yield b
    finally:
        await b.close()


async def test_overlay_is_injected(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    assert await browser.page.evaluate("typeof window.__showme") == "object"
    assert await browser.page.evaluate("typeof window.__showme.snapshot") == "function"


async def test_overlay_survives_reload(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    await browser.page.reload()

    assert await browser.page.evaluate("typeof window.__showme") == "object"
    assert await browser.page.evaluate("typeof window.__showme.show") == "function"


async def test_emit_function_exists_in_page(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    assert await browser.page.evaluate("typeof window.__showme_emit") == "function"


async def test_emit_reaches_python(browser, static_server):
    received: list[dict] = []
    browser.set_emit_handler(received.append)
    await browser.open(f"{static_server}/dashboard.html")

    await browser.page.evaluate(
        "window.__showme_emit({kind: 'step_done', url: location.href, ts: 1})"
    )

    assert len(received) == 1
    assert received[0]["kind"] == "step_done"
    assert received[0]["ts"] == 1
    assert received[0]["url"].endswith("/dashboard.html")


async def test_emit_still_works_after_reload(browser, static_server):
    received: list[dict] = []
    browser.set_emit_handler(received.append)
    await browser.open(f"{static_server}/dashboard.html")
    await browser.page.reload()

    await browser.page.evaluate(
        "window.__showme_emit({kind: 'stuck', url: location.href, ts: 2})"
    )

    assert [event["kind"] for event in received] == ["stuck"]


async def test_emit_without_handler_does_not_raise(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    result = await browser.page.evaluate(
        "window.__showme_emit({kind: 'step_done', url: location.href, ts: 3})"
    )

    assert result is None
```

**幾個要看懂的地方：**

- `browser.set_emit_handler(received.append)`：`list.append` 剛好就是「吃一個參數、回 None」的函式，正好符合 `EmitHandler = Callable[[dict], None]`。不用另外寫一個假的 handler class。
- `await browser.page.evaluate("window.__showme_emit({...})")` —— **這個 `await` 很重要**。`window.__showme_emit(...)` 回的是一個 Promise；Playwright 的 `evaluate` 遇到 Promise 會自己等它兌現才回來。所以 `evaluate` 一回來，Python 的 `_on_emit` **一定已經跑完了**，下一行的 `assert len(received) == 1` 不會有時序問題。
  （如果 `evaluate` 不等 Promise，這個測試就會偶爾紅、偶爾綠 —— 那種測試最難修，所以特別點出來。）
- 傳給 `evaluate` 的字串是**運算式**（不是箭頭函式），Playwright 會直接求值。之後 A06 要傳參數時才會寫成 `"(n) => ..."` 的形式。
- `result is None`：Python callback 回 `None` → 頁面拿到 `undefined` → `evaluate` 回到 Python 又變成 `None`。
- `test_emit_without_handler_does_not_raise` 是防呆：MCP server 剛啟動、還沒有 Session 時，如果頁面因為任何原因 emit，不可以把瀏覽器或 Python 弄爆。

跑一次看紅：

```bash
uv run pytest -m browser tests/test_browser_inject.py -q
```

預期輸出（六個測試，三種紅法都可能出現，重點是有 failed）：

```text
FFF...                                                              [100%]
=================================== FAILURES ===================================
______________________________ test_overlay_is_injected ________________________
E       AssertionError: assert 'undefined' == 'object'
...
____________________________ test_emit_reaches_python __________________________
E       playwright._impl._errors.Error: Page.evaluate: TypeError:
        window.__showme_emit is not a function
...
E       AttributeError: 'PlaywrightBrowser' object has no attribute 'set_emit_handler'
...
6 failed in 5.12s
```

三種紅訊息分別對應三件還沒做的事：沒注入 overlay（`undefined`）、沒 expose 函式（`is not a function`）、沒有 `set_emit_handler`。

### Step 2：改 `launch()`，加兩行（5 分鐘）

在 `showme/browser.py` 的 `launch()` 裡，`new_context()` 之後、`new_page()` **之前**，插入兩行：

```python
    async def launch(self) -> None:
        self._pw = await async_playwright().start()
        try:
            self._browser = await self._pw.chromium.launch(
                channel="chrome", headless=self.headless
            )
        except Exception:
            self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context()
        await self._context.add_init_script(path=self.overlay_path)
        await self._context.expose_function(EMIT_FUNCTION_NAME, self._on_emit)
        self.page = await self._context.new_page()
```

**順序不能換。** 兩者都是登記在 **Context** 上的設定，要在 `new_page()` 之前登記好，第一個分頁才吃得到。如果先開了分頁再登記，那個分頁要 reload 一次才會有 `window.__showme`（`expose_function` 對已存在的頁也會補掛，但 init script 不會回頭補跑）。這種「要 reload 一次才正常」的行為在 demo 現場很難查。

### Step 3：加 `_on_emit` 與 `set_emit_handler`（3 分鐘）

`_on_emit` 放在 `launch()` 後面（順序照 A00 的模組地圖），`set_emit_handler` 放在 `close()` 前面：

```python
    def _on_emit(self, event: dict) -> None:
        if self._emit_handler is None:
            return
        self._emit_handler(event)
```

```python
    def set_emit_handler(self, handler: EmitHandler | None) -> None:
        self._emit_handler = handler
```

**為什麼 `_on_emit` 是同步（`def` 不是 `async def`）？**
Playwright 的 callback 兩種都收：同步函式直接呼叫、非同步函式會 `await`。我們選同步，因為：

1. 它要做的事只有「把 dict 交出去」與（A12 起）「`future.set_result(...)`」，都是瞬間完成、不需要 await 的動作。
2. 同步 callback 執行時不會被其他 task 插隊，所以「每步只取第一筆 emit」的判斷（A07 的 `ShowMeApp._on_emit` 會檢查 `pending.done()`）不會有競態。

**它在哪個執行緒／事件迴圈跑？**
在「當初 `await async_playwright().start()` 的那個事件迴圈」上，以 `asyncio.create_task(...)` 起一個 task 執行 —— **不是**另一條執行緒。（Playwright Python 1.62.0 的 `BrowserContext._on_binding` 就是 `asyncio.create_task(binding_call.call(func))`；官方文件對 `expose_function` 的描述是「callback 在 Playwright 的 context 中執行」，見 https://playwright.dev/python/docs/api/class-browsercontext ）

這件事對 A12 很關鍵：因為同一個迴圈，所以之後可以在 handler 裡**直接** `future.set_result(...)`，不需要 `loop.call_soon_threadsafe(...)`。

**`_on_emit` 丟例外會怎樣？**
Playwright 會把例外送回頁面，讓那個 Promise reject —— Python 這邊不會整個爆掉。但頁面上會出現一個未處理的 rejection，很難查。所以 A07 的 `ShowMeApp._on_emit` 寫成「先檢查、不符合就 return」，不倚賴例外。

### Step 4：跑測試看它綠（3 分鐘）

```bash
uv run pytest -m browser tests/test_browser_inject.py -q
```

預期輸出：

```text
......                                                              [100%]
6 passed in 4.83s
```

全部瀏覽器測試一起跑（A04 的四個 + 本篇六個）：

```bash
uv run pytest -m browser -q
```

預期輸出：

```text
..........                                                          [100%]
10 passed in 8.11s
```

不開瀏覽器那組不受影響：

```bash
uv run pytest -m "not browser" -q
```

預期最後一行類似：`28 passed, 10 deselected in 0.43s`

### Step 5：用眼睛看一次注入（5 分鐘）

自動測試綠了，但這是 A/B 的交界，值得手動看一眼。把 `scripts/dev_open.py` 跑起來、開一個真視窗，然後在 Chrome 的 DevTools Console 打字確認：

```bash
uv run python scripts/dev_open.py https://example.com
```

視窗跳出來後（只有 10 秒，動作快一點；也可以先把 `asyncio.sleep(10)` 改成 `asyncio.sleep(60)`）：

1. 按 `Cmd+Option+J` 開 Console。
2. 輸入 `window.__showme` → 應該印出一個物件，展開看得到 `snapshot`、`show`、`clear`、`done` 四個 function。
3. 輸入 `typeof window.__showme_emit` → 應該印 `"function"`。
4. 輸入 `window.__showme_emit({kind:"step_done", url:location.href, ts:1})` → 印出一個 `Promise {<fulfilled>: undefined}`。（Python 那邊沒有登記 handler，所以什麼都不會發生 —— 這正是 `test_emit_without_handler_does_not_raise` 驗的行為。）
5. 按 `Cmd+R` reload，再打一次 `window.__showme` → **還在**。

這第 5 點就是 `docs/handoff.md`「過了再分頭」的第 1 條，用眼睛再確認一次。

### Step 6：把「這一篇改完後的完整 `browser.py`」對一遍（3 分鐘）

貼出來對照（**這是本篇結束時 `showme/browser.py` 應有的全部內容**）：

```python
"""Playwright 瀏覽器層：ShowMe 唯一碰瀏覽器的檔案。

上層（showme/app.py）只依賴 BrowserLike 這個介面，所以測試可以換成
tests/fakes.py 的 FakeBrowser，不必真的開瀏覽器。

本檔在 A04 建立（開頁），A05 補注入與 emit 橋，A06 補四個 JS 呼叫。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from playwright.async_api import async_playwright

OVERLAY_PATH = Path(__file__).resolve().parent.parent / "overlay" / "overlay.js"
EMIT_FUNCTION_NAME = "__showme_emit"
EmitHandler = Callable[[dict], None]


class NavigationFailed(Exception):
    """page.goto 丟錯時由 open() 轉成這個。"""


class BrowserLike(Protocol):
    """app.py 只依賴這個介面；真的 PlaywrightBrowser 與測試用 FakeBrowser 都實作它。"""

    async def launch(self) -> None: ...
    async def is_alive(self) -> bool: ...
    async def open(self, url: str) -> None: ...
    async def current_url(self) -> str: ...
    async def title(self) -> str: ...
    async def snapshot(self, n: int) -> dict: ...
    async def show(self, opts: dict) -> None: ...
    async def clear(self) -> None: ...
    async def done(self, text: str) -> None: ...
    def set_emit_handler(self, handler: EmitHandler | None) -> None: ...
    async def close(self) -> None: ...


class PlaywrightBrowser:
    def __init__(self, overlay_path: Path = OVERLAY_PATH, headless: bool = False) -> None:
        self.overlay_path = overlay_path
        self.headless = headless
        self.page = None        # playwright Page；測試會直接用它 evaluate
        self._pw = None
        self._browser = None
        self._context = None
        self._emit_handler: EmitHandler | None = None

    async def launch(self) -> None:
        self._pw = await async_playwright().start()
        try:
            self._browser = await self._pw.chromium.launch(
                channel="chrome", headless=self.headless
            )
        except Exception:
            self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context()
        await self._context.add_init_script(path=self.overlay_path)
        await self._context.expose_function(EMIT_FUNCTION_NAME, self._on_emit)
        self.page = await self._context.new_page()

    def _on_emit(self, event: dict) -> None:
        if self._emit_handler is None:
            return
        self._emit_handler(event)

    async def is_alive(self) -> bool:
        if self.page is None or self._browser is None:
            return False
        return not self.page.is_closed() and self._browser.is_connected()

    async def open(self, url: str) -> None:
        try:
            await self.page.goto(url)
        except Exception as exc:
            raise NavigationFailed(str(exc)) from exc

    async def current_url(self) -> str:
        return self.page.url

    async def title(self) -> str:
        return await self.page.title()

    def set_emit_handler(self, handler: EmitHandler | None) -> None:
        self._emit_handler = handler

    async def close(self) -> None:
        for closeable in (self._context, self._browser):
            if closeable is None:
                continue
            try:
                await closeable.close()
            except Exception:
                pass
        if self._pw is not None:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self.page = None
        self._context = None
        self._browser = None
        self._pw = None
```

（A06 會在 `title()` 與 `set_emit_handler()` 之間插入 `snapshot`／`show`／`clear`／`done` 四個方法，那時候檔案就完成了。）

### Step 7：跟 B 對一次接縫（5 分鐘，如果 B 在旁邊）

`docs/design/showme.md` §15 說 S2 要「兩人一起鎖定介面（約 20 分鐘）後再分頭」。接縫已經寫在 `docs/handoff.md`，這裡只是逐項唸過確認：

```text
A 在頁面裡呼叫（page.evaluate）：
  window.__showme.snapshot(n)  → { elements: [{uid, role, name, testid}], truncated: bool }
  window.__showme.show({ uid, instruction, kind, index, total, expect })
  window.__showme.clear()
  window.__showme.done(text)

B 在頁面裡呼叫（每步恰好一次；A 用 expose_function 接）：
  window.__showme_emit({ kind: "step_done" | "stuck", url, ts })
```

要當面確認的四件事：

1. `uid` 的 `n` **由 A 傳入**，B 只負責組 `s{n}-{index}` 這個字串。B 不自己記世代。
2. `elements[]` 每一筆**四個鍵都要在**；沒有 `data-testid` 時 `testid` 是 `""`，不是省略鍵。
3. B **不發** `timeout`。timeout 是 A 在 Python 用計時器決定的。
4. `show` 的 `expect` 就是 MCP 參數的 `expect_text`；`index`／`total` 就是 `step_index`／`step_total`。名字在邊界上換過，別搞混。

確認完就可以分頭：A 走 A06 → A15，B 去把 overlay 寫成真的。等 B 完成後，A16 會把 `overlay/overlay.js` 換成真的，再跑一次本篇的六個測試 —— **它們不需要改一個字就應該繼續綠**，因為它們只依賴 `window.__showme` 是個物件、`window.__showme_emit` 是個函式。

### Step 8：commit（2 分鐘）

```bash
git add showme/browser.py tests/test_browser_inject.py
git commit -m "feat(browser): inject overlay init script and expose __showme_emit (S2)"
```

預期輸出：

```text
[main xxxxxxx] feat(browser): inject overlay init script and expose __showme_emit (S2)
 2 files changed, 1xx insertions(+)
```

---

## 8. 驗收清單

- [ ] `launch()` 裡 `add_init_script` 與 `expose_function` 都在 `new_context()` **之後**、`new_page()` **之前**。
- [ ] `PlaywrightBrowser` 有 `_on_emit`（同步）與 `set_emit_handler`。
- [ ] `uv run pytest -m browser tests/test_browser_inject.py -q` → `6 passed`。
- [ ] `uv run pytest -m browser -q` → `10 passed`（A04 的 4 個 + 本篇 6 個）。
- [ ] `uv run pytest -m "not browser" -q` → 全綠。
- [ ] **handoff 檢查點 1**：DevTools 裡 reload 後 `window.__showme` 仍在（Step 5 手動確認過）。
- [ ] **handoff 檢查點 2**：頁面 `window.__showme_emit({...})` 之後，Python 的 list 收到一個 dict（`test_emit_reaches_python` 綠）。
- [ ] `overlay/overlay.js` 沒有被改（`git status` 看不到它）。
- [ ] commit 已建立，只含 `showme/browser.py` 與 `tests/test_browser_inject.py`。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `typeof window.__showme` 回 `"undefined"` | `add_init_script` 沒加、或 `overlay_path` 指到不存在的檔 | `uv run python -c "from showme.browser import OVERLAY_PATH; print(OVERLAY_PATH.exists())"` 應為 `True`。注意 `OVERLAY_PATH` 是 `Path(__file__).resolve().parent.parent / "overlay" / "overlay.js"`，`resolve()` 不能省，否則從別的工作目錄跑會算錯。 |
| 第一次開頁沒有 `__showme`，reload 一次就有 | `add_init_script` 寫在 `new_page()` **之後** | 把兩行搬到 `new_page()` 之前。 |
| `Page.evaluate: TypeError: window.__showme_emit is not a function` | `expose_function` 沒呼叫，或名字打錯 | 用常數 `EMIT_FUNCTION_NAME`，不要手打字串；確認它的值是 `"__showme_emit"`（兩個底線開頭）。 |
| `Error: Function "__showme_emit" has been already registered` | `launch()` 被呼叫兩次卻共用同一個 context | 每次 `launch()` 都應該建新的 `_pw`／`_browser`／`_context`。若是在測試裡重複 launch 同一個物件，先 `await b.close()`。 |
| `received` 是空的，但 `evaluate` 沒報錯 | 忘了 `set_emit_handler`，或在 `open()` **之後**才設 | `set_emit_handler` 何時設都可以（它只改 Python 這邊的欄位），但要在 `evaluate` 觸發 emit **之前**。檢查測試裡的順序。 |
| 測試偶爾紅、偶爾綠 | `evaluate` 的回傳沒有 `await` | 一定要 `await browser.page.evaluate(...)`。少了 await，Python 不會等頁面那個 Promise 兌現。 |
| `_on_emit` 收到的 `ts` 是 `1.0` 不是 `1` | JS 只有一種數字型別，Playwright 會依值決定給 int 或 float | 測試用 `== 1` 比較（`1.0 == 1` 為 True），不要用 `is` 或 `type()` 比。 |
| B 換上真 overlay 之後，`test_overlay_is_injected` 紅了 | 真 overlay 執行時丟例外（例如 Driver.js 沒載到） | 這是 A16 合流時的事。用 `browser.page.on("console", print)` 或在 DevTools Console 看紅字，把訊息貼給 B。**不要**自己去改 `overlay/`。 |
| `PytestUnknownMarkWarning: Unknown pytest.mark.anyio` | 沒裝 `anyio` 或 `anyio_backend` fixture 不見了 | `uv sync`；確認 `tests/conftest.py` 有 `anyio_backend`。 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/features/開始教學.feature` | Rule：注入 overlay.js（`#TODO`，無 Example） | `launch()` 用 `context.add_init_script(path=self.overlay_path)`；`test_overlay_is_injected` 驗證頁面上真的有 `window.__showme`。 |
| `docs/spec/features/開始教學.feature` | Rule：啟動或重用 Chrome 並開啟傳入的 url（`#TODO`） | 本篇讓「重用」變得有意義：init script 與 expose 都掛在 Context 上，人在頁面上點來點去、換頁、reload，`window.__showme` 與 `window.__showme_emit` 都還在。 |
| `docs/spec/features/顯示步驟.feature` | Rule：每步恰好回傳一次事件；同一 session 同一 ts 後至的事件丟棄 | 本篇只鋪**管道**（頁面 → Python）。「只取第一筆」的判斷在 A07 的 `ShowMeApp._on_emit`（檢查 `pending.done()`），A12 有對應測試。 |
| `docs/spec/erm.dbml` | `Event`：`session_id`／`ts`／`kind`／`signal`／`url`；overlay 只發 `step_done`／`stuck`／`off_script` | `_on_emit(event: dict)` 原封不動把 dict 往上送，不在這一層解析或過濾欄位。MVP overlay 不發 `off_script`。 |
| `docs/spec/.clarify/resolved/data/Event_overlay的kind與StepResult的event是否使用同一組值.md` | overlay 的 `kind` 與 `StepResult.event` 分開建模；`timeout` 只在 `StepResult.event` | `_on_emit` 不會製造 `timeout`；本篇也沒有任何計時器。timeout 是 A12 在 `app.show_step` 用 `asyncio.wait_for` 做的。 |
| `docs/design/showme.md` §5 | design：`add_init_script` 在每次導航、document 腳本之前執行 | Step 1 的 `test_overlay_survives_reload` 就是驗這件事。 |
| `docs/design/showme.md` §5 / §3.1（A 的設計決定 A-5，可改） | `expose_function` 掛在哪：設計文件寫 `page.expose_function`，A 選 **`context.expose_function`** | 掛在 Context 上，跨 page 與跨導航都在，和 `add_init_script` 同一層，比較好推理。這是 **A 的設計決定（可改）**，不是規格；行為上兩者都滿足「跨導航仍在」。 |
| `docs/design/showme.md` §12 | Python：`add_init_script`、`expose_function`；**不**在 Python 做 click／fill | 本篇只加這兩個註冊動作，沒有任何操作頁面的方法。 |
| `docs/design/showme.md` §15 | 切片 S2：驗證 reload 後 `window.__showme` 仍在；頁面能呼叫 emit 印到 Python | Step 1 的六個測試 + Step 5 的手動確認。 |
| `docs/handoff.md` | 「過了再分頭」1：reload 後仍有 `window.__showme` | `test_overlay_survives_reload` |
| `docs/handoff.md` | 「過了再分頭」2：頁面 `emit`，Python 收得到 | `test_emit_reaches_python`、`test_emit_still_works_after_reload` |
| `docs/handoff.md` | 鎖死的名字：`__showme_emit({ kind, url, ts })` | 測試用的就是這三個鍵，且常數 `EMIT_FUNCTION_NAME = "__showme_emit"` 不可改。 |
