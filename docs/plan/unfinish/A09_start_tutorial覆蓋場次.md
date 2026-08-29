# A09｜start_tutorial 覆蓋既有場次

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：`A08_start_tutorial.md` ｜ 下一篇：`A10_inspect_page.md`
> 對應設計：`docs/design/showme.md` §6（覆蓋）、§7.1（覆蓋時的行為）、§8（狀態機）、§17 open question 2 ｜ 對應切片：S5
> 預估時間：40–55 分鐘

---

## 1. 這一篇要做什麼

A08 的 `start_tutorial` 只會「新建」場次：每呼叫一次就 `store.create()` 一個新的 `session_id`。規格要的是**同一個 process 永遠只有一個場次**：Session 還在時再呼叫 `start_tutorial`，要**沿用同一個 `session_id`**、覆寫 `goal`、開新網址、`steps_shown` 歸零、snapshot# 從 1 重算、狀態回 `READY`。

這一篇把覆蓋路徑補上，順便處理三件覆蓋才會遇到的事：

1. 覆蓋前要先 `clear()` 舊的 overlay（不然舊箭頭會留在畫面上）。
2. 瀏覽器被人手動關掉時，要重新 launch 一個。
3. 覆蓋時如果有一次 `show_step` 正卡在等使用者，要把它叫醒（**OQ2，A 的設計決定，可改**）。

---

## 2. 做完會看到什麼

### 2.1 覆蓋前後的 Session 欄位對照

```text
                  覆蓋前（第一次 start 之後，可能已經走了幾步）   覆蓋後（第二次 start 成功之後）
  ─────────────  ──────────────────────────────────────────  ─────────────────────────────
  session_id      s_8f2a                                       s_8f2a          ← 不變
  goal            create a project                             invite a member ← 覆寫
  state           READY 或 SHOWING                              READY           ← 一律回 READY
  steps_shown     3                                            0               ← 歸零
  snapshot_no     4                                            1               ← 從頭算，uid 又是 s1-*
  latest_page     舊頁的 elements（s4-*）                        新頁的 elements（s1-*）
  pending         Future（正在等 emit）或 None                   None            ← 先解掉再清空
```

### 2.2 第二次 `start_tutorial` 的呼叫順序

```text
app.start_tutorial(new_url, new_goal)
  │
  ├─(1) _ensure_browser() ── 活著 ──▶ 沿用同一個 browser（不再 launch）
  │                       └─ 死了 ──▶ factory() 造一個新的 + launch()
  │
  ├─(2) 有 Session 且 state 是 SHOWING 且 pending 還沒 done？
  │        └──▶ pending.set_result({"kind": "cancelled", "url": "", "ts": 0})   ← OQ2
  │
  ├─(3) 有 Session？ ──▶ await browser.clear()                 記錄 ("clear",)
  │
  ├─(4) await browser.open(new_url)                            記錄 ("open", new_url)
  │        └── 丟 NavigationFailed ──▶ store.delete() ──▶ error="navigation_failed"
  │
  ├─(5) 有 Session ──▶ 覆寫欄位（goal/state/steps_shown/snapshot_no/pending/latest_page）
  │     沒有        ──▶ store.create(goal)
  │
  ├─(6) _take_snapshot()                                       記錄 ("snapshot", 1)
  │
  └─(7) 回傳成功形狀（session_id 與覆蓋前相同）
```

`FakeBrowser.calls` 在「start → start」之後應該長這樣：

```text
[("open", "http://localhost:3000/"), ("snapshot", 1),
 ("clear",), ("open", "http://localhost:3000/projects/new"), ("snapshot", 1)]
   ▲                                                                     ▲
   第一次沒有 clear（那時還沒有 Session）                                    覆蓋後 snapshot# 又是 1
```

---

## 3. 開始前先確認

- [ ] A08 的驗收全部打勾，`uv run pytest tests/test_tool_start.py -q` 是 11 passed。
- [ ] `showme/app.py` 的 `start_tutorial` 目前長這樣（A08 的成果）：

