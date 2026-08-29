# A13｜end_tutorial

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：[A12_show_step阻塞等待.md](A12_show_step阻塞等待.md)　｜　下一篇：[A14_MCP契約測試與stdio.md](A14_MCP契約測試與stdio.md)
> 對應設計：`docs/design/showme.md` §7.4、§8、§13、§18（結束教學 6 條 Rule）｜ 對應切片：S8
> 預估時間：30–40 分鐘

---

## 1. 這一篇要做什麼

實作第四個、也是最後一個 tool：`end_tutorial`。
它做三件事——**清掉 overlay、貼上固定的完成 banner、把 Session 刪掉**——然後回 `{"ok": True, "error": ""}`。
`summary` 參數收下來但**完全不用**（規格明訂 banner 文案固定）。瀏覽器**不關**，因為人要留在畫面上看到那句 ✅。

做完這一篇，四個 tool 的邏輯就全部寫完了。

---

## 2. 做完會看到什麼

### 2.1 `end_tutorial` 的流程

```text
  end_tutorial(session_id, summary)
            │
            ├─ store.get(session_id) 是 None ? ──yes──> {"ok": False, "error": "session_not_found"}
            │        （沒有 Session、或 id 對不上）
            no
            │
            ├─ state 是 SHOWING ?           ──yes──> {"ok": False, "error": "show_step_in_progress"}
            │   （A 的設計決定 OQ1，可改）             （正在等人做事，不准收攤）
            no
            │
            ├─ await browser.clear()                拿掉箭頭與 popover
            ├─ await browser.done(DONE_BANNER_TEXT) 貼上 "✅ Done — you created a project"
            │                                       ↑ summary 在這裡被完全忽略
            ├─ store.delete()                       Session 消失（沒有 DONE 狀態）
            │
            └─> {"ok": True, "error": ""}

  ※ 沒有 browser.close()。瀏覽器留著（A 的設計決定 A-2，可改）。
```

### 2.2 Session 的一生（本篇把最後一段補上）

```text
   (無 Session)
        │  start_tutorial 成功                       ┌──────────────┐
        ├──────────────────────────────────────────> │    READY     │
        │                                            └──────┬───────┘
        │                                     show_step 畫出 │    ▲ 事件 / timeout
        │                                                   v    │
        │                                            ┌──────────────┐
        │                                            │   SHOWING    │
        │                                            └──────────────┘
        │                                                   │
        │                            inspect / end 在這裡都失敗：show_step_in_progress
        │
        │  <──────── end_tutorial 成功（本篇）：clear + done + delete ────────┐
        │                                                                    │
   (無 Session)  ← 之後 inspect / show / end 一律 session_not_found     ─────┘
        │
        └── 再 start_tutorial → 建立一個「全新的」Session（新 id、steps_shown=0、snapshot#=1）
```

### 2.3 `fake.calls` 走完一輪長這樣

```text
  [("open",     "http://localhost:3000/"),
   ("snapshot", 1),                          <- start_tutorial
   ("show",     {...}),                      <- show_step 畫
   ("snapshot", 2),                          <- show_step 收尾拍新 page
   ("clear",),                               <- end_tutorial ①
   ("done",     "✅ Done — you created a project")]   <- end_tutorial ②

  注意：最後兩筆的「順序」是驗收項目（先 clear 再 done），
  而且清單裡「不可以」出現 ("close",)。
```

---

## 3. 開始前先確認

A01–A12 都已完成並且測試全綠：

