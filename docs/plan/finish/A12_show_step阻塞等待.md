# A12｜show_step 阻塞等待

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：[A11_show_step前置檢查.md](A11_show_step前置檢查.md)　｜　下一篇：[A13_end_tutorial.md](A13_end_tutorial.md)
> 對應設計：`docs/design/showme.md` §7.3、§8、§11、§13、§18（顯示步驟 30 條 Rule）｜ 對應切片：S7
> 預估時間：60–75 分鐘

---

## 1. 這一篇要做什麼

把 `show_step` 通過前置檢查之後的那段佔位 `{"error": "not_implemented"}` 換成真正的**「畫 → 卡住 → 醒來 → 回新 page」**。
這是整個 ShowMe 最核心、也是唯一一個「Python 會停下來等人類做事」的地方：我們用 `asyncio.Future` 當信箱、用 `asyncio.wait_for` 當鬧鐘，overlay 呼叫 `window.__showme_emit(...)` 時把答案投進信箱把我們叫醒。
本篇全部用 `FakeBrowser` 測，**不開任何瀏覽器**；真的瀏覽器留到 A15。

---

## 2. 做完會看到什麼

### 2.1 一次成功的 `show_step`（時序圖）

```text
 Qoder            ShowMe (show_step)         Browser/overlay          人
   |                     |                        |                    |
   |--show_step(uid)---->|                        |                    |
   |                     | 前置 6 檢查 (A11) OK   |                    |
   |                     | pending = Future()     |                    |
   |                     | state = SHOWING        |                    |
   |                     | steps_shown += 1       |                    |
   |                     |----show(opts)--------->|                    |
   |                     |                        |--畫箭頭+popover--->|
   |                     | started = loop.time()  |                    |
   |                     |                        |                    |
   |                (卡在 await wait_for)          |            人自己點 New Project
   |                     |                        |<--完成訊號---------|
   |                     |<--__showme_emit({kind:"step_done",...})     |
   |                     | _on_emit → set_result  |                    |
   |                 (醒來)                        |                    |
   |                     | elapsed = now - started|                    |
   |                     | pending = None         |                    |
   |                     | state = READY          |                    |
   |                     |----snapshot(2)-------->|                    |
   |<--{event:"step_done", elapsed_s, page(s2-*)} |                    |
   |                     |                        |                    |
```

### 2.2 Future 就是一個「信箱」

```text
      show_step 這一邊                        _on_emit 那一邊
   +--------------------------+            +-------------------------+
   |  pending = Future()      |            | 頁面呼叫 __showme_emit  |
   |                          |            |          |              |
   |  await wait_for(         |            |          v              |
   |      shield(pending),    |  <-------- |  pending.set_result(ev) |
   |      timeout=timeout_s)  |   投進信箱  |                         |
   |          |               |            +-------------------------+
   |    (整個 coroutine 停住)  |
   |          |               |            +-------------------------+
   |          v               |  <-------- |  鬧鐘響了（timeout_s 到）|
   |   TimeoutError → event=None|          |  信箱裡永遠沒有東西      |
   +--------------------------+            +-------------------------+

   信箱只收「第一封信」：set_result 之前先看 pending.done()，
   已經有信就整封丟掉（規格：每步恰好一次事件，同 ts 後至丟棄）。
```

### 2.3 這一篇碰到的狀態機

```text
                 show_step 前置檢查失敗（6 種 error）
                 ┌──────────────────────────────┐
                 │        (state 不變)           │
                 v                              │
   (無 Session) --start_tutorial--> READY ───────┘
                                     │
                                     │ 前置檢查全過 → show(opts)
                                     │ steps_shown += 1
                                     v
                                  SHOWING ──第二個 show_step──> show_step_in_progress
                                     │                          （第一個繼續等）
        ┌────────────────────────────┼──────────────────────────┐
        │ emit step_done             │ emit stuck               │ 等到 timeout_s
        v                            v                          v
   event="step_done"            event="stuck"              event="timeout"
   （不 clear）                  （不 clear）                await browser.clear()
        └────────────────────────────┴──────────────────────────┘
                                     │
                                     v  pending=None, state=READY, snapshot# +1
                                   READY  → 回傳附新鮮 page
```

---

## 3. 開始前先確認

A01–A11 都已完成並且測試全綠。逐項打勾：

- [ ] `uv run pytest -m "not browser"` 全綠（A01–A11 的測試都在）。
- [ ] `showme/session.py` 存在，含 `State`（`READY` / `SHOWING`）、`Session`（欄位 `session_id / goal / state / steps_shown / snapshot_no / latest_page / pending`）、`SessionStore`、常數 `MAX_STEPS = 12`、`DEFAULT_TIMEOUT_S = 120.0`、`STEP_NEXT_ACTION`。
- [ ] `showme/rules.py` 存在，含 `normalize_timeout_s`、`normalize_kind`、`expect_text_missing`、`build_page`、`uid_in_page`、`empty_page`。
- [ ] `showme/browser.py` 存在，含 `NavigationFailed`、`BrowserLike`、`PlaywrightBrowser`。
- [ ] `showme/app.py` 的 `ShowMeApp` 已經有 `_ensure_browser()`、`_on_emit()`、`_take_snapshot()`、`shutdown()`，而且 `start_tutorial`（A08/A09）與 `inspect_page`（A10）都已完成。
- [ ] `showme/app.py` 的 `show_step` 已經有 A11 的**前置 6 道檢查**；通過檢查之後目前是暫時回 `{"error": "not_implemented"}` 的佔位。
- [ ] `tests/fakes.py` 的 `FakeBrowser` 有 `emit(kind, url=None, ts=0)`、`navigate(url)`、`add_page(url, title, elements, truncated=False)`，並且會把每次呼叫記進 `self.calls`。
- [ ] `tests/conftest.py` 有 `anyio_backend`、`fake_browser`、`app`、`started` 四個 fixture。
- [ ] `tests/test_tool_start.py` 裡有一個標了 `@pytest.mark.skip(reason="A12 完成 show_step 阻塞等待後打開")` 的 OQ2 測試——**本篇最後一步就是把它打開**。
- [ ] `tests/test_fakes.py` 末尾 parametrize 的 `show_step` 那一行**已經在 A11 刪掉了**（A11 一實作前置檢查，`show_step` 就不再回裸的 `{"error": "not_implemented"}`），本篇不用再動這個檔。

