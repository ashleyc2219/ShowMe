# A11｜show_step 的六道前置檢查

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：`A10_inspect_page.md` ｜ 下一篇：`A12_show_step阻塞等待.md`
> 對應設計：`docs/design/showme.md` §7.3（tool 契約）、§8（狀態機）、§10（uid 驗證）、§13（錯誤語意）｜ 對應切片：S6
> 預估時間：45–60 分鐘

---

## 1. 這一篇要做什麼

`show_step` 是四個 tool 裡最複雜的一個：**驗 uid → 畫箭頭 → 阻塞等使用者做完 → 回新 page**。這一篇只做前半段的「驗」：**六道前置檢查**。每一道被擋下來的呼叫都必須是「什麼都沒發生」——不畫箭頭、`steps_shown` 不加、state 不變。

通過六道檢查之後的「畫 + 等」留給 A12。本篇先在那裡放一個佔位回傳 `{"error": "not_implemented"}`，測試看到這個佔位就代表「前置檢查全過了」。

---

## 2. 做完會看到什麼

### 2.1 六道關卡漏斗

```text
show_step(session_id, uid, instruction, kind, step_index, step_total, expect_text="", timeout_s=120)
   │
   ├─(1) store.get(session_id) is None ? ────────▶ error="session_not_found"       page=None
   │        沒有場次，或 id 對不上
   │
   ├─(2) session.state is SHOWING ? ─────────────▶ error="show_step_in_progress"   page=None
   │        已經有一次在等使用者了（第一次繼續等，不取消）
   │
   ├─(3) session.steps_shown >= MAX_STEPS(12) ? ─▶ error="max_steps_exceeded"      page=None
   │
   ├─(4) kind = normalize_kind(kind)
   │     expect_text_missing(kind, expect_text) ?▶ error="expect_text_required"    page=None
   │        （kind 不是 click/input/select 一律變成 observe，observe 就必須有 expect_text）
   │
   ├─(5) uid 不在 session.latest_page ? ─────────▶ error="uid_not_in_snapshot"
   │        先拍一份新鮮 page（snapshot# +1）        page=剛拍好的新鮮 page   ← 只有這一關會附 page
   │
   ├─(6) timeout_s = normalize_timeout_s(timeout_s)   未傳／0／負值 → 120.0（這一關不會失敗）
   │
   ▼
  六關全過 ──▶ 本篇先回 error="not_implemented"
              A12 換成：畫箭頭 → state=SHOWING → steps_shown+1 → 阻塞等 emit 或 timeout → 回新 page
```

### 2.2 被擋下來時，什麼可以動、什麼不准動

```text
                            steps_shown   snapshot_no   state    browser.show 被呼叫？
  ────────────────────────  ───────────   ───────────   ──────   ──────────────────
  (1) session_not_found         —             —           —              否
  (2) show_step_in_progress    不變          不變      不變(SHOWING)      否
  (3) max_steps_exceeded       不變          不變      不變(READY)        否
  (4) expect_text_required     不變          不變      不變(READY)        否
  (5) uid_not_in_snapshot      不變          +1        不變(READY)        否
  (6) 六關全過（本篇佔位）      不變          不變      不變(READY)        否
      六關全過（A12 完成後）     +1           +1        SHOWING→READY      是
```

只有第 5 關會動 `snapshot_no`，因為規格明寫「uid 失敗仍附新鮮 page 且 snapshot# 加一」——這是給 agent 的救生索：它拿到新清單就能重挑一個 uid 再試。

---

## 3. 開始前先確認