- [ ] `uv run pytest -m "not browser" -q` 全綠、**0 skipped**（A12 已把 A09 的 OQ2 skip 打開）。
- [ ] `showme/session.py` 有常數 `DONE_BANNER_TEXT = "✅ Done — you created a project"`，以及 `SessionStore.delete()`、`SessionStore.current()`、`SessionStore.get(session_id)`。
- [ ] `showme/app.py` 的 `start_tutorial`（A08/A09）、`inspect_page`（A10）、`show_step`（A11 + A12）都已完成；`end_tutorial` 目前還是回 `{"error": "not_implemented"}` 的佔位。
- [ ] `showme/browser.py` 的 `BrowserLike` 有 `clear()` 與 `done(text)`。
- [ ] `tests/fakes.py` 的 `FakeBrowser` 會把 `("clear",)`、`("done", text)`、`("close",)` 記進 `self.calls`。
- [ ] `tests/conftest.py` 有 `anyio_backend`、`fake_browser`、`app`、`started` 四個 fixture。

確認 `DONE_BANNER_TEXT` 存在而且字沒打錯（那是一個 emoji + 一個 em dash `—`，不是減號）：

```bash
cd /Users/linjunting/hackathonQoder
uv run python -c "from showme.session import DONE_BANNER_TEXT; print(repr(DONE_BANNER_TEXT))"
```

預期輸出：

```text
'✅ Done — you created a project'
```

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| `end_tutorial` | 第四個 MCP tool。教學結束時由 agent 呼叫，負責收攤。 |
| `summary` | tool 的第二個參數，agent 會傳一句話（例如 `create a project`）。**規格明訂它不進 banner**，我們收下來就丟掉。 |
| `DONE_BANNER_TEXT` | 固定文案常數 `"✅ Done — you created a project"`。Python 這邊決定文字，overlay 只負責顯示（見 `docs/handoff.md`：`done(text)`）。 |
| banner | 頁面右上角（或 overlay 決定的位置）那條「完成了」的橫幅。B 的 overlay 用 `done(text)` 畫；A 的測試裡只驗「有沒有用正確的文字呼叫 done」。 |
| 刪除 Session | 不是把 state 改成 `DONE`，是真的把物件丟掉（`store.delete()`）。規格明訂沒有 DONE 狀態，之後任何 tool 都回 `session_not_found`。 |
| 冪等（idempotent） | 「做兩次跟做一次結果一樣」。`end_tutorial` **不是**冪等的：第二次會失敗回 `session_not_found`，這是 clarify 記錄明確選的行為。 |
| OQ1 | 設計文件 §17 的 open question 1：SHOWING 時 `inspect_page` / `end_tutorial` 該回哪個 error。**A 的設計決定（可改）**：回 `show_step_in_progress`，不新增錯誤碼。 |
| A-2 | A 的設計決定（可改）：`end_tutorial` 之後**不關瀏覽器**。人要看到完成 banner；瀏覽器在 process 結束時（`shutdown()`）才關。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 新增（測試） | `tests/test_tool_end.py` | 本篇全部的行為測試 |
| 修改 | `showme/app.py` | 把 `end_tutorial` 的佔位換成真的實作 |

**不會動到：** `overlay/**`、`showme/server.py`（薄殼在 A07 就寫好了，簽名沒變）、`showme/session.py`、`showme/rules.py`、`showme/browser.py`。

---

## 6. 介面約定

### 6.1 用到（來自前面幾篇，簽名不可改）

```python
# showme/session.py
DONE_BANNER_TEXT = "✅ Done — you created a project"

class State(str, Enum):
    READY = "READY"
    SHOWING = "SHOWING"

class SessionStore:
    def current(self) -> Session | None: ...
    def get(self, session_id: str) -> Session | None:
        """沒有 Session、或 id 對不上 → None。"""
    def create(self, goal: str) -> Session: ...
    def delete(self) -> None: ...
```

```python
# showme/browser.py（BrowserLike，本篇只用這兩個）
async def clear(self) -> None: ...          # window.__showme.clear()
async def done(self, text: str) -> None: ...  # window.__showme.done(text)
```

```python
# showme/app.py（A07 已完成）
async def _ensure_browser(self) -> BrowserLike: ...
```

### 6.2 提供（給後面幾篇）

```python
async def end_tutorial(self, session_id: str, summary: str) -> dict: ...
```