用這兩行確認最後兩點：

```bash
cd /Users/linjunting/hackathonQoder
uv run pytest -m "not browser" -q
grep -n "A12" tests/test_tool_start.py
```

預期輸出（數字會依你前幾篇寫了幾個測試而不同）：

```text
115 passed, 1 skipped, 18 deselected in 0.10s

309:@pytest.mark.skip(reason="A12 完成 show_step 阻塞等待後打開")
```

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| coroutine（協程） | 用 `async def` 定義的函數。呼叫它不會馬上執行，要 `await` 或丟給 event loop 才會跑。 |
| event loop（事件迴圈） | asyncio 的「排班表」。同一時間只跑一段程式；遇到 `await` 就把控制權交回去，換別人跑。所以「阻塞」在 asyncio 裡不是把整個 process 凍住，只是**這一條 coroutine** 停在那裡等。 |
| `asyncio.Future` | 一個「之後才會有答案的信箱」。`await future` 的人會停住；別人呼叫 `future.set_result(x)` 把答案投進去，等的人就醒來拿到 `x`。 |
| `loop.create_future()` | 跟這個 event loop 綁在一起、建立一個空信箱。比直接 `asyncio.Future()` 安全，因為它一定用對 loop。 |
| `future.done()` | 信箱裡已經有答案（或已被取消）了嗎？`True` 代表**不可以再** `set_result`，否則丟 `InvalidStateError`。 |
| `asyncio.create_task(coro)` | 把一個 coroutine 丟去背景跑，馬上回傳一個 `Task` 握把。測試就是靠它「一邊讓 `show_step` 卡住、一邊做別的事」。 |
| `await asyncio.sleep(0)` | 「讓一下」。不真的睡，只是把控制權還給 event loop 一次，讓背景 task 有機會往前跑。測試裡連做幾次就能確保 `show_step` 已經跑到等待點。 |
| `asyncio.wait_for(aw, timeout)` | 幫 `await` 加一個鬧鐘。時間到還沒結果就丟 `TimeoutError`（Python 3.11 起 `asyncio.TimeoutError` 就是內建的 `TimeoutError`，寫哪個都一樣）。 |
| `asyncio.shield(aw)` | 「防彈衣」。`wait_for` 逾時時預設會**取消**它在等的東西；包一層 `shield` 之後被取消的是外面那層假殼，裡面真正的 `Future` **不會被取消**、仍然是「未完成」狀態。 |
| `loop.time()` | event loop 的**單調時鐘**（monotonic clock），單位秒的 float。它只會往前走，不會因為使用者調系統時間、或夏令時間而倒退。量「經過多久」一定用它，不要用 `time.time()`。 |
| `elapsed_s` | 這一步等了幾秒。規格例子是 `4.2`，所以我們 `round(elapsed, 1)`（A 的設計決定 A-4，可改）。 |
| emit | overlay 在頁面裡呼叫 `window.__showme_emit({kind, url, ts})`，Playwright 的 `expose_function` 把它轉成 Python 這邊 `_on_emit(event)` 的呼叫。 |
| `event` vs `error` | `event` ∈ `step_done` / `stuck` / `timeout`，是「這一步怎麼結束的」；`error` 是六個錯誤碼之一或空字串，是「這次呼叫有沒有失敗」。**timeout 不是錯誤**，它的 `error` 是 `""`。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 新增（測試） | `tests/test_tool_show_step_wait.py` | 本篇全部的行為測試：畫出、等待、三種 event、並發、只收第一筆 emit |
| 修改 | `showme/app.py` | 把 `show_step` 通過前置檢查後的佔位換成「畫 + 等 + 收尾」 |
| 修改（測試） | `tests/test_tool_start.py` | 把 A09 留下的 OQ2 測試的 `@pytest.mark.skip` 拿掉並跑綠 |

**不會動到：** `overlay/**`（那是 B 的）、`showme/server.py`、`showme/session.py`、`showme/rules.py`、`showme/browser.py`。

---

## 6. 介面約定

### 6.1 用到（來自前面幾篇，簽名不可改）

```python
# showme/session.py
MAX_STEPS = 12
DEFAULT_TIMEOUT_S = 120.0
STEP_NEXT_ACTION = (
    "If the goal is not yet achieved, call show_step for the next step using a uid "
    "from page.elements. If the page shows the goal is achieved, call end_tutorial."
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
```

```python
# showme/rules.py
def normalize_timeout_s(value: float | int | None) -> float: ...   # None/0/負 → 120.0
def normalize_kind(kind: str | None) -> str: ...                   # 不在四選一 → "observe"
def expect_text_missing(kind: str, expect_text: str | None) -> bool: ...
def uid_in_page(uid: str, page: dict | None) -> bool: ...
```

```python
# showme/browser.py（BrowserLike 這一篇只會用到這三個）
async def show(self, opts: dict) -> None: ...    # window.__showme.show(opts)
async def clear(self) -> None: ...               # window.__showme.clear()
async def snapshot(self, n: int) -> dict: ...    # window.__showme.snapshot(n)
```

```python
# showme/app.py（A07 已完成，本篇直接用）
async def _ensure_browser(self) -> BrowserLike: ...
async def _take_snapshot(self, session: Session) -> dict: ...
    # snapshot_no += 1 → browser.snapshot(n) → build_page(raw, url, title)
    # → session.latest_page = page → return page

def _on_emit(self, event: dict) -> None:
    """只有 current session 在 SHOWING 且 pending 未 done 時才 set_result(event)；
    其他一律忽略（= 每步只取第一筆 emit）。"""
```

`_on_emit` 的實作長這樣（A07 已寫好，本篇不改，只是要記得它的守門條件）：

```python
    def _on_emit(self, event: dict) -> None:
        session = self.store.current()
        if session is None or session.state is not State.SHOWING:
            return
        pending = session.pending
        if pending is None or pending.done():
            return
        pending.set_result(event)
```