```python
    async def start_tutorial(self, url: str, goal: str) -> dict:
        browser = await self._ensure_browser()
        try:
            await browser.open(url)
        except NavigationFailed:
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

- [ ] `showme/session.py` 的 `Session` 是 `@dataclass`，欄位可以直接指派（例如 `session.goal = "..."`）。
- [ ] `tests/fakes.py` 的 `FakeBrowser` 有 `alive` 屬性、`calls` list、`add_page()`、`navigate()`、`emit()`。
- [ ] `tests/conftest.py` 有 `fake_browser`、`app`、`started` 三個 fixture。
- [ ] `showme/app.py` 的 `_ensure_browser()` 是「沒有瀏覽器**或 `is_alive()` 回 False**」才呼叫 factory。
- [ ] `uv run pytest -m "not browser" -q` 全綠。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| 覆蓋（override） | 不是「刪掉舊的再開新的」，而是「同一張記事本上把字擦掉重寫」。`session_id` 是那張記事本的編號，所以不會變。 |
| Future | 「之後才會有答案的信箱」。`await` 它的人會睡著，等別人 `set_result(...)` 放答案進去才醒來。`show_step` 阻塞等使用者就是在 await 這個信箱。 |
| `pending.done()` | 問信箱「已經有答案了嗎？」。已經有答案時再 `set_result()` 會丟 `InvalidStateError`，所以放答案前一定要先問。 |
| `set_result(value)` | 把答案放進信箱，睡著的人立刻被排進事件迴圈準備醒來。 |
| OQ2 | design §17 的第 2 個 open question：「SHOWING 時 `start_tutorial` 覆蓋，已阻塞的 `show_step` 如何結束」。規格沒寫，A 先決定：那次 `show_step` 回 `event="timeout"`、`page=None`、`error=""`。**可改**。 |
| `@pytest.mark.skip` | 告訴 pytest「這條先別跑」，結果會顯示 `s`（skipped）而不是失敗。用在「測試已經寫好，但要等後面的實作才能通過」。 |
| monkeypatch | 在測試裡臨時把某個屬性換成自己的版本（例如把 `fake.launch` 換成會計數的版本），測完就丟。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 修改 | `showme/app.py` | 只改 `ShowMeApp.start_tutorial()`。其他方法一律不動。 |
| 修改 | `tests/test_tool_start.py` | 在 A08 的檔案裡繼續加測試（上面 11 條保持原樣）。 |

---

## 6. 介面約定

### 6.1 用到（重述精確簽名）

```python
# showme/session.py
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

class SessionStore:
    def current(self) -> Session | None: ...
    def get(self, session_id: str) -> Session | None: ...
    def create(self, goal: str) -> Session: ...
    def delete(self) -> None: ...

START_NEXT_ACTION = (
    "Plan 3–8 steps in your head, then call show_step for the FIRST step "
    "using a uid from page.elements."
)

# showme/browser.py
class NavigationFailed(Exception): ...
# BrowserLike: launch / is_alive / open / current_url / title / snapshot / show / clear / done
#              / set_emit_handler / close

# showme/app.py（A07 已完成）
async def _ensure_browser(self) -> BrowserLike: ...   # 沒有或已死 → factory() + launch() + set_emit_handler
async def _take_snapshot(self, session: Session) -> dict: ...  # snapshot_no += 1，回 page 並寫進 latest_page

# tests/fakes.py
class FakeBrowser:
    def __init__(self, *, fail_urls: set[str] | None = None) -> None: ...
    launched: bool
    alive: bool
    calls: list[tuple]          # ("open", url) / ("snapshot", n) / ("show", opts) / ("clear",) / ("done", text) / ("close",)
    def add_page(self, url: str, title: str, elements: list[dict], truncated: bool = False) -> None: ...
    def navigate(self, url: str) -> None: ...
    def emit(self, kind: str, url: str | None = None, ts: int = 0) -> None: ...