回傳形狀（兩個鍵**永遠都在**）：

```python
{"ok": True,  "error": ""}
{"ok": False, "error": "session_not_found"}
{"ok": False, "error": "show_step_in_progress"}
```

`showme/server.py` 的薄殼（A07 已完成，本篇不改，只是提醒它長這樣）：

```python
@mcp.tool()
async def end_tutorial(session_id: str, summary: str) -> dict:
    """Clear the overlay, show the fixed done banner, and delete the session."""
    return await get_app().end_tutorial(session_id, summary)
```

---

## 7. 步驟

節奏一樣是 TDD：**先寫測試 → 跑一次看它紅 → 寫最小實作 → 跑一次看它綠 → commit**。

### Step 1：先寫測試檔（紅）

建立 `tests/test_tool_end.py`，整份貼上：

```python
"""A13：end_tutorial —— 清 overlay、貼固定 banner、刪 Session。

全部用 FakeBrowser，不開任何瀏覽器。
"""

from __future__ import annotations

import asyncio

import pytest

from showme.session import DONE_BANNER_TEXT, State

pytestmark = pytest.mark.anyio

DASHBOARD = "http://localhost:3000/"


async def _let_it_run(times: int = 5) -> None:
    """把控制權還給 event loop 幾次，讓背景 task 跑到『等 emit』那一步。"""
    for _ in range(times):
        await asyncio.sleep(0)


# --------------------------------------------------------------------------
# 成功路徑
# --------------------------------------------------------------------------

async def test_end_tutorial_returns_ok_true(started):
    app, fake, start_result = started

    result = await app.end_tutorial(start_result["session_id"], "create a project")

    assert result["ok"] is True
    assert result["error"] == ""


async def test_end_tutorial_clears_then_shows_the_banner_in_that_order(started):
    app, fake, start_result = started

    await app.end_tutorial(start_result["session_id"], "create a project")

    assert fake.calls[-2:] == [("clear",), ("done", DONE_BANNER_TEXT)]


async def test_banner_text_is_fixed_and_ignores_summary(started):
    """規格：完成 banner 文案固定，summary 不進橫幅。"""
    app, fake, start_result = started

    await app.end_tutorial(start_result["session_id"], "invite a member")

    assert ("done", DONE_BANNER_TEXT) in fake.calls
    assert ("done", "invite a member") not in fake.calls
    done_texts = [call[1] for call in fake.calls if call[0] == "done"]
    assert done_texts == ["✅ Done — you created a project"]


async def test_session_is_deleted_after_a_successful_end(started):
    app, fake, start_result = started

    await app.end_tutorial(start_result["session_id"], "create a project")

    assert app.store.current() is None


async def test_the_browser_is_not_closed(started):
    """A 的設計決定 A-2（可改）：人要留在畫面上看完成 banner，所以不關瀏覽器。"""
    app, fake, start_result = started

    await app.end_tutorial(start_result["session_id"], "create a project")

    assert ("close",) not in fake.calls
    assert fake.alive is True


# --------------------------------------------------------------------------
# 失敗路徑
# --------------------------------------------------------------------------

async def test_ending_twice_fails_with_session_not_found(started):
    """規格 Example：結束後再結束。"""
    app, fake, start_result = started
    session_id = start_result["session_id"]

    first = await app.end_tutorial(session_id, "create a project")
    assert first["ok"] is True

    second = await app.end_tutorial(session_id, "create a project")
    assert second["ok"] is False
    assert second["error"] == "session_not_found"


async def test_inspect_page_after_end_fails_with_session_not_found(started):
    """規格：Session 刪掉之後，任何 tool 都是 session_not_found。"""
    app, fake, start_result = started
    session_id = start_result["session_id"]

    await app.end_tutorial(session_id, "create a project")

    inspected = await app.inspect_page(session_id)
    assert inspected["error"] == "session_not_found"
    assert inspected["page"] is None


async def test_end_with_an_unknown_session_id_fails(started):
    app, fake, start_result = started

    result = await app.end_tutorial("s_missing", "create a project")

    assert result["ok"] is False
    assert result["error"] == "session_not_found"
    assert app.store.current() is not None, "id 對不上不可以把現有的 Session 刪掉"


async def test_end_without_any_session_fails(app, fake_browser):
    """完全還沒 start_tutorial 就結束。"""
    result = await app.end_tutorial("s_8f2a", "create a project")

    assert result["ok"] is False
    assert result["error"] == "session_not_found"


async def test_end_while_showing_is_rejected(started):
    """OQ1（A 的設計決定，可改）：SHOWING 時 end_tutorial 回 show_step_in_progress。

    規格只說「狀態不是 READY 時操作失敗」，沒給錯誤字串；
    我們重用既有的 show_step_in_progress，不新增第七個錯誤碼。
    """
    app, fake, start_result = started
    uid = start_result["page"]["elements"][0]["uid"]

    task = asyncio.create_task(
        app.show_step(start_result["session_id"], uid, "Click New Project", "click", 1, 4)
    )
    await _let_it_run()
    assert app.store.current().state is State.SHOWING

    result = await app.end_tutorial(start_result["session_id"], "create a project")

    assert result["ok"] is False
    assert result["error"] == "show_step_in_progress"
    assert app.store.current() is not None, "被拒絕就不可以刪 Session"
    assert ("done", DONE_BANNER_TEXT) not in fake.calls, "被拒絕就不可以貼 banner"

    # 收尾：讓卡住的 show_step 結束
    fake.emit("step_done")
    await task


# --------------------------------------------------------------------------
# 結束之後還能重新開始
# --------------------------------------------------------------------------

async def test_start_tutorial_after_end_creates_a_brand_new_session(started):
    app, fake, start_result = started

    await app.end_tutorial(start_result["session_id"], "create a project")
    assert app.store.current() is None

    again = await app.start_tutorial(DASHBOARD, "invite a member")

    assert again["error"] == ""
    assert again["goal"] == "invite a member"
    assert again["session_id"] != ""

    session = app.store.current()
    assert session is not None
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 1
    assert all(el["uid"].startswith("s1-") for el in again["page"]["elements"])
```