### 6.2 提供（給後面幾篇）

```python
async def show_step(self, session_id: str, uid: str, instruction: str, kind: str,
                    step_index: int, step_total: int, expect_text: str = "",
                    timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, object]: ...
```

回傳形狀（六個鍵**永遠都在**）：

```python
# 成功（含 stuck / timeout）
{"event": "step_done" | "stuck" | "timeout", "signal": "", "elapsed_s": 4.2,
 "page": {...}, "next_action": STEP_NEXT_ACTION, "error": ""}

# 前置檢查失敗
{"event": "", "signal": "", "elapsed_s": 0.0,
 "page": <uid_not_in_snapshot 時是新鮮 page，其他 None>,
 "next_action": "", "error": <六個錯誤碼之一>}

# 被 start_tutorial 覆蓋取消（A 的設計決定 OQ2，可改）
{"event": "timeout", "signal": "", "elapsed_s": 1.3, "page": None,
 "next_action": "", "error": ""}
```

傳給 `browser.show()` 的 `opts`（鍵名鎖死，見 `docs/handoff.md`）：

```python
{"uid": uid, "instruction": instruction, "kind": kind,
 "index": step_index, "total": step_total, "expect": expect_text or ""}
```

> `show.expect` 就是 MCP 的 `expect_text`；`show.index` / `show.total` 就是 `step_index` / `step_total`。名字不一樣是接縫的既定事實，不要「順手統一」。

---

## 7. 步驟

節奏是 TDD：**先寫測試 → 跑一次看它紅 → 寫最小實作 → 跑一次看它綠 → commit**。

### Step 1：先寫測試檔（紅）

建立 `tests/test_tool_show_step_wait.py`，整份貼上：

```python
"""A12：show_step 畫出 overlay 之後的阻塞等待。

全部用 FakeBrowser，不開任何瀏覽器。
測試手法：用 asyncio.create_task 把 show_step 丟到背景跑，
再用 await asyncio.sleep(0) 讓 event loop 轉幾圈，
確保它已經跑到「等 emit」那一步，然後才模擬頁面 emit。
"""

from __future__ import annotations

import asyncio

import pytest

from showme.session import STEP_NEXT_ACTION, State

pytestmark = pytest.mark.anyio

DASHBOARD = "http://localhost:3000/"
NEW_PROJECT = "http://localhost:3000/projects/new"


async def _let_it_run(times: int = 5) -> None:
    """把控制權還給 event loop 幾次，讓背景 task 跑到『等 emit』那一步。"""
    for _ in range(times):
        await asyncio.sleep(0)


def _first_uid(page: dict) -> str:
    return page["elements"][0]["uid"]


def _show_calls(fake) -> list[dict]:
    return [call[1] for call in fake.calls if call[0] == "show"]


# --------------------------------------------------------------------------
# 畫出來的那一瞬間
# --------------------------------------------------------------------------

async def test_after_drawing_state_is_showing_and_steps_shown_increased(started):
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()

    session = app.store.current()
    assert session.state is State.SHOWING
    assert session.steps_shown == 1
    assert not task.done(), "show_step 應該還卡在等 emit，不該已經回傳"

    # 收尾：讓卡住的 task 結束，避免 pytest 抱怨有沒收掉的 task
    fake.emit("step_done")
    await task


async def test_show_is_called_with_the_locked_option_keys(started):
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()

    calls = _show_calls(fake)
    assert len(calls) == 1
    opts = calls[0]
    assert set(opts) == {"uid", "instruction", "kind", "index", "total", "expect"}
    assert opts["uid"] == uid
    assert opts["instruction"] == "Click New Project"
    assert opts["kind"] == "click"
    assert opts["index"] == 1
    assert opts["total"] == 4
    assert opts["expect"] == ""

    fake.emit("step_done")
    await task


# --------------------------------------------------------------------------
# 三種 event
# --------------------------------------------------------------------------

async def test_step_done_returns_fresh_page_and_goes_back_to_ready(started):
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()

    # 模擬人點了 New Project：頁面換到 /projects/new，然後 overlay emit
    fake.navigate(NEW_PROJECT)
    fake.emit("step_done")
    result = await task

    assert result["event"] == "step_done"
    assert result["error"] == ""
    assert result["signal"] == ""
    assert result["next_action"] == STEP_NEXT_ACTION
    assert isinstance(result["elapsed_s"], float)

    page = result["page"]
    assert page["url"] == NEW_PROJECT
    assert page["title"] == "New Project"
    assert page["elements"], "新頁應該有元素"
    assert all(el["uid"].startswith("s2-") for el in page["elements"])

    session = app.store.current()
    assert session.state is State.READY
    assert session.pending is None
    assert session.snapshot_no == 2


async def test_stuck_returns_event_stuck(started):
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()
    fake.emit("stuck")
    result = await task

    assert result["event"] == "stuck"
    assert result["error"] == ""
    assert app.store.current().state is State.READY


async def test_redraw_after_stuck_increments_steps_shown_again(started):
    """卡住之後對『同一個元素』再畫一次，steps_shown 仍然要 +1。

    注意：show_step 回傳時一定附一份新 snapshot，所以同一個元素的 uid
    字串從 s1-1 變成 s2-1。規格說的「同一 uid 重畫」指的是同一個元素，
    不是同一個字串——字串一定要從最新的 page.elements 重挑。
    """
    app, fake, start_result = started
    uid1 = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid1, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()
    fake.emit("stuck")
    first = await task
    assert app.store.current().steps_shown == 1

    uid2 = _first_uid(first["page"])
    assert uid2.startswith("s2-")

    task2 = asyncio.create_task(
        app.show_step(
            start_result["session_id"], uid2,
            "Click the big blue New Project button at the top right", "click", 1, 4,
        )
    )
    await _let_it_run()
    fake.emit("step_done")
    second = await task2

    assert second["event"] == "step_done"
    assert app.store.current().steps_shown == 2


async def test_stale_uid_from_the_previous_snapshot_is_rejected(started):
    """接上一個測試的陷阱：拿舊 snapshot 的 uid 字串重畫會被擋下來。"""
    app, fake, start_result = started
    uid1 = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid1, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()
    fake.emit("stuck")
    await task

    again = await app.show_step(
        start_result["session_id"], uid1, "Click New Project", "click", 1, 4
    )
    assert again["error"] == "uid_not_in_snapshot"
    assert again["event"] == ""
    assert app.store.current().steps_shown == 1, "被擋下來就不能加 steps_shown"


async def test_timeout_clears_the_overlay_and_still_returns_a_page(started):
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    result = await app.show_step(
        start_result["session_id"], uid, "Click New Project", "click", 1, 4,
        timeout_s=0.2,
    )

    assert result["event"] == "timeout"
    assert result["error"] == "", "timeout 是 event，不是 error"
    assert result["next_action"] == STEP_NEXT_ACTION
    assert result["elapsed_s"] >= 0.2
    assert ("clear",) in fake.calls, "timeout 之後要清掉 overlay（A 的設計決定 A-3）"

    session = app.store.current()
    assert session.state is State.READY
    assert session.pending is None
    assert session.snapshot_no == 2
    assert result["page"] is not None
    assert all(el["uid"].startswith("s2-") for el in result["page"]["elements"])


async def test_emit_that_arrives_after_the_deadline_is_still_timeout(started):
    """規格：elapsed_s >= timeout_s 即 timeout（含剛好相等；同一瞬間有完成訊號仍算 timeout）。

    這裡故意睡得比 timeout_s 久，再 emit；因為鬧鐘早就響了，結果必須是 timeout。
    也順便證明 shield 有效：晚到的 set_result 不會把程式炸掉。
    """
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4,
                      timeout_s=0.2)
    )
    await asyncio.sleep(0.3)
    fake.emit("step_done")
    result = await task

    assert result["event"] == "timeout"
    assert result["error"] == ""


async def test_event_is_always_one_of_the_three_allowed_values(started):
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()
    fake.emit("stuck")
    result = await task

    assert result["event"] in {"step_done", "stuck", "timeout"}


# --------------------------------------------------------------------------
# 每步只收第一筆 emit
# --------------------------------------------------------------------------

async def test_only_the_first_emit_counts(started):
    """規格：每步恰好一次事件；同一 session 同一 ts 後至的事件丟棄。"""
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()

    fake.emit("step_done", ts=1756400000)
    fake.emit("stuck", ts=1756400000)      # 同一個 ts 的第二筆，必須被丟掉
    result = await task

    assert result["event"] == "step_done"


# --------------------------------------------------------------------------
# 並發
# --------------------------------------------------------------------------

async def test_second_show_step_while_showing_is_rejected(started):
    app, fake, start_result = started
    uid = _first_uid(start_result["page"])

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()

    second = await app.show_step(
        start_result["session_id"], uid, "Click New Project again", "click", 2, 4
    )
    assert second["error"] == "show_step_in_progress"
    assert second["event"] == ""
    assert second["page"] is None

    # 第一個仍在等，而且沒被第二個影響
    assert not task.done()
    assert app.store.current().state is State.SHOWING
    assert app.store.current().steps_shown == 1
    assert len(_show_calls(fake)) == 1, "被拒絕的那次不可以畫"

    fake.emit("step_done")
    first = await task
    assert first["event"] == "step_done"
```