```

### 6.2 提供（給後面幾篇）

```python
async def start_tutorial(self, url: str, goal: str) -> dict
# 沒有 Session：新建（A08）
# 有 Session：同 session_id、覆寫 goal、clear() 舊 overlay、開新 url、
#             steps_shown=0、snapshot_no 從 0 重算（拍完是 1）、state=READY、pending=None、latest_page=None
# 有 pending 且 state 是 SHOWING：pending.set_result({"kind": "cancelled", "url": "", "ts": 0})
```

A12 的 `show_step` 會依賴這個約定：它 `await` 的 future 若拿到 `{"kind": "cancelled"}`，就回 `event="timeout"`、`page=None`、`error=""`，而且**不再碰瀏覽器與 Session**（那些已經被 `start_tutorial` 換掉了）。

---

## 7. 步驟

### Step 1：先加 `import asyncio` 與一個小 helper

打開 `tests/test_tool_start.py`。把最上面的 import 區塊改成（多一行 `import asyncio`）：

```python
"""start_tutorial 的行為測試。全部用 FakeBrowser，不開瀏覽器。"""

from __future__ import annotations

import asyncio

import pytest

from fakes import FakeBrowser
from showme.app import ShowMeApp
from showme.session import START_NEXT_ACTION, State

pytestmark = pytest.mark.anyio

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"
BAD_URL = "http://localhost:1/"


def make_dashboard_browser(*, fail_urls: set[str] | None = None) -> FakeBrowser:
    """跟 conftest 的 fake_browser 一樣的兩頁，但可以自己指定 fail_urls。"""
    browser = FakeBrowser(fail_urls=fail_urls)
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
```

底下 A08 寫的 11 條測試原封不動留著。

跑一次確認沒打壞東西：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
11 passed in 0.12s
```

---

### Step 2：寫覆蓋的測試（會紅）

在 `tests/test_tool_start.py` 最後加上五條：

```python
# Rule: 同一時間只允許一個教學場次，再次開始教學時場次識別不變並覆蓋目標與網址
async def test_restart_keeps_the_session_id_and_overwrites_the_goal(started):
    app, fake, first = started

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert second["error"] == ""
    assert second["session_id"] == first["session_id"]
    assert second["goal"] == "invite a member"
    assert second["next_action"] == START_NEXT_ACTION


# Rule: 同一時間只允許一個教學場次，再次開始教學時場次識別不變並覆蓋目標與網址
async def test_restart_opens_the_new_url(started):
    app, fake, first = started

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert ("open", NEW_PROJECT_URL) in fake.calls
    assert second["page"]["url"] == NEW_PROJECT_URL
    assert second["page"]["title"] == "New Project"


# Rule: 同一時間只允許一個教學場次…（Example：進行中再開始另一個目標，steps_shown 為 0）
async def test_restart_resets_steps_shown(started):
    app, fake, first = started
    app.store.current().steps_shown = 3

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    session = app.store.get(first["session_id"])
    assert session is not None
    assert session.steps_shown == 0


# Rule: 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1（含覆蓋既有場次）
async def test_restart_restarts_snapshot_numbering(started):
    app, fake, first = started

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    uids = [element["uid"] for element in second["page"]["elements"]]
    assert uids != []
    assert all(uid.startswith("s1-") for uid in uids)
    session = app.store.get(first["session_id"])
    assert session is not None
    assert session.snapshot_no == 1
    assert fake.calls.count(("snapshot", 1)) == 2


# Rule: 同一時間只允許一個教學場次…（Example：進行中再開始另一個目標，state 為 READY）
async def test_restart_leaves_the_session_ready(started):
    app, fake, first = started
    app.store.current().state = State.SHOWING

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    session = app.store.get(first["session_id"])
    assert session is not None
    assert session.state is State.READY
    assert session.pending is None
    assert session.latest_page == app.store.current().latest_page
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期紅燈，重點行類似：

```text
E       assert 's_3c71' == 's_8f2a'
E        +  where 's_3c71' = <dict>['session_id']
...
4 failed, 12 passed in 0.14s
```

（`test_restart_opens_the_new_url` 會綠，因為現在的實作本來就會 `open` 新網址；另外四條紅，因為 `store.create()` 產生了新的 `session_id`，`app.store.get(first["session_id"])` 拿到 `None`。）

---

### Step 3：實作覆蓋（讓它綠）

把 `showme/app.py` 的 `start_tutorial` 整個換成：

```python
    async def start_tutorial(self, url: str, goal: str) -> dict:
        browser = await self._ensure_browser()
        session = self.store.current()
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
        if session is None:
            session = self.store.create(goal)
        else:
            session.goal = goal
            session.state = State.READY
            session.steps_shown = 0
            session.snapshot_no = 0
            session.pending = None
            session.latest_page = None
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
16 passed in 0.14s
```

**重點：**

- `session = self.store.current()` 放在 `open()` **之前**取一次就好；後面不要再 `current()` 一次。這樣「導航失敗 → `store.delete()`」之後，那個區域變數已經沒有人會用到了。
- `snapshot_no = 0` 而不是 `1`：因為 `_take_snapshot()` 自己會 `+= 1`。設成 1 的話 uid 會變成 `s2-*`，測試會抓到你。
- `latest_page = None`：舊頁的元素清單必須丟掉，否則 `show_step` 會允許 agent 用舊 uid（那正是規格要防的）。
- 沒有 `store.delete()` 再 `store.create()` 的寫法 —— 那會產生新的 `session_id`，違反「場次識別不變」。

---

### Step 4：覆蓋前要清掉舊 overlay（會先紅）

在 `tests/test_tool_start.py` 最後加上：

```python
# design §7.1 覆蓋時：關掉進行中的完成觀察、clear() overlay、再 goto 新 url
async def test_restart_clears_the_previous_overlay(started):
    app, fake, first = started

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert fake.calls.count(("clear",)) == 1
    assert fake.calls.index(("clear",)) < fake.calls.index(("open", NEW_PROJECT_URL))
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期紅燈：