跑一次看它紅：

```bash
cd /Users/linjunting/hackathonQoder
uv run pytest tests/test_tool_end.py -q
```

預期會看到一整排 `F`，訊息大致像這樣：

```text
FFFF.FFFFFF                                                         [100%]
=================================== FAILURES ===================================
_______________________ test_end_tutorial_returns_ok_true ______________________
>       assert result["ok"] is True
E       KeyError: 'ok'
...
________ test_end_tutorial_clears_then_shows_the_banner_in_that_order __________
>       assert fake.calls[-2:] == [("clear",), ("done", DONE_BANNER_TEXT)]
E       AssertionError: assert [('open', 'http://localhost:3000/'), ('snapshot', 1)] == [('clear',), ('done', '✅ Done — you created a project')]
10 failed, 1 passed in 0.3s
```

（`test_the_browser_is_not_closed` 會意外地綠——因為佔位根本沒碰瀏覽器，當然也就沒有 `("close",)`。這個測試要等實作寫完才有意義。紅的那一輪你可能還會看到 `Task was destroyed but it is pending!` 的警告，那是 `test_end_while_showing_is_rejected` 提早失敗、來不及收掉背景 task，實作寫完就不會再出現。）

**紅得對**：現在 `end_tutorial` 回的是佔位 `{"error": "not_implemented"}`，沒有 `ok` 鍵，也完全沒碰瀏覽器。

### Step 2：寫實作

打開 `showme/app.py`，把 `end_tutorial` 換成這一份：