- [ ] A08、A09、A10 的驗收都打勾了。
- [ ] `uv run pytest -m "not browser" -q` 全綠（只有 A09 那一條 `@pytest.mark.skip`）。
- [ ] `showme/app.py` 的 `start_tutorial` 與 `inspect_page` 都已完成；`show_step` 與 `end_tutorial` 還是 `return {"error": "not_implemented"}`。
- [ ] `showme/rules.py` 有 `normalize_kind`、`expect_text_missing`、`uid_in_page`、`normalize_timeout_s`，而且 `tests/test_rules.py`（A03）全綠。
- [ ] `showme/session.py` 有 `MAX_STEPS = 12`、`DEFAULT_TIMEOUT_S = 120.0`、`State`。
- [ ] `tests/conftest.py` 有 `fake_browser`、`app`、`started` 三個 fixture；`started` 之後 `latest_page` 的 uid 是 `s1-1`（New Project）與 `s1-2`（Settings）。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| 前置檢查（pre-check） | 在真的動手之前先確認「這個要求合不合理」。不合理就立刻回一個錯誤碼，而且**保證什麼都沒改**。 |
| 陳舊的 uid（stale uid） | 舊世代的代號，例如手上還拿著 `s1-4`，但畫面已經重拍成 `s3-*` 了。規格用 snapshot# 讓舊 uid 自動失效。 |
| `normalize_kind(kind)` | 把 `kind` 洗乾淨：不是 `click`／`input`／`select`／`observe` 的（含 `None`、空字串、大小寫不同）一律變成 `observe`。 |
| `expect_text_missing(kind, expect_text)` | 問「這一步是 observe 而且沒給要等的文字嗎？」是 → `True` → 回 `expect_text_required`。 |
| `uid_in_page(uid, page)` | 問「這個 uid 在這份清單裡嗎？」`page` 是 `None` 時回 `False`。 |
| `normalize_timeout_s(value)` | `None`／`0`／負值 → `120.0`；其他轉成 `float`。 |
| `MAX_STEPS` | 常數 12。`steps_shown >= 12` 就不准再畫，避免 agent 無限迴圈。**注意是 `>=` 不是 `>`**。 |
| 佔位回傳（placeholder） | 暫時放一個「還沒做」的回傳值，讓上下游可以先接起來。本篇的佔位是 `error="not_implemented"`，A12 會換掉。 |
| `#TODO` 的 Rule | `.feature` 裡有規則、但沒有例子。這種只測「負責層的不變條件」，**不可以自己發明例子當需求**。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 修改 | `showme/app.py` | 只改 `ShowMeApp.show_step()`。其他方法一律不動。 |
| 新增 | `tests/test_tool_show_step_checks.py` | `show_step` 六道前置檢查的測試（不開瀏覽器）。A12 的等待測試會另外開 `tests/test_tool_show_step_wait.py`。 |
| 修改 | `tests/test_fakes.py` | 只刪一行：末尾 parametrize 的 `show_step` 佔位案例。實作後 `show_step` 不再回裸 `{"error": "not_implemented"}`（六個鍵都在），那條佔位測試在**本篇**就過期了，不是 A12。 |

---

## 6. 介面約定

### 6.1 用到（重述精確簽名）

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

class SessionStore:
    def get(self, session_id: str) -> Session | None:
        """沒有 Session、或 id 對不上 → None。"""

# showme/rules.py
KINDS = ("click", "input", "select", "observe")

def normalize_timeout_s(value: float | int | None) -> float:
    """None、0、負值 → 120.0；其他轉 float 原樣回傳。"""

def normalize_kind(kind: str | None) -> str:
    """不在 KINDS 裡（含 None、空字串、大小寫不同）→ 'observe'。"""

def expect_text_missing(kind: str, expect_text: str | None) -> bool:
    """normalize_kind(kind) == 'observe' 且 (expect_text is None or expect_text == '') → True。"""

def uid_in_page(uid: str, page: dict | None) -> bool: ...

# showme/app.py（A07／A10 已完成）
async def _take_snapshot(self, session: Session) -> dict:
    """snapshot_no += 1 → browser.snapshot(n) → build_page → 寫進 latest_page → 回 page"""
```

### 6.2 提供（給後面幾篇）

```python
async def show_step(self, session_id: str, uid: str, instruction: str, kind: str,
                    step_index: int, step_total: int, expect_text: str = "",
                    timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, object]