```text
E       assert 0 == 1
E        +  where 0 = <built-in method count of list object>(('clear',))
...
1 failed, 16 passed in 0.14s
```

把 `showme/app.py` 的 `start_tutorial` 整個換成（只多了中間那個 `if session is not None:` 區塊）：

```python
    async def start_tutorial(self, url: str, goal: str) -> dict:
        browser = await self._ensure_browser()
        session = self.store.current()
        if session is not None:
            # 舊場次的箭頭還在畫面上，先擦掉再開新頁。這是善後動作，
            # 就算頁面已經跳走、overlay 不在了也不該擋住新的教學，所以吞掉例外。
            try:
                await browser.clear()
            except Exception:
                pass
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
        if session is None:
            session = self.store.create(goal)
        else:
            session.goal = goal
            session.state = State.READY
            session.steps_shown = 0
            session.snapshot_no = 0
            session.pending = None
            session.latest_page = None
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
17 passed in 0.15s
```

`except Exception: pass` 在這裡是**刻意**的，而且是**唯一**允許這樣寫的地方：`clear()` 是善後，失敗不影響新場次能不能開始。其他地方（例如 `open()`）絕對不可以這樣寫。

---

### Step 5：瀏覽器被關掉時要重新 launch

在 `tests/test_tool_start.py` 最後加上：

```python
# design §7.1：同一 Browser/Page 若仍活著則 goto 新 url；死掉則重 launch
async def test_restart_relaunches_a_dead_browser():
    made: list[FakeBrowser] = []

    def factory() -> FakeBrowser:
        browser = make_dashboard_browser()
        made.append(browser)
        return browser

    app = ShowMeApp(browser_factory=factory)
    first = await app.start_tutorial(DASHBOARD_URL, "create a project")
    assert len(made) == 1

    made[0].alive = False
    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert len(made) == 2
    assert made[1].launched is True
    assert ("open", NEW_PROJECT_URL) in made[1].calls
    assert second["error"] == ""
    assert second["session_id"] == first["session_id"]
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
18 passed in 0.15s
```

**這條不需要改實作就綠**，因為 A07 的 `_ensure_browser()` 已經寫了「沒有瀏覽器**或 `is_alive()` 是 False**就 factory() + launch()」。它是回歸測試：把 design §7.1 的「死掉則重 launch」釘在 `start_tutorial` 這一層，之後誰把 `_ensure_browser()` 改壞都會被抓到。

順帶注意 `made[1].calls` 裡有 `("clear",)`：新的瀏覽器上根本沒有舊 overlay，但我們還是照打一次。這沒有害處（`FakeBrowser` 只記錄；真的 overlay 是 `add_init_script` 注入的，`clear()` 在乾淨頁面上是 no-op），而且讓程式流程只有一條路，比較好讀。

---

### Step 6：導航失敗時，既有的 Session 會被刪掉

在 `tests/test_tool_start.py` 最後加上：