跑一次看它紅：

```bash
cd /Users/linjunting/hackathonQoder
uv run pytest tests/test_tool_show_step_wait.py -q
```

預期會看到一整排 `F`，訊息大致像這樣（依 A11 佔位的寫法會是 `KeyError` 或 `AssertionError` 其中一種）：

```text
FFFFFFFFFFF                                                         [100%]
=================================== FAILURES ===================================
____ test_after_drawing_state_is_showing_and_steps_shown_increased _____
>       assert session.state is State.SHOWING
E       AssertionError: assert <State.READY: 'READY'> is <State.SHOWING: 'SHOWING'>
...
____________ test_step_done_returns_fresh_page_and_goes_back_to_ready __________
>       assert result["event"] == "step_done"
E       KeyError: 'event'
11 failed in 0.41s
```

**紅得對**：現在 `show_step` 通過前置檢查後直接回佔位，既沒把 state 改成 SHOWING，也沒有 `event` 這個鍵。

### Step 2：把佔位換成「畫 + 等」

打開 `showme/app.py`，把整個 `show_step` 方法換成下面這一份（**前置 6 檢查照抄 A11 的，後面是新的**）：

```python
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
        """對一個 uid 畫 overlay，然後阻塞等到 overlay emit 或 timeout_s 到期。

        回傳永遠有六個鍵：event / signal / elapsed_s / page / next_action / error。
        失敗寫在 error，不丟例外（MCP 呼叫本身仍算成功）。
        """
        # ---------- 前置檢查（A11；每一項都不畫、不加 steps_shown） ----------
        session = self.store.get(session_id)
        if session is None:
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "session_not_found"}

        if session.state is State.SHOWING:
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "show_step_in_progress"}

        if session.steps_shown >= MAX_STEPS:
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "max_steps_exceeded"}

        kind = normalize_kind(kind)
        if expect_text_missing(kind, expect_text):
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "expect_text_required"}

        if not uid_in_page(uid, session.latest_page):
            stale_page = await self._take_snapshot(session)
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": stale_page,
                    "next_action": "", "error": "uid_not_in_snapshot"}

        timeout_s = normalize_timeout_s(timeout_s)

        # ---------- 畫（A12） ----------
        browser = await self._ensure_browser()
        loop = asyncio.get_running_loop()
        session.pending = loop.create_future()
        session.state = State.SHOWING
        session.steps_shown += 1
        await browser.show({
            "uid": uid,
            "instruction": instruction,
            "kind": kind,
            "index": step_index,
            "total": step_total,
            "expect": expect_text or "",
        })

        # ---------- 等（A12） ----------
        started = loop.time()
        try:
            event = await asyncio.wait_for(asyncio.shield(session.pending), timeout=timeout_s)
        except asyncio.TimeoutError:
            event = None
        elapsed = loop.time() - started

        # 被 start_tutorial 覆蓋掉了（A 的設計決定 OQ2，可改）：
        # 這一次不再碰瀏覽器、也不再碰 Session，因為 start_tutorial 已經接手重設了。
        if event is not None and event.get("kind") == "cancelled":
            return {"event": "timeout", "signal": "", "elapsed_s": round(elapsed, 1),
                    "page": None, "next_action": "", "error": ""}

        if event is None or elapsed >= timeout_s:
            result_event = "timeout"
            await browser.clear()          # A 的設計決定 A-3：只有 timeout 才主動清
        else:
            result_event = event["kind"]   # "step_done" 或 "stuck"

        # ---------- 收尾（A12） ----------
        session.pending = None
        session.state = State.READY
        page = await self._take_snapshot(session)
        return {"event": result_event, "signal": "", "elapsed_s": round(elapsed, 1),
                "page": page, "next_action": STEP_NEXT_ACTION, "error": ""}
```

