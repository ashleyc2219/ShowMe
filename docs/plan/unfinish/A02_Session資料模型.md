# A02｜Session 資料模型

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：[A01_環境建置與骨架確認.md](A01_環境建置與骨架確認.md)　｜　下一篇：[A03_純函數規則.md](A03_純函數規則.md)
> 對應設計：`docs/design/showme.md` §8（Session 狀態機）、§9（資料模型）　｜　對應切片：無（是 S5～S8 的地基）
> 預估時間：30 分鐘

---

## 1. 這一篇要做什麼

寫出 `showme/session.py`：一個 `Session` dataclass（記著這場教學的 id、目標、狀態、畫了幾步、拍到第幾張、最新那張 page、正在等的信箱）、一個只裝得下一個 Session 的 `SessionStore`，以及四個全專案共用的常數。**完全是純 Python**——不開瀏覽器、不碰 asyncio 的事件迴圈、不做任何 I/O，所以它是整套裡最好測的一塊，也是你第一次跑完整 TDD 循環的地方。

---

## 2. 做完會看到什麼

### 2.1 這一篇造出來的東西

```text
                    SessionStore（同一個 process 只有一個）
                    ┌──────────────────────────────────┐
                    │  _session: Session | None        │
                    │                                   │
                    │  current() → Session | None       │
                    │  get(session_id) → Session | None │
                    │  create(goal) → Session           │
                    │  delete() → None                  │
                    └───────────────┬──────────────────┘
                                    │ 最多裝一個
                                    ▼
                    ┌──────────────────────────────────────────────┐
                    │ Session                                       │
                    │  session_id  "s_8f2a"      ← new_session_id() │
                    │  goal        "create a project"（可為空字串） │
                    │  state       READY / SHOWING                  │
                    │  steps_shown 0…12                             │
                    │  snapshot_no 0 → 1 → 2 …（uid 的世代號）      │
                    │  latest_page {"url","title","elements",       │
                    │               "truncated"} 或 None            │
                    │  pending     asyncio.Future 或 None           │
                    │                                               │
                    │  uids() → {"s1-4", "s1-7", …}                 │
                    └──────────────────────────────────────────────┘
```

### 2.2 每個欄位是誰在什麼時候改的（後面幾篇的預告）

```text
時間 ──────────────────────────────────────────────────────────────────▶

start_tutorial 成功   show_step 畫出      收到 emit / timeout     end_tutorial 成功
        │                   │                     │                      │
 create(goal) 或覆蓋        │                     │                      │
 state    = READY     state = SHOWING       state = READY           store.delete()
 steps_shown = 0      steps_shown += 1      pending = None          （整個物件消失）
 snapshot_no: 0→1     pending = Future      snapshot_no += 1
 latest_page = 新的                          latest_page = 新的

（A02 只負責「這些欄位存在、預設值正確、store 一次只裝一個」；
  誰在什麼時候改它們，是 A08～A13 的事。）
```

### 2.3 檔案樹

```text
hackathonQoder/
├── showme/
│   ├── __init__.py
│   ├── __main__.py
│   ├── server.py
│   └── session.py        ← 這一篇新增
└── tests/
    ├── conftest.py
    ├── test_smoke.py
    └── test_session.py   ← 這一篇新增
```

---

## 3. 開始前先確認