```python
# A 的設計決定（可改）：導航失敗不留下 Session（成功的 start 才有 Session）
async def test_restart_navigation_failure_deletes_the_session():
    browser = make_dashboard_browser(fail_urls={BAD_URL})
    app = ShowMeApp(browser_factory=lambda: browser)
    first = await app.start_tutorial(DASHBOARD_URL, "create a project")
    assert first["error"] == ""

    second = await app.start_tutorial(BAD_URL, "invite a member")

    assert second["error"] == "navigation_failed"
    assert second["session_id"] == ""
    assert second["page"] is None
    assert app.store.current() is None
    assert app.store.get(first["session_id"]) is None
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
19 passed in 0.16s
```

也不需要改實作（A08 就寫了 `self.store.delete()`），這條是把 **A-1 這個設計決定**釘在覆蓋路徑上。

**再說一次：這是 A 的設計決定，可改。** 規格（`開始教學_目標url無法開啟時是否操作失敗.md`）只說「操作失敗且錯誤為 `navigation_failed`」，沒說既有場次要不要留。我們選「刪掉」的理由：`start_tutorial` 已經 `clear()` 過、也已經離開原本那一頁了，留一個 `latest_page` 指向不存在畫面的場次只會讓 agent 用錯 uid。如果 demo 當天覺得「打錯字就整場沒了」太兇，可以改成「保留舊場次不動」——**但要連測試一起改，並在這份文件註記理由**。

---

### Step 7：覆蓋時把卡住的 `show_step` 叫醒（OQ2）

先寫測試。在 `tests/test_tool_start.py` 最後加上：

```python
# A 的設計決定（可改）：OQ2 —— 覆蓋時把還在等的 future 用 cancelled 解掉
async def test_restart_resolves_a_pending_future_with_cancelled(started):
    app, fake, first = started
    session = app.store.current()
    loop = asyncio.get_running_loop()
    pending = loop.create_future()
    session.pending = pending
    session.state = State.SHOWING

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert pending.done() is True
    assert pending.result() == {"kind": "cancelled", "url": "", "ts": 0}
    assert app.store.current().pending is None
    assert app.store.current().state is State.READY
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期紅燈：

```text
E       assert False is True
E        +  where False = <bound method Future.done of <Future pending>>()
...
1 failed, 19 passed in 0.16s
```

把 `showme/app.py` 的 `start_tutorial` 整個換成最終版（只在 `if session is not None:` 裡多了叫醒那三行）：

```python
    async def start_tutorial(self, url: str, goal: str) -> dict:
        browser = await self._ensure_browser()
        session = self.store.current()
        if session is not None:
            # OQ2（A 的設計決定，可改）：覆蓋時若有一次 show_step 正卡著等使用者，
            # 用 "cancelled" 把它的信箱解掉；那一次 show_step 會回 event="timeout"、page=None。
            pending = session.pending
            if session.state is State.SHOWING and pending is not None and not pending.done():
                pending.set_result({"kind": "cancelled", "url": "", "ts": 0})
            # 舊場次的箭頭還在畫面上，先擦掉再開新頁。這是善後動作，
            # 就算頁面已經跳走、overlay 不在了也不該擋住新的教學，所以吞掉例外。
            try:
                await browser.clear()
            except Exception:
                pass
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
        if session is None:
            session = self.store.create(goal)
        else:
            session.goal = goal
            session.state = State.READY
            session.steps_shown = 0
            session.snapshot_no = 0
            session.pending = None
            session.latest_page = None
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
20 passed in 0.17s
```

**為什麼要先問 `not pending.done()`？** 因為對一個已經有答案的 Future 再 `set_result()` 會丟 `asyncio.InvalidStateError`。「先問再放」這個順序，`_on_emit()`（A07）也是同一招——這就是規格「每步只取第一筆事件、同 ts 後至丟棄」的實作方式。

---

### Step 8：把 OQ2 的端到端測試寫好，先 skip

上面那條測試只證明「future 被解掉了」。**那次 `show_step` 到底回什麼**，要等 A12 把阻塞等待寫完才能驗。現在先把測試寫好、標上 skip，A12 的最後一步會把 skip 拿掉。

在 `tests/test_tool_start.py` 最後加上：

```python
# A 的設計決定（可改）：OQ2 —— 被覆蓋的那次 show_step 回 event="timeout"、page=None、error=""
@pytest.mark.skip(reason="A12 完成 show_step 阻塞等待後打開")
async def test_restart_ends_the_blocked_show_step_as_timeout(started):
    app, fake, first = started
    session_id = first["session_id"]

    task = asyncio.create_task(
        app.show_step(session_id, "s1-1", "Click New Project", "click", 1, 4)
    )
    for _ in range(100):
        if app.store.current().state is State.SHOWING:
            break
        await asyncio.sleep(0.01)
    assert app.store.current().state is State.SHOWING

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")
    step = await asyncio.wait_for(task, timeout=5)

    assert step["event"] == "timeout"
    assert step["page"] is None
    assert step["error"] == ""
    assert step["next_action"] == ""
    assert second["error"] == ""
    assert second["session_id"] == session_id
    assert app.store.current().state is State.READY
    assert app.store.current().steps_shown == 0