# 失敗（六道前置檢查）：
#   {"event": "", "signal": "", "elapsed_s": 0.0,
#    "page": <uid_not_in_snapshot 時是新鮮 page，其他一律 None>,
#    "next_action": "", "error": <六個錯誤碼之一>}
# 通過（本篇佔位，A12 換掉）：
#   {"event": "", "signal": "", "elapsed_s": 0.0, "page": None, "next_action": "", "error": "not_implemented"}
```

A12 會保留這六道檢查一字不改，只把最後那個佔位換成「畫 + 等」，並改回 `{"event": "step_done"|"stuck"|"timeout", "signal": "", "elapsed_s": 4.2, "page": {...}, "next_action": STEP_NEXT_ACTION, "error": ""}`。

---

## 7. 步驟

### Step 1：建立測試檔，寫前三關的測試（先看它紅）

建立 `tests/test_tool_show_step_checks.py`，內容如下（整檔貼上）：

```python
"""show_step 六道前置檢查的測試。全部用 FakeBrowser，不開瀏覽器。

通過前置檢查的路徑本篇還沒實作，會回 error="not_implemented"；
測試看到這個佔位就代表「六關都過了」。A12 會把佔位換成真的畫箭頭與阻塞等待。
"""

from __future__ import annotations

import pytest

from showme.session import MAX_STEPS, State

pytestmark = pytest.mark.anyio

NEW_PROJECT_URL = "http://localhost:3000/projects/new"


# Rule: session 不存在時操作失敗且錯誤為 session_not_found
async def test_show_step_without_a_session_returns_session_not_found(app):
    result = await app.show_step("s_8f2a", "s1-1", "Click New Project", "click", 1, 4)

    assert result["error"] == "session_not_found"
    assert result["page"] is None
    assert result["event"] == ""


# Rule: session 不存在時操作失敗且錯誤為 session_not_found
async def test_show_step_with_an_unknown_session_id_returns_session_not_found(started):
    app, fake, first = started

    result = await app.show_step("s_missing", "s1-1", "Click New Project", "click", 1, 4)

    assert result["error"] == "session_not_found"
    assert result["page"] is None
    assert app.store.current().steps_shown == 0
    assert not any(call[0] == "show" for call in fake.calls)


# Rule: 同一 session 並發的 show_step 被拒絕且錯誤為 show_step_in_progress
#       Example: 正在等使用者時又畫下一步
async def test_show_step_while_showing_returns_show_step_in_progress(started):
    app, fake, first = started
    session = app.store.current()
    session.state = State.SHOWING

    result = await app.show_step(first["session_id"], "s1-1", "Click New Project", "click", 1, 4)

    assert result["error"] == "show_step_in_progress"
    assert result["page"] is None
    # 第一次繼續等：state 不變、什麼都沒畫
    assert session.state is State.SHOWING
    assert session.steps_shown == 0
    assert not any(call[0] == "show" for call in fake.calls)


# Rule: steps_shown 大於等於 12 時操作失敗且錯誤為 max_steps_exceeded
#       Example: 已畫滿 12 步
async def test_show_step_with_twelve_steps_returns_max_steps_exceeded(started):
    app, fake, first = started
    session = app.store.current()
    session.steps_shown = MAX_STEPS

    result = await app.show_step(first["session_id"], "s1-1", "Click New Project", "click", 1, 4)

    assert result["error"] == "max_steps_exceeded"
    assert result["page"] is None
    assert session.steps_shown == MAX_STEPS
    assert not any(call[0] == "show" for call in fake.calls)


# Rule: steps_shown 大於等於 12 時操作失敗（11 步還沒滿，不可以擋）
async def test_show_step_with_eleven_steps_passes_the_pre_checks(started):
    app, fake, first = started
    session = app.store.current()
    session.steps_shown = MAX_STEPS - 1

    result = await app.show_step(
        first["session_id"], "s1-1", "Click New Project", "click", 1, 4, timeout_s=0.2
    )

    assert result["error"] == "not_implemented"   # 六關都過了（A12 會換成真的等待）


# 檢查順序：state 比 steps_shown 先檢查
async def test_state_is_checked_before_the_step_count(started):
    app, fake, first = started
    session = app.store.current()
    session.state = State.SHOWING
    session.steps_shown = MAX_STEPS

    result = await app.show_step(first["session_id"], "s1-1", "Click New Project", "click", 1, 4)

    assert result["error"] == "show_step_in_progress"