確認 `showme/app.py` 檔案最上面的 import 至少有這些（A07–A11 應該都已經加過了，缺哪個補哪個）：

```python
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
```

> 如果你在 A11 寫了自己的小 helper（例如 `_step_error("session_not_found")`）來組失敗形狀，保留它沒問題。重點只有一個：回傳的**六個鍵與值**要跟上面完全一樣。

### Step 3：跑綠（本篇的測試綠了，但全套會有 4 條紅——那是預期中的）

```bash
uv run pytest tests/test_tool_show_step_wait.py -q
```

預期輸出：

```text
...........                                                         [100%]
11 passed in 0.53s
```

（會花將近 1 秒是因為兩個 timeout 測試真的等了 0.2 / 0.3 秒。）

接著跑全部不開瀏覽器的測試：

```bash
uv run pytest -m "not browser" -q
```

**這一次不會全綠。** 預期會有 **4 failed**，而且四條全部在 `tests/test_tool_show_step_checks.py`（A11 寫的）：

```text
.....F..F.F.......F...........................s...........          [100%]
=================================== FAILURES ===================================
________________ test_show_step_with_eleven_steps_passes_the_pre_checks ________
>       assert result["error"] == "not_implemented"   # 六關都過了（A12 會換成真的等待）
E       AssertionError: assert '' == 'not_implemented'
...
4 failed, 123 passed in 1.5s
```

**紅得對。** A11 那四條測試斷言的是「六道檢查全過之後回 `not_implemented` 佔位」——那個佔位剛剛被 Step 2 換掉了，現在會真的畫、真的等 0.2 秒、然後回 `event="timeout"`、`error=""`。A11 文件末尾的「給 A12 的交代」就是在交代這件事，**Step 5 會把這四條改好**。

同時確認**另外 11 條**前置檢查的測試（六道檢查的失敗路徑）原封不動繼續綠——它們是 A12 不可以弄壞的護欄：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期：

```text
.....F..F.F.......F                                                 [100%]
4 failed, 11 passed in 0.89s
```

如果紅的不只那四條、或紅的名字不在下面 Step 5 的清單裡，代表 Step 2 把前置檢查改壞了——回去比對一次那六道檢查。

### Step 4：逐行讀一次「等」那段（沒有程式碼要改，但一定要看懂）

```python
started = loop.time()
```
`loop.time()` 是**單調時鐘**：只會往前走，量「經過多久」用它才不會被系統時間調整影響。不要用 `time.time()`。

```python
event = await asyncio.wait_for(asyncio.shield(session.pending), timeout=timeout_s)
```
三件事疊在一起：

1. `session.pending` 是空信箱。`await` 它會讓這條 coroutine 停住。
2. `asyncio.shield(...)` 在信箱外面套一層假殼。
3. `asyncio.wait_for(..., timeout=...)` 加鬧鐘；時間到就**取消它正在等的東西**再丟 `TimeoutError`。

**為什麼一定要 `shield`？** 因為 `wait_for` 逾時時取消的是「它在等的那個東西」。沒有 shield 的話被取消的就是 `session.pending` 本人，它會進入 cancelled 狀態；之後人終於做完動作、overlay emit 進來，`_on_emit` 想 `pending.set_result(...)` 就會丟 `InvalidStateError: invalid state`，把 Playwright 的 callback 炸掉，終端機噴一堆紅字。有了 shield，被取消的是外面那層假殼，`session.pending` 仍是「未完成」，晚到的 `set_result` 安安靜靜地成功，然後隨著 `session.pending = None` 被丟掉。

```text
  沒有 shield：                            有 shield：
  wait_for --取消--> session.pending       wait_for --取消--> shield 假殼
                     (CANCELLED)                              (CANCELLED)
                          ^                                        |
             稍後 set_result → 💥 InvalidStateError                 | 裡面的
                                                    session.pending (PENDING) 沒事
                                          稍後 set_result → 靜靜成功，沒人來拿
```

（`_on_emit` 裡的 `pending.done()` 檢查是第二道保險：它同時擋住「同一步的第二筆 emit」。兩道防線都要留著。）

```python
if event is None or elapsed >= timeout_s:
```
`event is None` 是鬧鐘先響。`elapsed >= timeout_s` 是規格明寫的邊界：**「經過時間大於等於 timeout_s 就是 timeout，含剛好相等；同一瞬間有完成訊號仍算 timeout」**（`docs/spec/.clarify/resolved/features/顯示步驟_等待時間剛好等於timeout_s時算timeout還是完成.md`，答案 A）。第二個條件在實務上幾乎不會單獨成立，但它把規則寫進程式裡，之後誰改都不會改壞。

```python
await browser.clear()
```
只有 timeout 才清。`step_done` / `stuck` 之後**不**清：overlay 自己會處理，而且下一次 `show()` 本來就會先 clear（見 `docs/design/showme.md` §12）。這是 A 的設計決定 A-3（可改），來源是設計 §11：「timeout……然後 `clear()` 觀察器、拍 page、state=READY」。

### Step 5：更新 A11 留下的 4 條佔位斷言

打開 `tests/test_tool_show_step_checks.py`（A11 建立的），把下面四條測試**整段換成**這裡的版本。四條的共同點：它們斷言的都是「六道前置檢查全部通過」，只是判斷方式從「回 `not_implemented` 佔位」改成「回 `event="timeout"`、`error=""`」。四條都已經帶了 `timeout_s=0.2`，所以每條只會等 0.2 秒。