```python
    async def end_tutorial(self, session_id: str, summary: str) -> dict:
        """清掉 overlay、貼上固定的完成 banner、刪掉 Session。

        summary 只是給呼叫端自己記錄用的，規格明訂它不影響 banner 文案，
        所以這裡刻意完全不使用它。瀏覽器不關（A 的設計決定 A-2，可改）：
        人要留在畫面上看到那句 ✅。
        """
        session = self.store.get(session_id)
        if session is None:
            return {"ok": False, "error": "session_not_found"}

        # OQ1（A 的設計決定，可改）：正在等人做事就不准收攤，重用既有的錯誤碼。
        if session.state is State.SHOWING:
            return {"ok": False, "error": "show_step_in_progress"}

        browser = await self._ensure_browser()
        await browser.clear()
        await browser.done(DONE_BANNER_TEXT)
        self.store.delete()
        return {"ok": True, "error": ""}
```

確認 `showme/app.py` 最上面的 import 有 `DONE_BANNER_TEXT`（A07 建骨架時就該有了；沒有就補進那個 `from showme.session import (...)` 的清單）：

```python
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

> **三個容易寫錯的地方**
> 1. `clear()` 一定在 `done()` 之前。先拿掉箭頭，再貼橫幅；反過來會讓橫幅被 clear 掉（B 的 overlay 怎麼實作是他家的事，但呼叫順序是接縫的一部分）。
> 2. `store.delete()` 一定在兩個 await 之後。萬一 `clear()` 丟例外，Session 還在，agent 可以重試。
> 3. **不要**寫 `await browser.close()`。

### Step 3：跑綠

```bash
uv run pytest tests/test_tool_end.py -q
```

預期輸出：

```text
...........                                                         [100%]
11 passed in 0.2s
```

再跑一次全部不開瀏覽器的測試：

```bash
uv run pytest -m "not browser" -q
```

預期：全綠、0 skipped。

### Step 4：用一次「完整走完一輪」確認手感（可選，2 分鐘）

這一步不寫進測試檔，只是讓你親眼看到四個 tool 串起來的樣子。開一個 Python REPL：

```bash
uv run python
```

貼進去：

```python
import asyncio
import sys; sys.path.insert(0, "tests")   # 跑 pytest 時不用這行：pytest 會自己把 tests/ 放進 sys.path

from showme.app import ShowMeApp
from fakes import FakeBrowser            # tests/ 沒有 __init__.py，所以是 fakes 不是 tests.fakes

fake = FakeBrowser()
fake.add_page("http://localhost:3000/", "Dashboard",
              [{"role": "button", "name": "New Project", "testid": "new-project"}])

async def main():
    app = ShowMeApp(browser_factory=lambda: fake)
    start = await app.start_tutorial("http://localhost:3000/", "create a project")
    print("start :", start["session_id"], start["page"]["elements"])
    uid = start["page"]["elements"][0]["uid"]
    task = asyncio.create_task(app.show_step(start["session_id"], uid, "Click New Project", "click", 1, 2))
    for _ in range(5):
        await asyncio.sleep(0)
    fake.emit("step_done")
    print("step  :", await task)
    print("end   :", await app.end_tutorial(start["session_id"], "create a project"))
    print("again :", await app.end_tutorial(start["session_id"], "create a project"))
    print("calls :", fake.calls)