```

跑：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期紅燈，重點行是：

```text
E       AssertionError: assert 'not_implemented' == 'session_not_found'
...
5 failed, 1 passed in 0.12s
```

（唯一綠的是 `test_show_step_with_eleven_steps_passes_the_pre_checks`——佔位剛好就回 `not_implemented`。這正常，它是要守住「11 步不可以被擋」這個邊界。）

---

### Step 2：實作前三關 + 佔位（讓它綠）

打開 `showme/app.py`，把 `show_step` 整個換掉：

```python
    async def show_step(self, session_id: str, uid: str, instruction: str, kind: str,
                        step_index: int, step_total: int, expect_text: str = "",
                        timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, object]:
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
        # A12 會把下面這一行換成「畫箭頭 + 阻塞等待 emit 或 timeout」。
        return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                "next_action": "", "error": "not_implemented"}
```

跑：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期：

```text
6 passed in 0.12s
```

**檢查順序不是隨便排的**，`test_state_is_checked_before_the_step_count` 就是在釘住它：SHOWING 而且已經畫滿 12 步時，要回 `show_step_in_progress` 而不是 `max_steps_exceeded`。理由是「正在等的那一次 `show_step` 還在跑」是更急迫、更能解釋現況的事實；agent 看到 `show_step_in_progress` 才知道「我不該現在再送一個」。規格沒有規定順序，但**測試把它釘死了，之後誰調換順序都會被抓到**。

另外注意 `>=`：規格寫「`steps_shown >= 12` 時失敗」，所以第 12 步是**畫不出來**的（畫完第 12 步時 `steps_shown` 已經是 12）。

---

### Step 3：寫 kind 與 expect_text 的測試（會紅）

在 `tests/test_tool_show_step_checks.py` 最後加上：

```python
# Rule: kind 不屬於 click、input、select、observe 時視為 observe
#       Example: 傳入 tap 且 expect_text 為空
async def test_unknown_kind_without_expect_text_returns_expect_text_required(started):
    app, fake, first = started

    result = await app.show_step(
        first["session_id"], "s1-1", "Wait for the heading", "tap", 1, 4, expect_text=""
    )

    assert result["error"] == "expect_text_required"
    assert result["page"] is None
    assert app.store.current().steps_shown == 0
    assert not any(call[0] == "show" for call in fake.calls)


# Rule: kind 為 observe 且 expect_text 為空時操作失敗且錯誤為 expect_text_required
#       Example: 等文字出現但沒帶文字
async def test_observe_without_expect_text_returns_expect_text_required(started):
    app, fake, first = started

    result = await app.show_step(
        first["session_id"], "s1-1", "Wait for the heading", "observe", 1, 4, expect_text=""
    )

    assert result["error"] == "expect_text_required"
    assert result["page"] is None
    assert app.store.current().steps_shown == 0
    assert not any(call[0] == "show" for call in fake.calls)


# Rule: kind 為 observe 且 expect_text 為空時操作失敗（有帶文字就不該被擋）
async def test_observe_with_expect_text_passes_the_pre_checks(started):
    app, fake, first = started

    result = await app.show_step(
        first["session_id"], "s1-1", "Wait for the heading", "observe", 1, 4,
        expect_text="New Project", timeout_s=0.2,
    )

    assert result["error"] == "not_implemented"   # 六關都過了


# Rule: kind 為 observe 且 expect_text 為空時操作失敗（其他 kind 不受這條限制）
async def test_click_without_expect_text_passes_the_pre_checks(started):
    app, fake, first = started

    result = await app.show_step(
        first["session_id"], "s1-1", "Click New Project", "click", 1, 4,
        expect_text="", timeout_s=0.2,
    )

    assert result["error"] == "not_implemented"   # 六關都過了
```

跑：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期紅燈，重點行是：

```text
E       AssertionError: assert 'not_implemented' == 'expect_text_required'
...
2 failed, 8 passed in 0.13s
```

---

### Step 4：實作第四關（讓它綠）

把 `showme/app.py` 的 `show_step` 整個換成：

```python
    async def show_step(self, session_id: str, uid: str, instruction: str, kind: str,
                        step_index: int, step_total: int, expect_text: str = "",
                        timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, object]:
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
        # A12 會把下面這一行換成「畫箭頭 + 阻塞等待 emit 或 timeout」。
        return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                "next_action": "", "error": "not_implemented"}