- [ ] A01 的驗收清單全部打勾。
- [ ] `uv run pytest` 現在是 `2 passed`。
- [ ] `git status --short` 是空的。
- [ ] 你知道規格說的三件事：**同一個 process 至多一個 Session**、**沒有 ttl（不會過期）**、**`end_tutorial` 成功後 Session 被刪掉（沒有 DONE 狀態）**。
- [ ] 這一篇不需要瀏覽器、不需要網路。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| **dataclass** | Python 內建的「資料容器」寫法。在 class 上面加 `@dataclass`，然後只列欄位名與型別，Python 就自動幫你生 `__init__`、`__repr__`、`__eq__`。 |
| **`from __future__ import annotations`** | 放在檔案最上面的一行。它讓所有型別註記變成「先當字串存著、需要時才解析」，好處是可以寫 `dict \| None` 這種新語法而不用擔心相容性，也不會因為註記而產生 import 循環。 |
| **`Enum`** | 列舉：把有限的幾個值變成具名常數，避免打錯字。`State.READY` 打錯會立刻 `AttributeError`，字串 `"REDAY"` 則會安靜地錯下去。 |
| **`class State(str, Enum)`** | 同時是字串也是列舉。好處：`State.READY == "READY"` 是 `True`，而且 `json` 序列化時會變成 `"READY"`。 |
| **`is` vs `==`** | `is` 問「是不是同一個物件」，`==` 問「內容一不一樣」。測試裡我們用 `store.current() is session` 來確認**沒有偷偷複製一份**。 |
| **`secrets.token_hex(2)`** | 產生 2 個位元組的亂數，轉成 **4 個十六進位字元**的字串，例如 `"8f2a"`。用 `secrets` 而不是 `random`，是因為它是標準函式庫裡「拿來當識別碼」的正規做法。 |
| **`asyncio.Future`** | 「一個之後才會有答案的信箱」。`show_step` 會建一個放進 `session.pending`，然後睡著等；overlay 送事件進來時，另一段程式把答案放進去，睡著的人就醒來。**這一篇只是留一個欄位放它，還不會真的用。** |
| **`set`（集合）** | 不重複、沒順序的一堆值。`session.uids()` 回一個 set，因為我們只想問「這個 uid 在不在裡面」。 |
| **`Session \| None`** | 「可能是 Session，也可能是 None」。這是型別註記的寫法，Python 3.10 之後可以用 `\|`。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 新增 | `showme/session.py` | Session dataclass、State 列舉、SessionStore、`new_session_id()`、四個共用常數 |
| 新增 | `tests/test_session.py` | 上面每個行為的測試（19 條） |
| 不動 | `showme/server.py`、`showme/__main__.py` | A07 才會改 `server.py` |

---

## 6. 介面約定

### 6.1 用到（來自前面幾篇）

只用 Python 標準函式庫（`asyncio`、`secrets`、`dataclasses`、`enum`）。這個模組**不 import 專案裡任何其他模組**，也不該被任何人加上這種 import——它是最底層。

### 6.2 提供（給後面幾篇）

```python
MAX_STEPS = 12
DEFAULT_TIMEOUT_S = 120.0
DONE_BANNER_TEXT = "✅ Done — you created a project"
START_NEXT_ACTION = (
    "Plan 3–8 steps in your head, then call show_step for the FIRST step "
    "using a uid from page.elements."
)
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
    snapshot_no: int = 0                   # 目前最新 snapshot 的世代；start 成功後為 1
    latest_page: dict | None = None        # {"url","title","elements":[...],"truncated"}
    pending: asyncio.Future | None = None   # SHOWING 時等待 emit 的 future

    def uids(self) -> set[str]: ...


def new_session_id() -> str: ...            # "s_" + 4 個 hex，例如 "s_8f2a"


class SessionStore:
    def __init__(self) -> None: ...
    def current(self) -> Session | None: ...
    def get(self, session_id: str) -> Session | None: ...
    def create(self, goal: str) -> Session: ...
    def delete(self) -> None: ...
```

誰會用到它們：

| 使用者 | 用來做什麼 |
|---|---|
| A07 `showme/app.py` | `self.store = SessionStore()`；每個 tool 開頭 `store.get(session_id)` |
| A08/A09 `start_tutorial` | `store.create(goal)` 或就地覆寫欄位 |
| A11 `show_step` 前置檢查 | `MAX_STEPS`、`session.state`、`session.latest_page` |
| A12 `show_step` 等待 | `State.SHOWING`、`session.pending`、`DEFAULT_TIMEOUT_S`、`STEP_NEXT_ACTION` |
| A13 `end_tutorial` | `DONE_BANNER_TEXT`、`store.delete()` |
| A03 `tests/test_rules.py` | 借 `DEFAULT_TIMEOUT_S` 來確認 `rules.py` 的預設值沒有走鐘 |

### 6.3 規格上不能寫錯的細節