asyncio.run(main())
```

預期輸出（`s_xxxx` 每次不同）：

```text
start : s_8f2a [{'uid': 's1-1', 'role': 'button', 'name': 'New Project', 'testid': 'new-project'}]
step  : {'event': 'step_done', 'signal': '', 'elapsed_s': 0.0, 'page': {...}, 'next_action': 'If the goal is not yet achieved, ...', 'error': ''}
end   : {'ok': True, 'error': ''}
again : {'ok': False, 'error': 'session_not_found'}
calls : [('open', 'http://localhost:3000/'), ('snapshot', 1), ('show', {...}), ('snapshot', 2), ('clear',), ('done', '✅ Done — you created a project')]
```

按 `Ctrl-D` 離開 REPL。

### Step 5：commit

```bash
git add showme/app.py tests/test_tool_end.py
git commit -m "feat: end_tutorial clears overlay, shows the fixed banner, deletes the session"
```

---

## 8. 驗收清單

- [ ] `uv run pytest tests/test_tool_end.py -q` → 11 passed。
- [ ] `uv run pytest -m "not browser" -q` → 全綠、0 skipped。
- [ ] 成功時 `result["ok"] is True`（是 `True` 這個布林，不是 `1`、不是 `"true"`）且 `result["error"] == ""`。
- [ ] `fake.calls` 的最後兩筆**依序**是 `("clear",)`、`("done", DONE_BANNER_TEXT)`。
- [ ] `summary` 傳 `"invite a member"`，`done` 的文字仍然是 `"✅ Done — you created a project"`。
- [ ] 成功之後 `app.store.current()` 是 `None`。
- [ ] 再 `end_tutorial` → `{"ok": False, "error": "session_not_found"}`。
- [ ] 再 `inspect_page` → `error == "session_not_found"`、`page is None`。
- [ ] 用假的 `session_id`（`"s_missing"`）→ `session_not_found`，而且**現有的 Session 沒被刪掉**。
- [ ] 完全沒有 Session 時呼叫 → `session_not_found`。
- [ ] SHOWING 時呼叫 → `show_step_in_progress`，Session 沒被刪、banner 沒貼（OQ1，A 的設計決定，可改）。
- [ ] `fake.calls` 裡**沒有** `("close",)`，`fake.alive` 仍是 `True`（A-2，可改）。
- [ ] `end_tutorial` 之後再 `start_tutorial` → `error == ""`、有新的 Session、`state is State.READY`、`steps_shown == 0`、`snapshot_no == 1`、page 的 uid 是 `s1-*`。
- [ ] 沒有動到 `overlay/**` 與 `showme/server.py`。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `assert fake.calls[-2:] == [("clear",), ("done", ...)]` 失敗，實際多了一筆 `("snapshot", n)` | `end_tutorial` 裡多呼叫了 `_take_snapshot` | `end_tutorial` **不拍 snapshot**，它的回傳只有 `ok` 與 `error` 兩個鍵 |
| `("done", "✅ Done — you created a project")` 比不過，看起來字一模一樣 | 中間那條是 em dash `—`（U+2014），不是 hyphen `-`；或 emoji 後面少一個空格 | 一律 `from showme.session import DONE_BANNER_TEXT` 引用常數，**不要**在測試或實作裡再打一次字串 |
| `test_the_browser_is_not_closed` 失敗 | 寫了 `await browser.close()` | 拿掉。瀏覽器只在 `ShowMeApp.shutdown()`（process 結束）時關 |
| `test_end_with_an_unknown_session_id_fails` 失敗、Session 被刪掉了 | 用 `self.store.current()` 判斷而不是 `self.store.get(session_id)` | 一律 `self.store.get(session_id)`：它會同時處理「沒有 Session」與「id 對不上」兩種情況 |
| SHOWING 的測試掛住 60 秒被砍 | 建了 `create_task` 卻沒有 `fake.emit(...)` + `await task` 收尾 | 測試最後兩行一定要有 |
| `AttributeError: 'FakeBrowser' object has no attribute 'done'` | `tests/fakes.py` 漏了 `done` | 補上 `async def done(self, text): self.calls.append(("done", text))` |
| `ok` 是 `1` 不是 `True`，測試用 `is True` 比失敗 | 寫成 `"ok": bool(1)` 之類 | 直接寫字面值 `True` / `False` |
| 結束後再 `start_tutorial`，`session_id` 跟之前一樣 | `store.delete()` 沒真的把物件丟掉（例如只改了 state） | `delete()` 要把內部那個 optional 欄位設回 `None`；A02 的 `test_session.py` 有測這條，回去看看 |
| 想順手做「end 之後 banner 也自動消失」 | 這不是規格 | 不要做。人必須看得到 banner；`clear()` 是拿掉**箭頭**，不是拿掉 banner |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `features/結束教學.feature` | Rule：成功結束後回傳 ok 為 true（Example：結束一場教學） | `test_end_tutorial_returns_ok_true` |
| `features/結束教學.feature` | Rule：session 不存在時操作失敗且錯誤為 session_not_found（Example：用假的場次識別 `s_missing`） | `test_end_with_an_unknown_session_id_fails`、`test_end_without_any_session_fails` |
| `features/結束教學.feature` | Rule：成功結束後刪除 Session（Example：結束後再結束 → session_not_found） | `test_session_is_deleted_after_a_successful_end`、`test_ending_twice_fails_with_session_not_found` |
| `features/結束教學.feature` | Rule：session 狀態不是 READY 時操作失敗（Example 仍是 `#TODO`） | `test_end_while_showing_is_rejected`；錯誤字串是 **A 的設計決定 OQ1（可改）**：`show_step_in_progress` |
| `features/結束教學.feature` | Rule：成功結束後清掉 overlay（Example 仍是 `#TODO`） | `await browser.clear()`；`test_end_tutorial_clears_then_shows_the_banner_in_that_order` |
| `features/結束教學.feature` | Rule：成功結束後顯示完成 banner，文案固定且忽略 summary（Example：傳入 `invite a member` 文案仍相同） | `test_banner_text_is_fixed_and_ignores_summary` |
| `features/檢查頁面.feature` | Rule：session 不存在時 inspect_page 為 session_not_found | `test_inspect_page_after_end_fails_with_session_not_found`（「結束後」也算不存在） |
| `features/開始教學.feature` | Rule：Session 已刪除後再 start_tutorial 新建 Session | `test_start_tutorial_after_end_creates_a_brand_new_session` |
| `.clarify/resolved/features/結束教學_完成banner文案與summary參數的關係為何.md` | 答案 B：banner 固定為 `✅ Done — you created a project`，忽略 summary | 呼叫 `browser.done(DONE_BANNER_TEXT)`，實作完全不讀 `summary` |
| `.clarify/resolved/features/結束教學_釋放後該session_id再呼叫要如何回應.md` | 答案 A：刪除 Session；之後任何 tool 皆 session_not_found | `store.delete()` + 兩個「之後」測試 |
| `.clarify/resolved/features/結束教學_session不存在時的錯誤碼為何.md` | 答案 A：`session_not_found`（不是冪等成功） | 失敗路徑測試 |
| `.clarify/resolved/data/Session_各狀態允許呼叫哪些MCP工具.md` | 答案 A：僅 READY 可 show_step / inspect / end；SHOWING 只等 | SHOWING 檢查放在 `session is None` 之後 |
| `docs/spec/erm.dbml` | Session Note：「end_tutorial 成功後刪除 Session，不保留 DONE」「end_tutorial 的 summary 不影響完成 banner」 | 同上 |
| `docs/design/showme.md` §7.4 | 成功：`ok=true`、`error=""`、`clear()` + `done("✅ Done — you created a project")`、忽略 summary、刪除 Session | 實作三行 |
| `docs/design/showme.md` §8 | `READY ──end_tutorial 成功──▶（刪除，無 Session）` | `store.delete()` |
| `docs/design/showme.md` §13 | 只准用六個錯誤碼；`show_step_in_progress` 是其中之一 | 沒有新增第七個碼 |
| `docs/design/showme.md` §17 open Q1 | SHOWING 時 `inspect_page` / `end_tutorial` 的 error 字串未定案 | 文件與測試都標成 **A 的設計決定（可改）**，不寫成規格 |
| `docs/handoff.md` 鎖死的名字 | `__showme.clear()`、`__showme.done(text)`；文案由 A 傳入 | `browser.clear()` → `browser.done(DONE_BANNER_TEXT)` |