```

跑：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期：

```text
10 passed in 0.13s
```

**`kind = normalize_kind(kind)` 那一行把參數本身覆蓋掉是刻意的**：從這一行以後，程式裡的 `kind` 一定是四個合法值之一。A12 會把這個洗乾淨的 `kind` 傳給 `browser.show({... "kind": kind ...})`，overlay（B）才不用再處理奇怪的字串。這正是規格「非法 kind 視為 observe」的落點——它是 **T 層（tool handler）**的責任，不是 overlay 的（design §18 的覆蓋表就是這樣分的）。

---

### Step 5：寫 uid 驗證的測試（會紅）

在 `tests/test_tool_show_step_checks.py` 最後加上：

```python
# Rule: uid 不在最新 snapshot 時操作失敗且錯誤為 uid_not_in_snapshot
# Rule: uid 不在最新 snapshot 時回傳新鮮 page 且 uid snapshot# 加一
async def test_stale_uid_returns_uid_not_in_snapshot_with_a_fresh_page(started):
    app, fake, first = started

    result = await app.show_step(first["session_id"], "s0-9", "Click New Project", "click", 1, 4)

    assert result["error"] == "uid_not_in_snapshot"
    assert result["page"] is not None
    uids = [element["uid"] for element in result["page"]["elements"]]
    assert uids != []
    assert all(uid.startswith("s2-") for uid in uids)
    assert app.store.current().snapshot_no == 2
    assert result["event"] == ""
    assert result["next_action"] == ""


# Rule: uid 不在最新 snapshot 時操作失敗且錯誤為 uid_not_in_snapshot（同世代但位置不存在）
async def test_uid_with_an_unknown_index_returns_uid_not_in_snapshot(started):
    app, fake, first = started

    result = await app.show_step(first["session_id"], "s1-99", "Click New Project", "click", 1, 4)

    assert result["error"] == "uid_not_in_snapshot"
    assert all(e["uid"].startswith("s2-") for e in result["page"]["elements"])


# Rule: uid 驗證失敗不畫、steps_shown 不加
async def test_uid_failure_does_not_draw_and_does_not_count(started):
    app, fake, first = started
    session = app.store.current()

    await app.show_step(first["session_id"], "s0-9", "Click New Project", "click", 1, 4)

    assert session.steps_shown == 0
    assert session.state is State.READY
    assert not any(call[0] == "show" for call in fake.calls)


# Rule: uid 不在最新 snapshot 時回傳新鮮 page（agent 可以用新 page 的 uid 再試一次）
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
    assert retried["error"] == "not_implemented"   # 六關都過了


# 回傳形狀固定：六個鍵永遠都在
async def test_failed_pre_checks_return_all_six_keys(started):
    app, fake, first = started
    keys = {"event", "signal", "elapsed_s", "page", "next_action", "error"}

    not_found = await app.show_step("s_missing", "s1-1", "Click New Project", "click", 1, 4)
    bad_uid = await app.show_step(first["session_id"], "s0-9", "Click New Project", "click", 1, 4)

    assert set(not_found) == keys
    assert set(bad_uid) == keys
    assert not_found["signal"] == "" and not_found["elapsed_s"] == 0.0
    assert bad_uid["signal"] == "" and bad_uid["elapsed_s"] == 0.0
```

跑：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期紅燈，重點行是：

```text
E       AssertionError: assert 'not_implemented' == 'uid_not_in_snapshot'
...
E       TypeError: 'NoneType' object is not subscriptable
...
3 failed, 12 passed in 0.14s
```

三條紅的是 `test_stale_uid_returns_uid_not_in_snapshot_with_a_fresh_page`、`test_uid_with_an_unknown_index_returns_uid_not_in_snapshot`（錯誤碼不對），以及 `test_uid_failure_lets_the_next_call_use_a_fresh_uid`（佔位的 `page` 是 `None`，`failed["page"]["elements"]` 就會丟 `TypeError`）。

另外兩條新測試現在是綠的，但它們**不是白寫的**：`test_uid_failure_does_not_draw_and_does_not_count` 與 `test_failed_pre_checks_return_all_six_keys` 驗的是「沒有副作用」與「六個鍵都在」，等一下實作第五關時，只要不小心把 `steps_shown` 加上去或漏了某個鍵，它們就會變紅。

---

### Step 6：實作第五、六關（讓它綠）

把 `showme/app.py` 的 `show_step` 整個換成**最終版**：

```python
    async def show_step(self, session_id: str, uid: str, instruction: str, kind: str,
                        step_index: int, step_total: int, expect_text: str = "",
                        timeout_s: float = DEFAULT_TIMEOUT_S) -> dict[str, object]:
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
            # 不畫、steps_shown 不加，但要附一份新鮮 page（snapshot# +1）讓 agent 重挑 uid。
            page = await self._take_snapshot(session)
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": page,
                    "next_action": "", "error": "uid_not_in_snapshot"}
        timeout_s = normalize_timeout_s(timeout_s)
        # A12 會把下面這一行換成「畫箭頭 + 阻塞等待 emit 或 timeout」，
        # 並用上面這個正規化過的 timeout_s 當等待上限。
        return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                "next_action": "", "error": "not_implemented"}