檔案上方原有的 import 與常數不要動，本步驟會用到的是這些（A11 已經寫好）：

```python
import pytest

from showme.session import MAX_STEPS, State

pytestmark = pytest.mark.anyio

NEW_PROJECT_URL = "http://localhost:3000/projects/new"
```

> 順帶一提本專案的匯入慣例：`tests/` 底下**沒有** `__init__.py`，pytest 會把 `tests/` 放進 `sys.path`，所以測試檔要用 `FakeBrowser` 時一律寫 `from fakes import FakeBrowser`（不是 `from tests.fakes import ...`）。本篇的測試都靠 fixture 拿到 `FakeBrowser`，所以不需要這行 import。

**第 1 條**——改完後長這樣：

```python
async def test_show_step_with_eleven_steps_passes_the_pre_checks(started):
    app, fake, first = started
    session = app.store.current()
    session.steps_shown = MAX_STEPS - 1

    result = await app.show_step(
        first["session_id"], "s1-1", "Click New Project", "click", 1, 4, timeout_s=0.2
    )

    # 六關都過了：真的畫出來、等 0.2 秒沒人 emit → timeout（A12 之後的行為）
    assert result["error"] == ""
    assert result["event"] == "timeout"
    assert app.store.current().steps_shown == MAX_STEPS   # 11 + 1 = 12
```

**第 2 條**：

```python
async def test_observe_with_expect_text_passes_the_pre_checks(started):
    app, fake, first = started

    result = await app.show_step(
        first["session_id"], "s1-1", "Wait for the heading", "observe", 1, 4,
        expect_text="New Project", timeout_s=0.2,
    )

    # 六關都過了
    assert result["error"] == ""
    assert result["event"] == "timeout"
```

**第 3 條**：

```python
async def test_click_without_expect_text_passes_the_pre_checks(started):
    app, fake, first = started

    result = await app.show_step(
        first["session_id"], "s1-1", "Click New Project", "click", 1, 4,
        expect_text="", timeout_s=0.2,
    )

    # 六關都過了（click 不需要 expect_text）
    assert result["error"] == ""
    assert result["event"] == "timeout"
```

**第 4 條**：

```python
async def test_uid_failure_lets_the_next_call_use_a_fresh_uid(started):
    app, fake, first = started
    fake.navigate(NEW_PROJECT_URL)

    # s1-3 不在 Dashboard 那份清單裡（那份只有 s1-1、s1-2），所以第五關會擋下來
    failed = await app.show_step(first["session_id"], "s1-3", "Type a project name", "input", 2, 4)
    fresh_uid = failed["page"]["elements"][1]["uid"]

    retried = await app.show_step(
        first["session_id"], fresh_uid, "Type a project name", "input", 2, 4, timeout_s=0.2
    )

    assert failed["error"] == "uid_not_in_snapshot"
    assert fresh_uid == "s2-2"
    # 用新鮮 uid 重試就過得了第五關；六關都過 → 等 0.2 秒 → timeout
    assert retried["error"] == ""
    assert retried["event"] == "timeout"
```

改完跑一次：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期輸出（四條各等 0.2 秒，所以會花 1 秒多）：

```text
...............                                                     [100%]
15 passed in 0.87s
```

> **為什麼結果是 `timeout` 而不是 `step_done`？** 因為這四條測試只是要證明「六道檢查沒有把它擋下來」，它們**沒有**去 emit 任何事件。既然沒人 emit，等 0.2 秒之後 Python 這邊的計時器就到期，回 `event="timeout"`、`error=""`。「畫出來之後真的等到 emit」的行為由本篇的 `tests/test_tool_show_step_wait.py` 負責驗。

---

### Step 6：打開 A09 留下的 OQ2 測試

`start_tutorial` 在覆蓋一個正在 SHOWING 的場次時，會把 pending 用 `{"kind": "cancelled", "url": "", "ts": 0}` 解掉（A09 已實作）。現在 `show_step` 認得這個訊號了，那個測試可以打開了。

打開 `tests/test_tool_start.py`，找到標了 skip 的那個測試，**刪掉 `@pytest.mark.skip(...)` 那一行**，並確認測試主體是這樣：

```python
async def test_start_tutorial_cancels_a_waiting_show_step(app, fake_browser):
    """OQ2（A 的設計決定，可改）：SHOWING 時 start_tutorial 覆蓋，
    卡住的那次 show_step 回 event="timeout"、page=None、error=""。"""
    started = await app.start_tutorial(DASHBOARD, "create a project")
    uid = started["page"]["elements"][0]["uid"]

    task = asyncio.create_task(
        app.show_step(started["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    for _ in range(5):
        await asyncio.sleep(0)
    assert app.store.current().state is State.SHOWING

    await app.start_tutorial(DASHBOARD, "invite a member")

    result = await task
    assert result["event"] == "timeout"
    assert result["page"] is None
    assert result["error"] == ""

    # 覆蓋之後是一個乾淨的 READY 場次
    session = app.store.current()
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 1
```

（檔案上方要有 `import asyncio` 與 `from showme.session import State`；A09 寫這個測試時應該已經加了，沒有就補上。如果你 A09 的測試主體寫法跟這裡略有不同也沒關係，只要那三條斷言在就好。）

跑：

```bash
uv run pytest tests/test_tool_start.py -q
```

預期：全綠、**0 skipped**。

```text
.....................                                               [100%]
21 passed in 0.08s
```

### Step 7：全部再跑一次，然後 commit

```bash
uv run pytest -m "not browser" -q
```

預期：全綠、**0 failed、0 skipped**。

```text
.......................................................             [100%]
127 passed in 1.5s
```

（測試總數會依你前幾篇寫了幾個而不同；重點是 `failed` 與 `skipped` 都是 0。）

```bash
git add showme/app.py tests/test_tool_show_step_wait.py \
        tests/test_tool_show_step_checks.py tests/test_tool_start.py
git commit -m "feat: block show_step until overlay emits or timeout_s elapses"
```