```

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：

```text
20 passed, 1 skipped in 0.17s
```

用 `-rs` 可以看到 skip 的理由：

```bash
uv run pytest tests/test_tool_start.py -q -rs
```

```text
SKIPPED [1] tests/test_tool_start.py:NNN: A12 完成 show_step 阻塞等待後打開
20 passed, 1 skipped in 0.17s
```

**寫給 A12 的交代**：`A12_show_step阻塞等待.md` 的最後一步，要把上面那行 `@pytest.mark.skip(...)` 刪掉，然後這條測試必須綠。那條 `for _ in range(100): ... await asyncio.sleep(0.01)` 是「等到 `show_step` 真的進入 SHOWING 為止，最多等 1 秒」的忙等寫法——`asyncio.create_task()` 只是把工作排進事件迴圈，不會立刻執行到阻塞點，所以要讓出控制權給它跑。

---

### Step 9：跑完整套件並 commit

```bash
uv run pytest -m "not browser" -q
```

預期最後一行類似：

```text
54 passed, 1 skipped in 0.62s
```

```bash
git add showme/app.py tests/test_tool_start.py
git commit -m "feat: start_tutorial overrides the running session"
```

預期輸出類似：

```text
[main 2b3c4d5] feat: start_tutorial overrides the running session
 2 files changed, 132 insertions(+), 3 deletions(-)