```

跑：

```bash
uv run pytest tests/test_tool_show_step_checks.py -q
```

預期：

```text
15 passed in 0.15s
```

**關於第六關 `timeout_s = normalize_timeout_s(timeout_s)`：** 這一行現在算完沒有人用（因為佔位不會等待），所以本篇**沒有**替它寫測試——`timeout_s` 未傳／`0`／負值 → `120.0` 這條規格，A03 已經對 `normalize_timeout_s()` 這個純函數測過了（`tests/test_rules.py`）。A12 會把它接上真正的等待，那時「傳 0 要等 120 秒而不是立刻 timeout」才變成看得見的行為，也才有辦法測。**現在不要為了讓它「有被用到」而亂改行為**。

**為什麼 uid 檢查要放在最後（第五關）？** 因為它是唯一會**動到狀態**（`snapshot_no +1`）的檢查。前面四關都是「純看資料」，能先擋掉就先擋掉，這樣「被 `max_steps_exceeded` 擋下的呼叫也不會偷偷多拍一張快照」。

---

### Step 7：跑完整套件並 commit

```bash
uv run pytest -m "not browser" -q
```

預期最後一行類似：

```text
115 passed, 1 skipped in 0.10s
```

（`1 skipped` 是 A09 那條 OQ2 測試，A12 會打開。）

```bash
git add showme/app.py tests/test_tool_show_step_checks.py tests/test_fakes.py
git commit -m "feat: show_step pre-checks for session, state, steps, kind and uid"
```

預期輸出類似：

```text
[main 4d5e6f7] feat: show_step pre-checks for session, state, steps, kind and uid
 2 files changed, 148 insertions(+), 2 deletions(-)
 create mode 100644 tests/test_tool_show_step_checks.py