| 細節 | 來源 |
|---|---|
| `max_steps = 12`、預設 `timeout_s = 120` | `docs/spec/erm.dbml`（Session Note：「硬限制（常數，非欄位）：max_steps = 12、step_timeout = 120 s」） |
| banner 文案就是 `✅ Done — you created a project`（**em dash `—`，不是減號**） | `docs/spec/features/結束教學.feature` |
| 只有 READY 與 SHOWING 兩個實務狀態；「IDLE」＝根本沒有 Session；**沒有 DONE** | `docs/design/showme.md` §8 + clarified：`結束教學_釋放後該session_id再呼叫要如何回應.md` |
| `session_id` 形如 `s_8f2a`；產生演算法不鎖定 | `docs/design/showme.md` §5（design：「固定前綴 + 短 hex」） |
| `goal` 可以是空字串，不 trim、不失敗 | clarified：`開始教學_goal為空字串時是否操作失敗.md` |
| 同一 process 至多一個 Session；再次 start 覆蓋、id 不變 | clarified：`Session_既有進行中場次時再次start_tutorial要新建還是重用.md` |
| 沒有 ttl | clarified：`Session_session_ttl到期時進行中的等待如何結束.md`（回答是「不要這個限制」） |

---

## 7. 步驟

這一篇跑**兩輪** TDD：第一輪做常數與 `Session` 本身，第二輪做 `SessionStore`。每輪都是「寫測試 → 看紅 → 寫實作 → 看綠」。

### Step 1：寫第一批測試（會紅）

新增檔案 `tests/test_session.py`，內容完整如下：

```python
"""showme/session.py 的行為測試。

純 Python：不開瀏覽器、不需要 asyncio 事件迴圈，所以全部是普通的 def。
"""

import re

from showme.session import (
    DEFAULT_TIMEOUT_S,
    DONE_BANNER_TEXT,
    MAX_STEPS,
    START_NEXT_ACTION,
    STEP_NEXT_ACTION,
    Session,
    State,
    new_session_id,
)


# --- 常數 -----------------------------------------------------------------


def test_constants_match_the_spec_numbers():
    # erm.dbml（Session Note）：硬限制 max_steps = 12、step_timeout = 120 s
    assert MAX_STEPS == 12
    assert DEFAULT_TIMEOUT_S == 120.0


def test_done_banner_text_is_the_fixed_sentence():
    # 結束教學.feature：「成功結束後顯示完成 banner，文案固定且忽略 summary」
    # 中間是 em dash（—），不是減號，也不是 en dash
    assert DONE_BANNER_TEXT == "✅ Done — you created a project"


def test_next_action_hints_point_at_the_right_next_tool():
    # design §5：next_action 沿用 draft 的舉例字串，不是 .feature 的驗收字，
    # 所以這裡只確認它有把 agent 指去正確的下一個動作。
    assert "show_step" in START_NEXT_ACTION
    assert "page.elements" in START_NEXT_ACTION
    assert "show_step" in STEP_NEXT_ACTION
    assert "end_tutorial" in STEP_NEXT_ACTION


# --- session_id -----------------------------------------------------------


def test_new_session_id_looks_like_the_spec_example():
    # 規格舉例是 s_8f2a：前綴 s_ 加 4 個小寫十六進位字元
    assert re.fullmatch(r"s_[0-9a-f]{4}", new_session_id())


def test_new_session_id_is_not_always_the_same():
    # 每次都一樣的話，「end 之後再 start 拿到新場次」就沒有意義了
    assert len({new_session_id() for _ in range(20)}) > 1


# --- Session 本身 ---------------------------------------------------------


def test_state_has_exactly_the_two_runtime_states():
    # design §8：實務狀態只有 READY 與 SHOWING。
    # erm 的 IDLE 是「沒有 Session 物件」，end_tutorial 之後也不留 DONE。
    assert [state.value for state in State] == ["READY", "SHOWING"]
    assert State.READY == "READY"  # str Enum 可以直接跟字串比


def test_new_session_starts_ready_with_zero_counters():
    # 開始教學.feature：「成功開始後 session 狀態為 READY」、steps_shown 為 0
    session = Session(session_id="s_8f2a", goal="create a project")

    assert session.session_id == "s_8f2a"
    assert session.goal == "create a project"
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 0  # 還沒拍過任何 snapshot；start 成功後才變 1
    assert session.latest_page is None
    assert session.pending is None


def test_uids_is_empty_when_there_is_no_page_yet():
    session = Session(session_id="s_8f2a", goal="")

    assert session.uids() == set()


def test_uids_lists_every_uid_in_the_latest_page():
    # show_step 就是拿這個集合來判斷 uid_not_in_snapshot
    session = Session(session_id="s_8f2a", goal="")
    session.latest_page = {
        "url": "http://localhost:3000/",
        "title": "Dashboard",
        "elements": [
            {"uid": "s1-4", "role": "button", "name": "New Project", "testid": "new-project"},
            {"uid": "s1-7", "role": "link", "name": "Settings", "testid": ""},
        ],
        "truncated": False,
    }

    assert session.uids() == {"s1-4", "s1-7"}


def test_uids_ignores_an_element_without_a_uid():
    # build_page（A03）遇到沒有 uid 的元素不會補一個假的，這裡不能因此爆掉
    session = Session(session_id="s_8f2a", goal="")
    session.latest_page = {
        "url": "http://localhost:3000/",
        "title": "Dashboard",
        "elements": [
            {"role": "button", "name": "Mystery", "testid": ""},
            {"uid": "s1-2", "role": "button", "name": "New Project", "testid": ""},
        ],
        "truncated": False,
    }

    assert session.uids() == {"s1-2"}
```