```

---

## 8. 驗收清單

- [ ] `uv run pytest tests/test_tool_start.py -q` 是 `20 passed, 1 skipped`。
- [ ] `uv run pytest -m "not browser" -q` 全綠（只有那一條 skip）。
- [ ] 覆蓋時 `session_id` 沒有變；程式裡**沒有**「先 delete 再 create」的寫法。
- [ ] 覆蓋時 `steps_shown` 歸零、`snapshot_no` 設成 0（拍完變 1）、`state` 回 `READY`、`pending` 與 `latest_page` 都清成 `None`。
- [ ] `("clear",)` 只在有既有 Session 時出現，而且排在 `("open", new_url)` 前面。
- [ ] 瀏覽器 `alive = False` 時，第二次 start 會叫 factory 產生新的並 `launch()`。
- [ ] 導航失敗時既有 Session 被刪掉，`store.current()` 是 `None`。
- [ ] `pending.set_result(...)` 前面有 `not pending.done()` 的檢查。
- [ ] 只有 `browser.clear()` 那一處用 `except Exception: pass`，而且旁邊有註解說明理由。
- [ ] 文件裡標為「A 的設計決定（可改）」的兩件事，在測試註解裡也標了：OQ2、導航失敗刪 Session。
- [ ] `inspect_page`、`show_step`、`end_tutorial` 還是佔位。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `assert 's_3c71' == 's_8f2a'` | 覆蓋時還是走 `store.create()` | 照 Step 3 的完整方法重貼；`if session is None:` 才 create |
| 覆蓋後 uid 是 `s2-*` | 覆寫時把 `snapshot_no` 設成 1 了 | 設成 `0`，`_take_snapshot()` 會加成 1 |
| `asyncio.InvalidStateError: invalid state` | 對已經有答案的 Future 再 `set_result()` | `set_result` 前一定要 `if ... and not pending.done():` |
| `test_restart_clears_the_previous_overlay` 失敗，`count(("clear",))` 是 2 | 你在沒有 Session 時也呼叫了 `clear()` | `clear()` 要放在 `if session is not None:` 裡面 |
| `test_restart_relaunches_a_dead_browser` 只有 1 個 browser | `_ensure_browser()` 沒有檢查 `is_alive()` | 回 A07 修 `_ensure_browser()` |
| 那條 skip 的測試被跑起來而且卡住 | skip 標記被刪了，但 `show_step` 還是佔位 | 現在還不該打開；把 `@pytest.mark.skip(...)` 加回去 |
| 覆蓋後 `show_step` 還能用舊的 `s4-*` uid | `latest_page` 沒有清成 `None` | 覆寫區塊要有 `session.latest_page = None` |
| 全套件跑很久才結束 | 那條 skip 的測試被打開，`show_step` 佔位不會阻塞但 `for` 迴圈等滿 1 秒 | 確認 skip 還在；`pyproject.toml` 的 `timeout = 60` 也會保護你 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/features/開始教學.feature` | Rule：同一時間只允許一個教學場次，再次開始教學時場次識別不變並覆蓋目標與網址（Example：進行中再開始另一個目標） | `test_restart_keeps_the_session_id_and_overwrites_the_goal`、`test_restart_opens_the_new_url`、`test_restart_resets_steps_shown`、`test_restart_leaves_the_session_ready` |
| 同上 | Rule：成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1（覆蓋時同樣從 1 起算） | `test_restart_restarts_snapshot_numbering` |
| 同上 | Rule：成功開始後 session 狀態為 READY | `test_restart_leaves_the_session_ready`（先把 state 設成 SHOWING 再覆蓋） |
| 同上 | Rule：啟動或重用 Chrome 並開啟傳入的 url（只有 `#TODO`） | `test_restart_relaunches_a_dead_browser`（測不變條件：活著就重用、死了就重開） |
| 同上 | Rule：目標 url 無法開啟時操作失敗且錯誤為 navigation_failed | `test_restart_navigation_failure_deletes_the_session`（覆蓋路徑上的同一條 Rule） |
| `docs/spec/.clarify/resolved/data/Session_既有進行中場次時再次start_tutorial要新建還是重用.md` | 答案 B：同一 process 只允許一個 Session；再次呼叫覆蓋 goal、重開 url、`session_id` 不變 | Step 3 的覆寫區塊 |
| `docs/spec/.clarify/resolved/data/Session_各狀態允許呼叫哪些MCP工具.md` | 答案 A：嚴格依狀態機，但 `start_tutorial` 仍可覆蓋（含 SHOWING） | `test_restart_leaves_the_session_ready`、`test_restart_resolves_a_pending_future_with_cancelled` |
| `docs/spec/.clarify/resolved/data/PageElement_uid的snapshot編號何時遞增.md` | 答案 A：start 從 1 起算（含覆蓋） | `test_restart_restarts_snapshot_numbering` |
| `docs/spec/erm.dbml` | `Session` Note：「再次呼叫 start_tutorial（Session 仍在）：覆蓋 goal、開啟傳入的 url、session_id 不變、steps_shown 歸零、state 為 READY」 | Step 3 的六行覆寫 |
| `docs/design/showme.md` §6 覆蓋段 | 場次還在時再 `start_tutorial` → 同 `session_id`、新 goal、重開 url、`steps_shown=0`、READY | 整篇 |
| `docs/design/showme.md` §7.1 覆蓋段 | 關掉進行中的完成觀察、`clear()` overlay、同一 Browser/Page 若仍活著則 goto 新 url；死掉則重 launch | Step 4、Step 5、Step 7 |
| `docs/design/showme.md` §17 open question 2 | 規格空隙；傾向（非決策）：取消等待，該次 `show_step` 回 `event=timeout` | Step 7 的 `cancelled`、Step 8 的 skip 測試；文件與測試都標「A 的設計決定（可改）」 |
| `docs/design/showme.md` §13 | 錯誤碼只有六個，不因為覆蓋而新增 | 被覆蓋的 `show_step` 用既有的 `event="timeout"`，`error` 保持 `""` |