---

## 8. 驗收清單

- [ ] `uv run pytest tests/test_tool_show_step_wait.py -q` → 11 passed。
- [ ] `uv run pytest tests/test_tool_show_step_checks.py -q` → **15 passed**（A11 的 4 條佔位斷言已在 Step 5 換成 `error == ""` + `event == "timeout"`；另外 11 條原封不動繼續綠）。
- [ ] `uv run pytest -m "not browser" -q` → 全綠，**0 failed、0 skipped**（A09 的 OQ2 測試已在 Step 6 打開）。
- [ ] 畫出後：`session.state is State.SHOWING`、`session.steps_shown` 加 1、`fake.calls` 出現 `("show", opts)`，且 `opts` 的鍵恰好是 `uid / instruction / kind / index / total / expect`。
- [ ] `emit("step_done")` → `event == "step_done"`、`page.url` 是新頁、`page.elements[].uid` 是 `s2-*`、`state` 回到 `READY`、`elapsed_s` 是 float、`next_action == STEP_NEXT_ACTION`、`error == ""`。
- [ ] `emit("stuck")` → `event == "stuck"`。
- [ ] stuck 之後對同一個元素（用新 snapshot 的 uid）再畫 → `steps_shown` 再 +1。
- [ ] 舊 snapshot 的 uid 字串再用 → `uid_not_in_snapshot`，`steps_shown` 不變。
- [ ] `timeout_s=0.2` 且不 emit → `event == "timeout"`、`("clear",)` 出現在 `fake.calls`、`state` 回 `READY`、仍附一份 page 且 `snapshot_no` 加 1。
- [ ] `timeout_s=0.2` → `sleep(0.3)` → 才 emit → 仍然是 `timeout`，而且**沒有任何例外或警告**（證明 `shield` 有效）。
- [ ] 同一步 emit 兩次（step_done 再 stuck）→ 結果是 `step_done`。
- [ ] SHOWING 時第二個 `show_step` → `show_step_in_progress`，第一個仍在等、`show` 只被呼叫過一次；之後 emit，第一個才回。
- [ ] `event` 只可能是 `step_done` / `stuck` / `timeout` 三者之一。
- [ ] `timeout` 的 `error` 是 `""`（timeout 是 event，不是錯誤碼）。
- [ ] 沒有動到 `overlay/**`、`showme/server.py`、`showme/session.py`、`showme/rules.py`、`showme/browser.py`。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| 測試整個掛住不動，最後被 pytest-timeout 砍掉（60 秒） | 用 `await app.show_step(...)` 直接呼叫，沒有 `create_task`，於是測試自己也卡在等 emit，永遠沒人來 emit | 除了「就是要測 timeout」的那兩個測試以外，一律 `task = asyncio.create_task(app.show_step(...))`，讓出控制權後才 `fake.emit(...)`，最後 `await task` |
| `assert not task.done()` 失敗 | `_let_it_run()` 讓的次數太多、或 `show_step` 根本沒有真的等（例如 `timeout_s` 被誤傳成 0 又沒正規化） | 確認 `normalize_timeout_s(0)` 回 `120.0`，而且 `show_step` 有呼叫它 |
| `InvalidStateError: invalid state` | `asyncio.shield` 忘了包，逾時時 `session.pending` 被取消，晚到的 `set_result` 就炸 | 補回 `asyncio.shield(session.pending)`；同時確認 `_on_emit` 有 `if pending is None or pending.done(): return` |
| `RuntimeError: Task got Future attached to a different loop` | 用 `asyncio.Future()` 自己 new，沒綁到目前的 loop | 一律用 `loop = asyncio.get_running_loop()` 之後 `loop.create_future()` |
| `KeyError: 'kind'` | emit 進來的 dict 沒有 `kind` 鍵 | 這在 FakeBrowser 不會發生；真瀏覽器要靠 B 遵守接縫 `{kind, url, ts}`。A 側不做防禦式改寫，接縫錯就是接縫錯，讓它紅出來 |
| `event` 是 `"cancelled"` | 直接把 emit 的 `kind` 當結果回傳，忘了先攔 `cancelled` | `if event is not None and event.get("kind") == "cancelled":` 這段一定要在 `result_event = event["kind"]` **之前** |
| timeout 測試的 `elapsed_s` 是 `0.2` 但斷言寫 `== 0.2` 失敗 | 浮點數 + `round(x, 1)`，實際會是 `0.2` 或 `0.3` | 用 `>=` 比較，不要比相等 |
| `("clear",)` 在 step_done 之後也出現了 | 把 `browser.clear()` 寫在 if/else 外面 | `clear()` 只放在 timeout 那一支 |
| `tests/test_tool_show_step_checks.py` 有 4 條紅在 `assert '' == 'not_implemented'` | Step 5 還沒做：A11 那四條斷言的是被換掉的佔位字串 | 照 Step 5 把那四條整段換成新版本（`error == ""` + `event == "timeout"`）。名字是 `..._with_eleven_steps_passes_the_pre_checks`、`test_observe_with_expect_text_passes_the_pre_checks`、`test_click_without_expect_text_passes_the_pre_checks`、`test_uid_failure_lets_the_next_call_use_a_fresh_uid` |
| `tests/test_tool_show_step_checks.py` 紅的**不只**那 4 條 | Step 2 把 A11 的六道前置檢查改壞了 | 逐條比對 Step 2 那份完整方法的前置檢查段；六個失敗回傳的鍵與值都不能動 |
| `ModuleNotFoundError: No module named 'tests'` | 在測試檔裡寫了 `from tests.fakes import FakeBrowser` | 本專案 `tests/` 沒有 `__init__.py`，pytest 會把 `tests/` 放進 `sys.path`，所以一律寫 `from fakes import FakeBrowser` |
| 全部測試都紅在 `fixture 'started' not found` | conftest 的 `started` fixture 沒建立或 import 出錯 | `uv run pytest --fixtures tests/test_tool_show_step_wait.py \| grep started` 確認；A07 應已建立 |
| `PytestUnhandledCoroutineWarning` 或測試被 skip | 檔案上面漏了 `pytestmark = pytest.mark.anyio`，或 conftest 沒有 `anyio_backend` fixture | 兩個都補上；`anyio_backend` 回 `"asyncio"` |
| 終端機出現 `Task was destroyed but it is pending!` | 有測試建了 task 卻沒 `await` 它就結束 | 每個 `create_task` 最後都要有對應的 `fake.emit(...)` + `await task` |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `features/顯示步驟.feature` | Rule：畫出 overlay 後阻塞直到使用者做完或逾時 | `await asyncio.wait_for(asyncio.shield(session.pending), timeout=timeout_s)`；`test_after_drawing_state_is_showing_and_steps_shown_increased` 斷言 `not task.done()` |
| `features/顯示步驟.feature` | Rule：畫出後 session 狀態為 SHOWING 直到事件 | `session.state = State.SHOWING`；同上測試 |
| `features/顯示步驟.feature` | Rule：收到事件後 session 狀態為 READY 並回傳新 page（Example 檢查 `page.url` = `/projects/new`、`page.title` = `New Project`、`state` = READY） | `test_step_done_returns_fresh_page_and_goes_back_to_ready` |
| `features/顯示步驟.feature` | Rule：uid 通過驗證並畫出後 steps_shown 加 1，含 I'm stuck 後對同一 uid 再畫 | `session.steps_shown += 1` 在 `show()` 之前；`test_redraw_after_stuck_increments_steps_shown_again` |
| `features/顯示步驟.feature` | Rule：完成判定只看 event，signal 可為空且不列入驗收 | 回傳固定 `"signal": ""`；測試只斷言 `event` |
| `features/顯示步驟.feature` | Rule：elapsed_s 大於等於 timeout_s 時 event 為 timeout 且狀態為 READY（含「完成訊號與截止同一瞬間仍為 timeout」） | `if event is None or elapsed >= timeout_s:`；`test_timeout_clears_the_overlay_and_still_returns_a_page`、`test_emit_that_arrives_after_the_deadline_is_still_timeout` |
| `features/顯示步驟.feature` | Rule：每步恰好回傳一次事件；同一 session 同一 ts 後至的事件丟棄（Example：同 ts 第二筆不取代第一筆） | `_on_emit` 的 `pending.done()` 守門；`test_only_the_first_emit_counts` |
| `overlay/overlay.js`（B 已進 repo） | 真 overlay 的 emit payload 是 `{kind, url, ts, signal}`，比接縫多一個 `signal` 鍵 | `_on_emit` 與 `show_step` 都只讀 `kind`，多出來的鍵直接忽略；回傳的 `signal` 一律是 `""` |
| `features/顯示步驟.feature` | Rule：同一 session 並發的 show_step 被拒絕且錯誤為 show_step_in_progress | 前置檢查 2；`test_second_show_step_while_showing_is_rejected` |
| `features/顯示步驟.feature` | Rule：任何 kind 使用者按 I'm stuck 時 event 為 stuck | `result_event = event["kind"]`；`test_stuck_returns_event_stuck` |
| `features/顯示步驟.feature` | Rule：操作失敗時寫在回傳的 error，不丟例外 | 全部路徑 `return dict`，沒有 `raise` |
| `.clarify/resolved/features/顯示步驟_等待時間剛好等於timeout_s時算timeout還是完成.md` | 答案 A：`elapsed_s >= timeout_s` 即 timeout（含剛好相等；同一瞬間完成訊號仍算 timeout） | `elapsed >= timeout_s` 條件；`test_emit_that_arrives_after_the_deadline_is_still_timeout` |
| `.clarify/resolved/features/顯示步驟_使用者按Im_stuck後重畫同uid是否增加steps_shown.md` | 答案 A：每次成功畫出都 +1，含 stuck 後重畫 | `test_redraw_after_stuck_increments_steps_shown_again` |
| `.clarify/resolved/features/顯示步驟_並發show_step失敗時的錯誤碼為何.md` | 答案 A：`show_step_in_progress` | `test_second_show_step_while_showing_is_rejected` |
| `.clarify/resolved/data/Event_同一session同一ts出現兩筆事件時如何識別.md` | 答案 A：同 ts 後至丟棄 | `_on_emit` 的 `pending.done()`；`test_only_the_first_emit_counts` |
| `.clarify/resolved/data/Event_signal的完整允許值有哪些.md` | 答案 C：signal 可為空，完成只看 event | 固定回 `""` |
| `.clarify/resolved/data/Event_overlay的kind與StepResult的event是否使用同一組值.md` | overlay 只發 `step_done` / `stuck`；`timeout` 只存在 `StepResult.event` | timeout 由 Python 的 `wait_for` 決定，不要求 overlay 發 |
| `docs/spec/erm.dbml` | `Session.state`、`steps_shown`、`StepResult.event/signal/elapsed_s/next_action/error` | 回傳六鍵形狀；`session.pending` 對應 Note 裡的「進行中 wait Future」 |
| `docs/design/showme.md` §7.3 | 成功畫出 → steps_shown+1 → SHOWING → 阻塞；完成回傳附新 page（snapshot# +1）、state=READY | 收尾三行 + `_take_snapshot` |
| `docs/design/showme.md` §11 | timeout：Python 在 `elapsed_s >= timeout_s` 結束等待，不等 overlay emit；然後 `clear()`、拍 page、state=READY | timeout 分支 |
| `docs/design/showme.md` §13 | `timeout`/`stuck`/`step_done` 是 `event`，不是錯誤碼 | timeout 回傳 `error: ""` |
| `docs/design/showme.md` §17 open Q2 | SHOWING 時被 `start_tutorial` 覆蓋，卡住的 `show_step` 如何收尾 | **A 的設計決定（可改）**：認 `{"kind": "cancelled"}` → 回 `event="timeout"`、`page=None`、`error=""`；A09 的 OQ2 測試在本篇打開 |
| `docs/handoff.md` 鎖死的名字 | `show({uid, instruction, kind, index, total, expect})`、emit 的 `kind` 只有 `step_done`/`stuck`、B 不發 timeout | `test_show_is_called_with_the_locked_option_keys` 用 `set(opts) ==` 鎖死鍵名 |