### Step 2：跑一次，看它紅

```bash
uv run pytest tests/test_session.py
```

預期輸出（重點在最後那幾行）：

```text
==================================== ERRORS ====================================
_____________________ ERROR collecting tests/test_session.py ___________________
ImportError while importing test module '/Users/linjunting/hackathonQoder/tests/test_session.py'.
Hint: make sure your test module/package has valid Python names.
Traceback:
tests/test_session.py:7: in <module>
    from showme.session import (
E   ModuleNotFoundError: No module named 'showme.session'
=========================== short test summary info ============================
ERROR tests/test_session.py
!!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

**這就是預期中的紅燈**：測試想 import 一個還不存在的模組。看到 `ModuleNotFoundError: No module named 'showme.session'` 才往下走；看到別的錯誤（例如 `No module named 'showme'`），代表 A01 的 `uv sync` 沒把專案裝進去，先回去修。

### Step 3：寫最小實作，讓它變綠

新增檔案 `showme/session.py`，內容完整如下：

```python
"""教學場次（Session）的資料模型與存放處。

規格重點（docs/spec/erm.dbml、docs/design/showme.md §8）：
- 同一個 process 同時只有一個 Session，存在記憶體裡，不是資料庫。
- 沒有 ttl：場次不會自己過期。
- end_tutorial 成功後直接刪除 Session，不保留 DONE 狀態。

這個模組是整包最底層：不 import 專案內其他模組、不做 I/O、不碰瀏覽器。
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from enum import Enum

# 一場教學最多畫幾步（erm.dbml：max_steps = 12）
MAX_STEPS = 12

# show_step 沒給 timeout_s（或給 0、負值）時用的秒數（erm.dbml：step_timeout = 120 s）
DEFAULT_TIMEOUT_S = 120.0

# end_tutorial 的完成橫幅，文案固定、忽略 summary（結束教學.feature）
DONE_BANNER_TEXT = "✅ Done — you created a project"

# 回給 agent 的下一步提示（design §5：沿用 draft 舉例字串，不是驗收字）
START_NEXT_ACTION = (
    "Plan 3–8 steps in your head, then call show_step for the FIRST step "
    "using a uid from page.elements."
)
STEP_NEXT_ACTION = (
    "If the goal is not yet achieved, call show_step for the next step using a uid "
    "from page.elements. If the page shows the goal is achieved, call end_tutorial."
)


class State(str, Enum):
    """場次的實務狀態。

    只有兩個：READY（可以 inspect / show / end）與 SHOWING（正在等使用者）。
    erm 裡的 IDLE 代表「根本沒有 Session 物件」，不是這裡的一個值；
    也沒有 DONE——end_tutorial 成功後 Session 直接被刪掉。
    """

    READY = "READY"
    SHOWING = "SHOWING"


@dataclass
class Session:
    """一場教學。欄位對應 erm.dbml 的 Session 表，外加三個實作用的握把。"""

    session_id: str
    goal: str
    state: State = State.READY
    steps_shown: int = 0
    # 目前最新 snapshot 的世代號。start_tutorial 成功後是 1，之後每拍一次 +1。
    snapshot_no: int = 0
    # 最新那份濃縮 page：{"url", "title", "elements": [...], "truncated"}
    latest_page: dict | None = None
    # SHOWING 時等待 overlay 事件的信箱；不在等待時是 None。
    pending: asyncio.Future | None = None

    def uids(self) -> set[str]:
        """最新 page 裡所有 uid；還沒拍過 page 時是空集合。

        show_step 用它判斷 agent 給的 uid 是不是還活著（不是陳舊世代的）。
        """
        if self.latest_page is None:
            return set()
        return {
            element["uid"]
            for element in self.latest_page.get("elements", [])
            if "uid" in element
        }


def new_session_id() -> str:
    """產生一個場次識別，形如 s_8f2a（前綴 s_ 加 4 個十六進位字元）。

    design §5：沿用規格舉例的長相，演算法不鎖定。
    """
    return "s_" + secrets.token_hex(2)


class SessionStore:
    """同一 process 至多一個 Session 的存放處。

    刻意不用 dict：規格說「同一時間只允許一個教學場次」，
    用 dict 會讓「不小心存了兩個」變成可能。
    """

    def __init__(self) -> None:
        self._session: Session | None = None

    def current(self) -> Session | None:
        """目前這場（沒有就是 None）。"""
        return self._session

    def get(self, session_id: str) -> Session | None:
        """依 id 取場次。沒有 Session、或 id 對不上，都回 None。

        呼叫端拿到 None 就回 error="session_not_found"。
        """
        session = self._session
        if session is None or session.session_id != session_id:
            return None
        return session

    def create(self, goal: str) -> Session:
        """建立新場次（新 id、READY、steps_shown=0、snapshot_no=0）並取代舊的。"""
        self._session = Session(session_id=new_session_id(), goal=goal)
        return self._session

    def delete(self) -> None:
        """刪掉場次。之後任何 inspect / show / end 都會是 session_not_found。"""
        self._session = None
```

### Step 4：跑一次，看它綠

```bash
uv run pytest tests/test_session.py
```

預期輸出：

```text
========================= test session starts =========================
collected 10 items

tests/test_session.py ..........                                [100%]

========================= 10 passed in 0.04s ==========================
```

沒綠的話對照第 9 節的排錯表。

### Step 5：第二輪——寫 SessionStore 的測試（會紅）

在 `tests/test_session.py` 的 **import 區塊**加上 `SessionStore`（把原本的 import 改成下面這樣）：

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
    new_session_id,
)
```

然後在 `tests/test_session.py` **檔案最後面**加上這一段：

```python
# --- SessionStore ---------------------------------------------------------


def test_store_is_empty_before_create():
    # erm：「IDLE」＝沒有 Session 物件。此時任何 tool 都會是 session_not_found。
    store = SessionStore()

    assert store.current() is None
    assert store.get("s_8f2a") is None


def test_create_returns_a_ready_session_that_becomes_the_current_one():
    # 開始教學.feature：「成功開始後 session 狀態為 READY」
    store = SessionStore()

    session = store.create("create a project")

    assert store.current() is session  # 就是同一個物件，沒有偷偷複製
    assert session.goal == "create a project"
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 0


def test_create_accepts_an_empty_goal():
    # clarified（開始教學_goal為空字串時是否操作失敗）：允許空 goal，不 trim、不失敗
    store = SessionStore()

    session = store.create("")

    assert session.goal == ""
    assert session.state is State.READY


def test_create_replaces_the_previous_session():
    # clarified（Session_既有進行中場次…）：同一 process 只允許一個 Session。
    # 注意：真正的 start_tutorial 覆蓋是「沿用同一個 session_id」（A09 處理），
    # store.create() 則是「從無到有」用的，它一定會換掉舊的那個。
    store = SessionStore()
    first = store.create("create a project")

    second = store.create("invite a member")

    assert store.current() is second
    assert store.get(first.session_id) is None


def test_get_returns_the_session_when_the_id_matches():
    store = SessionStore()
    session = store.create("create a project")

    assert store.get(session.session_id) is session


def test_get_returns_none_when_the_id_does_not_match():
    # 檢查頁面.feature / 結束教學.feature：用假的場次識別 → session_not_found
    store = SessionStore()
    store.create("create a project")

    assert store.get("s_missing") is None


def test_delete_removes_the_session():
    # 結束教學.feature：「成功結束後刪除 Session」；再呼叫一次要 session_not_found
    store = SessionStore()
    session = store.create("create a project")

    store.delete()

    assert store.current() is None
    assert store.get(session.session_id) is None


def test_delete_is_safe_when_there_is_no_session():
    # end_tutorial 失敗路徑不該因為「刪一個不存在的東西」而爆炸
    store = SessionStore()

    store.delete()

    assert store.current() is None


def test_create_after_delete_makes_a_brand_new_session():
    # 結束教學之後再 start_tutorial：Session 已刪除 → 新建（erm Session Note）
    store = SessionStore()
    store.create("create a project")
    store.delete()

    fresh = store.create("create a project")

    assert store.current() is fresh
    assert fresh.state is State.READY
    assert fresh.steps_shown == 0
```

跑一次：

```bash
uv run pytest tests/test_session.py
```

> **這一輪你可能看不到紅燈。** 因為 Step 3 已經把 `SessionStore` 一起寫進去了，所以會直接 `19 passed`。這是刻意的：`SessionStore` 只有 20 行，硬要拆成兩次貼檔反而更容易貼錯。
>
> 想真的看一次紅燈的話，把 `showme/session.py` 裡 `SessionStore.get` 的
> `if session is None or session.session_id != session_id:`
> 暫時改成 `if session is None:`，再跑一次——你會看到
> `test_get_returns_none_when_the_id_does_not_match` 失敗：
>
> ```text
> E       assert <showme.session.Session object at 0x...> is None
> ```
>
> 看到以後**記得改回來**。這一步是在確認「id 對不上要回 None」這條真的有被測到。

### Step 6：全部跑一次

```bash
uv run pytest
```

預期輸出：

```text
collected 21 items

tests/test_session.py ...................                       [ 90%]
tests/test_smoke.py ..                                          [100%]

========================= 21 passed in 0.42s ==========================
```

（`21 = 19 + 2`：A02 的 19 條加上 A01 的 2 條。）

### Step 7：commit

```bash
git add tests/test_session.py
git commit -m "test: add session model and store behaviour tests"

git add showme/session.py
git commit -m "feat: add Session dataclass, State enum and SessionStore"
```

確認乾淨：

```bash
git status --short
```

預期輸出：空白。

---

## 8. 驗收清單

- [ ] `showme/session.py` 存在，而且**沒有** import 專案裡其他模組（只有 `asyncio`、`secrets`、`dataclasses`、`enum`）。
- [ ] `uv run pytest tests/test_session.py` 顯示 `19 passed`。
- [ ] `uv run pytest` 全部顯示 `21 passed`。
- [ ] Step 2 有看到 `ModuleNotFoundError: No module named 'showme.session'` 的紅燈。
- [ ] `DONE_BANNER_TEXT` 的中間是 em dash `—`（可用 `uv run python -c "from showme.session import DONE_BANNER_TEXT; print(DONE_BANNER_TEXT)"` 目視確認，輸出要是 `✅ Done — you created a project`）。
- [ ] `State` 只有 READY 與 SHOWING，**沒有** IDLE、**沒有** DONE。
- [ ] `SessionStore` 內部是一個 `Session | None`，不是 dict／list。
- [ ] 兩個 commit 都在，`git status --short` 是空的。
- [ ] `overlay/` 一個字都沒改。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `ModuleNotFoundError: No module named 'showme.session'` 在 Step 4 之後還出現 | 檔案放錯位置或檔名打錯 | 必須是 `showme/session.py`（`ls showme/` 確認），不是 `sessions.py`、不是根目錄 |
| `ModuleNotFoundError: No module named 'showme'` | A01 的 `uv sync` 沒把專案裝進 venv | 重跑 `uv sync`，確認輸出有 `+ showme==0.1.0 (from file:///...)` |
| `test_done_banner_text_is_the_fixed_sentence` 紅，訊息看起來兩個字串一模一樣 | 破折號打成減號 `-` 或 en dash `–` | 直接從 `docs/spec/features/結束教學.feature` 複製那一行貼過來 |
| `test_new_session_id_looks_like_the_spec_example` 紅 | 用了 `token_hex(4)`（會給 8 個字元）或 `uuid4()` | 要 `secrets.token_hex(2)`：2 個位元組 = 4 個十六進位字元 |
| `TypeError: non-default argument 'goal' follows default argument` | dataclass 的欄位順序被調動 | 沒有預設值的欄位（`session_id`、`goal`）一定要排在有預設值的前面 |
| `ValueError: mutable default <class 'dict'> for field latest_page` | 把預設值寫成 `{}` 或 `[]` | 預設值必須是 `None`；dataclass 不允許可變預設值 |
| `test_uids_lists_every_uid_in_the_latest_page` 噴 `KeyError: 'uid'` | `uids()` 直接用 `element["uid"]` | 照 Step 3 的寫法先 `if "uid" in element` 過濾 |
| `test_create_replaces_the_previous_session` 紅 | `create()` 沒有覆寫 `self._session` | `create()` 一定要 `self._session = Session(...)` 再 return |
| 想加一個 `SessionStore.update()` / `save()` | 目前用不到 | 不要加。A08～A13 都是直接改 `session.xxx` 欄位；多一個方法只是多一個要維護的接縫 |
| 想把 `state` 存成字串 `"READY"` | 會打錯字而且不會被發現 | 用 `State.READY`。因為是 `str, Enum`，需要字串的地方它自己就是字串 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/erm.dbml` Table `Session` | `session_id` / `goal` / `state` / `steps_shown` 四個欄位 | `Session` dataclass 的前四個欄位，型別與預設值一致 |
| `docs/spec/erm.dbml` Session Note | 「硬限制（常數，非欄位）：max_steps = 12、step_timeout = 120 s」 | `MAX_STEPS = 12`、`DEFAULT_TIMEOUT_S = 120.0`＋`test_constants_match_the_spec_numbers` |
| `docs/spec/erm.dbml` Session Note | 「同一 process 只允許一個 Session」 | `SessionStore` 內部只有一個 `Session \| None`＋`test_create_replaces_the_previous_session` |
| `docs/spec/erm.dbml` Session Note | 「Session 已刪除後再 start_tutorial：新建 Session」 | `test_create_after_delete_makes_a_brand_new_session` |
| `docs/spec/erm.dbml` Session／Page 關聯 | 「Session 1:1 最新 Page（latest_snapshot）」「進行中 wait Future」「snapshot# 計數」 | `latest_page`、`pending`、`snapshot_no` 三個欄位 |
| `docs/spec/features/開始教學.feature` | Rule：「成功開始後 session 狀態為 READY」 | `Session.state` 預設 `State.READY`＋`test_new_session_starts_ready_with_zero_counters` |
| `docs/spec/features/開始教學.feature` | Rule：「goal 為空字串時仍成功開始」 | `test_create_accepts_an_empty_goal` |
| `docs/spec/features/結束教學.feature` | Rule：「成功結束後顯示完成 banner，文案固定且忽略 summary」 | `DONE_BANNER_TEXT`＋`test_done_banner_text_is_the_fixed_sentence`（真正呼叫在 A13） |
| `docs/spec/features/結束教學.feature` | Rule：「成功結束後刪除 Session」 | `SessionStore.delete()`＋`test_delete_removes_the_session` |
| `docs/spec/features/檢查頁面.feature` | Rule：「session 不存在時操作失敗且錯誤為 session_not_found」的 Example（`s_missing`） | `SessionStore.get()` 回 None＋`test_get_returns_none_when_the_id_does_not_match`（錯誤碼組裝在 A10） |
| clarified `Session_session_ttl到期時進行中的等待如何結束.md` | 回答：「不要這個限制」 | `Session` **沒有** ttl／到期時間欄位 |
| clarified `Session_各狀態允許呼叫哪些MCP工具.md` | 回答 A：嚴格依狀態機；僅 READY 可 show/inspect/end | `State` 只有 READY／SHOWING（誰能呼叫的判斷在 A10～A13） |
| clarified `Session_既有進行中場次時再次start_tutorial要新建還是重用.md` | 回答 B：覆蓋、`session_id` 不變 | `SessionStore` 一次只裝一個（覆蓋邏輯在 A09） |
| clarified `結束教學_釋放後該session_id再呼叫要如何回應.md` | 回答 A：刪除 Session、不保留 DONE | `State` 沒有 DONE；`delete()` 之後 `get()` 一律 None |
| `docs/design/showme.md` §5 | design：「`session_id` 沿用規格舉例形如 `s_8f2a`；產生演算法不鎖定」 | `new_session_id()`＋`test_new_session_id_looks_like_the_spec_example` |
| `docs/design/showme.md` §8 | 狀態機與常數 | `State` 列舉＋`test_state_has_exactly_the_two_runtime_states` |
| `docs/design/showme.md` §9 | 「ShowMe process 內一個 `Session` dataclass 即可」「Page / PageElement → `latest_page` dict，只留最新一份」 | 本篇的整個資料模型 |

---

**下一篇：[A03_純函數規則.md](A03_純函數規則.md)** — 把「timeout 怎麼正規化、kind 怎麼算 observe、150 怎麼截斷」這些規則寫成一堆不碰任何狀態的小函數。