```

---

### 給 A12 的交代（很重要，別漏看）

A12 會把最後那個 `not_implemented` 佔位換成「畫箭頭 + 阻塞等待」。換掉之後，本篇有 **4 條測試會失敗**，因為它們斷言的就是那個佔位字串：

| 測試 | A12 要怎麼改 |
|---|---|
| `test_show_step_with_eleven_steps_passes_the_pre_checks` | 改成斷言 `result["error"] == ""` 且 `result["event"] == "timeout"`（它已經帶了 `timeout_s=0.2`，會等 0.2 秒就回來），並加上 `steps_shown == MAX_STEPS`（11 + 1） |
| `test_observe_with_expect_text_passes_the_pre_checks` | 同上：`error == ""`、`event == "timeout"` |
| `test_click_without_expect_text_passes_the_pre_checks` | 同上 |
| `test_uid_failure_lets_the_next_call_use_a_fresh_uid` | 最後那個 `retried["error"] == "not_implemented"` 改成 `retried["error"] == ""` |

這四條都已經帶了 `timeout_s=0.2`，所以 A12 之後就算忘了改，測試也只會**很快失敗**，不會把整個測試套件卡 120 秒。另外 11 條測試（六道檢查的失敗路徑）在 A12 之後必須**原封不動繼續綠**——它們就是 A12 不可以弄壞的護欄。

---

## 8. 驗收清單

- [ ] `uv run pytest tests/test_tool_show_step_checks.py -q` 是 15 passed。
- [ ] `uv run pytest -m "not browser" -q` 全綠（只有 A09 那一條 skip）。
- [ ] `show_step` 的六道檢查順序是：`session_not_found` → `show_step_in_progress` → `max_steps_exceeded` → `expect_text_required` → `uid_not_in_snapshot` → `normalize_timeout_s`。
- [ ] 六個失敗回傳都有完整的六個鍵；`signal` 是 `""`、`elapsed_s` 是 `0.0`、`next_action` 是 `""`。
- [ ] 只有 `uid_not_in_snapshot` 會附 `page`，而且那份 page 的 uid 世代比上一份大 1。
- [ ] 任何一道檢查被擋下時，`steps_shown` 沒有加、`state` 沒有變、`fake.calls` 裡沒有 `("show", ...)`。
- [ ] `steps_shown` 的判斷是 `>= MAX_STEPS`，而且 `MAX_STEPS` 是從 `showme.session` import 的常數，不是硬寫的 `12`。
- [ ] `kind` 有被 `normalize_kind()` 洗過，而且洗過的值蓋掉了原本的參數。
- [ ] `show_step` 目前**還沒有**呼叫 `browser.show()`、沒有動 `session.pending`、沒有把 state 設成 SHOWING（那是 A12）。
- [ ] `end_tutorial` 還是佔位。
- [ ] `tests/test_fakes.py` 末尾 parametrize 的 `show_step` 那一行已刪掉（剩 `end_tutorial` 一行，A13 再刪）。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `assert 'not_implemented' == 'session_not_found'` | 對應那一關還沒實作 | 照該 Step 的完整方法重貼 |
| 測試卡住不動、最後被 `Timeout >60.0s` 砍掉 | 你提前把 A12 的阻塞等待寫進來了 | 本篇的 `show_step` 不可以 `await` 任何 Future；把最後一行改回佔位 |
| `uid_not_in_snapshot` 的 page uid 還是 `s1-*` | 你回傳了 `session.latest_page` 而不是重拍 | 一定要 `page = await self._take_snapshot(session)` |
| `max_steps_exceeded` 在 11 步就出現 | 用了 `>` 寫成 `>=`，或反過來 | 規格是「`steps_shown >= 12` 時失敗」 |
| `kind="CLICK"` 被當成 observe 而要求 `expect_text` | `normalize_kind()` 沒有處理大小寫 | 回 A03 修純函數，不要在 `app.py` 補 `if kind.lower()` |
| `expect_text_missing()` 對 `kind="click"`、`expect_text=""` 回 `True` | 純函數寫錯 | 回 A03；`click` 不需要 `expect_text` |
| SHOWING 的測試把 state 改成 READY 了 | 你在 `show_step` 的失敗分支裡改了 state | 被擋下來的呼叫不可以有任何副作用 |
| `TypeError: show_step() takes ... positional arguments` | 參數順序打錯 | 順序是 `session_id, uid, instruction, kind, step_index, step_total, expect_text="", timeout_s=DEFAULT_TIMEOUT_S`，與 `server.py` 的 tool 簽名一致 |
| 編輯器提示 `timeout_s` 指派後未使用 | 正常，A12 會用到 | 不要為了消掉提示就刪掉那一行或亂加程式 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/features/顯示步驟.feature` | Rule：session 不存在時操作失敗且錯誤為 session_not_found（只有 `#TODO`） | `test_show_step_without_a_session_returns_session_not_found`、`test_show_step_with_an_unknown_session_id_returns_session_not_found`（測不變條件：`store.get()` 回 `None` 就是這個碼） |
| 同上 | Rule：僅在 session 狀態為 READY 時可成功畫出步驟（只有 `#TODO`） | `test_show_step_while_showing_returns_show_step_in_progress`（SHOWING 進不去畫的路徑） |
| 同上 | Rule：同一 session 並發的 show_step 被拒絕且錯誤為 show_step_in_progress（Example：正在等使用者時又畫下一步） | 同上；並額外驗「第一次繼續等」＝ state 不變、沒有 `show` 呼叫 |
| 同上 | Rule：steps_shown 大於等於 12 時操作失敗且錯誤為 max_steps_exceeded（Example：已畫滿 12 步） | `test_show_step_with_twelve_steps_returns_max_steps_exceeded`、`test_show_step_with_eleven_steps_passes_the_pre_checks` |
| 同上 | Rule：操作失敗時寫在回傳的 error，不丟例外（Example：已畫滿 12 步） | 六個失敗分支全部 `return dict`，沒有任何 `raise` |
| 同上 | Rule：kind 不屬於 click、input、select、observe 時視為 observe（Example：傳入 tap 且 expect_text 為空） | `test_unknown_kind_without_expect_text_returns_expect_text_required` |
| 同上 | Rule：kind 為 observe 且 expect_text 為空時操作失敗且錯誤為 expect_text_required（Example：等文字出現但沒帶文字） | `test_observe_without_expect_text_returns_expect_text_required`、`test_observe_with_expect_text_passes_the_pre_checks`、`test_click_without_expect_text_passes_the_pre_checks` |
| 同上 | Rule：uid 不在最新 snapshot 時操作失敗且錯誤為 uid_not_in_snapshot（只有 `#TODO`） | `test_stale_uid_returns_uid_not_in_snapshot_with_a_fresh_page`、`test_uid_with_an_unknown_index_returns_uid_not_in_snapshot` |
| 同上 | Rule：uid 不在最新 snapshot 時回傳新鮮 page 且 uid snapshot# 加一（只有 `#TODO`） | 上面兩條的 `s2-*` 斷言 + `snapshot_no == 2` + `test_uid_failure_lets_the_next_call_use_a_fresh_uid` |
| 同上 | Rule：uid 通過驗證並畫出後 steps_shown 加 1（本篇只驗「沒通過就不加」） | `test_uid_failure_does_not_draw_and_does_not_count`；「加 1」由 A12 負責 |
| 同上 | Rule：timeout_s 未傳或為 0 或負值時視為 120（Example：傳入 0） | 第六關呼叫 `normalize_timeout_s()`；純函數本身由 A03 的 `tests/test_rules.py` 驗，行為面由 A12 驗 |
| 同上 | Rule：畫出 overlay 後阻塞／畫出高亮與 popover／收到事件後回新 page／各 kind 的完成條件 | 不在本篇：A12（阻塞與狀態機）與 overlay B（完成觀察） |
| `docs/spec/.clarify/resolved/features/顯示步驟_kind不屬於四選一時是否操作失敗.md` | 答案 B：視為 observe，expect_text 空則 `expect_text_required` | 第四關的 `normalize_kind()` + `expect_text_missing()` |
| `docs/spec/.clarify/resolved/data/Step_kind為observe且expect_text為空時如何判定完成.md` | 答案 A：前置失敗，`expect_text_required` | 同上 |
| `docs/spec/.clarify/resolved/features/顯示步驟_並發show_step失敗時的錯誤碼為何.md` | 答案 A：`show_step_in_progress` | 第二關 |
| `docs/spec/.clarify/resolved/data/Step_timeout_s為0或負值時如何處理.md` | 答案 C：未傳、0 或負值改用預設 120 | 第六關（行為驗收在 A12） |
| `docs/spec/.clarify/resolved/data/PageElement_uid的snapshot編號何時遞增.md` | 答案 A：`show_step` 附 page 時（含 `uid_not_in_snapshot`）+1 | 第五關的 `_take_snapshot()` |
| `docs/spec/.clarify/resolved/data/Session_各狀態允許呼叫哪些MCP工具.md` | 答案 A：僅 READY 可 `show_step`；SHOWING 只等 | 第二關 |
| `docs/spec/erm.dbml` | `Step`（uid/instruction/kind/step_index/step_total/expect_text/timeout_s）與其跨屬性不變條件；`Session` 的 `max_steps = 12` | 方法簽名與六道檢查 |
| `docs/design/showme.md` §7.3 | 前置條件表、非法 kind、`expect_text` 空、`timeout_s` 正規化、uid 失敗仍附新鮮 page | 整篇 |
| `docs/design/showme.md` §13 | 六個錯誤碼；`timeout`／`stuck`／`step_done` 是 `event` 不是 error | 本篇只用其中五個錯誤碼，`event` 一律留空字串 |
| `docs/design/showme.md` §18 | 「非法 kind 視為 observe」「observe 且 expect_text 空」「並發 show_step」都標成 T／S 層（Python） | 全部寫在 `app.py`，overlay 不處理 |
