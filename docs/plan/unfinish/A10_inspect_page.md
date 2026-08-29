# A10｜inspect_page（重拍，不畫）

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：`A09_start_tutorial覆蓋場次.md` ｜ 下一篇：`A11_show_step前置檢查.md`
> 對應設計：`docs/design/showme.md` §6（inspect 的用途）、§7.2（tool 契約）、§10（snapshot 與 uid）、§13（錯誤語意）、§17 open question 1 ｜ 對應切片：S6
> 預估時間：30–40 分鐘

---

## 1. 這一篇要做什麼

把 `ShowMeApp.inspect_page()` 從佔位改成真的：**確認場次存在且是 READY → 重拍一份新鮮的濃縮 page（snapshot# +1）→ 回傳**。

`inspect_page` 是四個 tool 裡最單純的一個，只有三條路，而且**絕對不能畫任何東西**（不呼叫 `browser.show()`）。它存在的理由是：agent 手上的 uid 過期了（`uid_not_in_snapshot`），或使用者自己在畫面上亂點導致頁面變了，agent 需要「再看一眼」。

---

## 2. 做完會看到什麼

### 2.1 snapshot# 時間軸（本篇負責哪一格）

```text
 時間 ────────────────────────────────────────────────────────────────▶

 呼叫       start_tutorial   inspect_page   inspect_page   show_step(回傳時)   show_step(uid 失敗)
 snapshot_no      1               2              3                4                  5
 uid 前綴        s1-             s2-            s3-              s4-                s5-
                                  ▲              ▲
                                  └──────────────┴── 這兩格是本篇負責的
                                                                  ▲                  ▲
                                                                  └──────────────────┴── A11／A12 負責

 規則：只要「產生了一份新的 elements 清單」，snapshot# 就 +1。
      舊世代的 uid 因此必然不在最新清單裡 → show_step 會回 uid_not_in_snapshot。
```

### 2.2 三條路（`inspect_page` 的全部行為）

```text
inspect_page(session_id)
   │
   ├─(1) store.get(session_id) is None ─────▶ {"page": None, "error": "session_not_found"}
   │        （沒有場次，或 id 對不上）              不碰瀏覽器、snapshot_no 不變
   │
   ├─(2) session.state is SHOWING ──────────▶ {"page": None, "error": "show_step_in_progress"}
   │        （OQ1：A 的設計決定，可改）              不碰瀏覽器、snapshot_no 不變
   │
   └─(3) 否則 _take_snapshot(session) ───────▶ {"page": {...}, "error": ""}
            snapshot_no += 1                    calls 多一筆 ("snapshot", n)
            latest_page 換成新的                 calls 裡永遠不會有 ("show", ...)
```

---

## 3. 開始前先確認

- [ ] A08、A09 的驗收都打勾了。
- [ ] `uv run pytest tests/test_tool_start.py -q` 是 `20 passed, 1 skipped`。
- [ ] `uv run pytest -m "not browser" -q` 全綠。
- [ ] `showme/app.py` 的 `start_tutorial` 已經完成（新建 + 覆蓋 + `navigation_failed`），`inspect_page`／`show_step`／`end_tutorial` 還是 `return {"error": "not_implemented"}`。
- [ ] `showme/session.py` 有 `State.READY`／`State.SHOWING` 與 `SessionStore.get()`。
- [ ] `showme/rules.py` 的 `build_page()` 會套 150 上限並算出 `truncated`。
- [ ] `tests/conftest.py` 有 `fake_browser`、`app`、`started` 三個 fixture。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| 新鮮的 page | 「現在這一刻」重新掃出來的元素清單。跟上一份可能一模一樣，但 uid 的世代編號一定不同。 |
| snapshot# | 世代編號，寫在 uid 前綴。第 2 次拍的清單 uid 都是 `s2-*`。它讓「舊 uid」自動失效，不需要另外做過期時間。 |
| `truncated` | 這一頁符合條件的元素超過 150 個，被砍掉後面那些了。`true` 的時候 agent 知道「我看到的不是全部」。 |
| `store.get(session_id)` | 用 id 去抽屜拿場次。沒有場次、或 id 跟現在這場不一樣，都回 `None`（所以假 id 跟沒有場次是同一個錯誤碼）。 |
| OQ1 | design §17 的第 1 個 open question：「SHOWING 時 `inspect_page`／`end_tutorial` 的 error 字串是什麼」。已定案的六個錯誤碼裡沒有 `not_ready`，所以 A 決定沿用 `show_step_in_progress`，**不新增錯誤碼**。**可改**。 |
| `is` 與 `==` | 比 Enum 用 `is`（`session.state is State.SHOWING`）比較安全，因為 Enum 成員是單一物件。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 修改 | `showme/app.py` | 只改 `ShowMeApp.inspect_page()`。其他方法一律不動。 |
| 新增 | `tests/test_tool_inspect.py` | `inspect_page` 的行為測試（不開瀏覽器）。 |

---

## 6. 介面約定

### 6.1 用到（重述精確簽名）

```python
# showme/session.py
class State(str, Enum):
    READY = "READY"
    SHOWING = "SHOWING"

class SessionStore:
    def current(self) -> Session | None: ...
    def get(self, session_id: str) -> Session | None:
        """沒有 Session、或 id 對不上 → None。"""

# showme/app.py（A07 已完成）
async def _take_snapshot(self, session: Session) -> dict:
    """session.snapshot_no += 1
       → raw = browser.snapshot(session.snapshot_no)
       → page = build_page(raw, url, title)
       → session.latest_page = page
       → return page"""
```

`_take_snapshot()` 需要一個可用的瀏覽器。A07 的版本是在裡面自己取得瀏覽器（`browser = await self._ensure_browser()`）；如果你的版本是直接用 `self._browser`，本篇的測試一樣會過——因為能走到 `_take_snapshot()` 就代表 `start_tutorial` 已經成功過，瀏覽器一定存在。**不要為了這篇去改 `_take_snapshot()`。**

```python
# showme/rules.py
def build_page(raw: dict, url: str, title: str) -> dict:
    """回 {"url": url, "title": title, "elements": [...], "truncated": bool}
       - 每個 element 只留 uid/role/name/testid 四個鍵，缺的補 ""
       - 超過 150 → 只留前 150
       - truncated = bool(raw.get("truncated")) or len(raw elements) > 150"""

# tests/fakes.py
class FakeBrowser:
    calls: list[tuple]
    def add_page(self, url: str, title: str, elements: list[dict], truncated: bool = False) -> None: ...
    def navigate(self, url: str) -> None:
        """模擬使用者自己點一點換了頁；只改 self.url，不記進 calls。"""
    async def snapshot(self, n: int) -> dict:
        """記 ("snapshot", n)，並把該頁 elements 依 n 重新編號成 s{n}-{i+1}。"""
```

### 6.2 提供（給後面幾篇）

```python
async def inspect_page(self, session_id: str) -> dict
# 成功：{"page": {...}, "error": ""}
# 失敗：{"page": None,  "error": "session_not_found"}        沒有場次或 id 對不上
#      {"page": None,  "error": "show_step_in_progress"}    state 是 SHOWING（OQ1，可改）
```

A13（`end_tutorial`）會用同一組前置檢查（`get()` → `None` 就 `session_not_found`；SHOWING 就 `show_step_in_progress`），A14 的 MCP 契約測試會用「假 session_id 呼叫 `inspect_page`」來驗證「失敗不會變成 `is_error`」。

---

## 7. 步驟

### Step 1：建立測試檔，寫沒有場次的兩條（先看它紅）

建立 `tests/test_tool_inspect.py`，內容如下（整檔貼上）：

```python
"""inspect_page 的行為測試。全部用 FakeBrowser，不開瀏覽器。"""

from __future__ import annotations

import pytest

from showme.session import State

pytestmark = pytest.mark.anyio

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"
MANY_URL = "http://localhost:3000/many"


# Rule: session 不存在時操作失敗且錯誤為 session_not_found
#       Example: 尚未開始教學就檢查頁面
async def test_inspect_without_a_session_returns_session_not_found(app):
    result = await app.inspect_page("s_missing")

    assert result["error"] == "session_not_found"
    assert result["page"] is None


# Rule: session 不存在時操作失敗且錯誤為 session_not_found
async def test_inspect_with_an_unknown_session_id_returns_session_not_found(started):
    app, fake, result = started

    other = await app.inspect_page("s_missing")

    assert other["error"] == "session_not_found"
    assert other["page"] is None
    # 拿假 id 來問，不可以動到現在這一場
    assert app.store.current().snapshot_no == 1
    assert not any(call[0] == "snapshot" and call[1] == 2 for call in fake.calls)
```

跑：

```bash
uv run pytest tests/test_tool_inspect.py -q
```

預期紅燈，重點行是：

```text
E       KeyError: 'page'
...
2 failed in 0.09s
```

（A07 的佔位只回 `{"error": "not_implemented"}`，沒有 `page` 這個鍵。）

---

### Step 2：寫最小實作（讓它綠）

打開 `showme/app.py`，把 `inspect_page` 整個換掉：

```python
    async def inspect_page(self, session_id: str) -> dict:
        session = self.store.get(session_id)
        if session is None:
            return {"page": None, "error": "session_not_found"}
        page = await self._take_snapshot(session)
        return {"page": page, "error": ""}
```

跑：

```bash
uv run pytest tests/test_tool_inspect.py -q
```

預期：

```text
2 passed in 0.09s
```

注意 `store.get()` 已經幫我們把兩種情況合成一種：**沒有場次**、**id 對不上**，都回 `None`，也都對應同一個錯誤碼 `session_not_found`（clarify：`檢查頁面_session不存在時的錯誤碼為何.md`，答案 A）。所以這裡不需要寫兩個 `if`。

---

### Step 3：成功時 snapshot# 要 +1、而且不准畫東西

在 `tests/test_tool_inspect.py` 最後加上：

```python
# Rule: 成功時回傳的 page 其 uid snapshot# 比上一份加一
#       Example: 開始教學之後第一次檢查頁面（s1-4 → s2-4）
async def test_inspect_bumps_the_snapshot_number(started):
    app, fake, first = started
    first_uids = [element["uid"] for element in first["page"]["elements"]]
    assert all(uid.startswith("s1-") for uid in first_uids)

    result = await app.inspect_page(first["session_id"])

    assert result["error"] == ""
    uids = [element["uid"] for element in result["page"]["elements"]]
    assert all(uid.startswith("s2-") for uid in uids)
    # 世代變了，位置沒變：s1-4 → s2-4
    assert [uid.split("-")[1] for uid in uids] == [uid.split("-")[1] for uid in first_uids]
    assert app.store.current().snapshot_no == 2
    assert ("snapshot", 2) in fake.calls


# Rule: 成功時回傳新鮮的濃縮 page
async def test_inspect_replaces_the_latest_page(started):
    app, fake, first = started

    result = await app.inspect_page(first["session_id"])

    assert app.store.current().latest_page == result["page"]
    assert result["page"]["url"] == DASHBOARD_URL
    assert result["page"]["title"] == "Dashboard"
    assert result["page"]["truncated"] is False


# Rule: 呼叫後不畫任何 overlay 步驟
async def test_inspect_never_draws_anything(started):
    app, fake, first = started

    await app.inspect_page(first["session_id"])
    await app.inspect_page(first["session_id"])

    assert not any(call[0] == "show" for call in fake.calls)
    assert not any(call[0] == "clear" for call in fake.calls)
    assert not any(call[0] == "done" for call in fake.calls)
    assert app.store.current().snapshot_no == 3


# Rule: 成功時回傳新鮮的濃縮 page（使用者自己換頁之後）
async def test_inspect_sees_the_page_the_user_moved_to(started):
    app, fake, first = started
    fake.navigate(NEW_PROJECT_URL)

    result = await app.inspect_page(first["session_id"])

    assert result["error"] == ""
    assert result["page"]["url"] == NEW_PROJECT_URL
    assert result["page"]["title"] == "New Project"
    assert result["page"]["elements"] == [
        {"uid": "s2-1", "role": "heading", "name": "New Project", "testid": ""},
        {"uid": "s2-2", "role": "textbox", "name": "Project name", "testid": "project-name"},
        {"uid": "s2-3", "role": "button", "name": "Create", "testid": "create"},
    ]


# 回傳形狀固定：只有 page 與 error 兩個鍵
async def test_inspect_result_has_only_page_and_error(started):
    app, fake, first = started

    ok = await app.inspect_page(first["session_id"])
    bad = await app.inspect_page("s_missing")

    assert set(ok) == {"page", "error"}
    assert set(bad) == {"page", "error"}
```

跑：

```bash
uv run pytest tests/test_tool_inspect.py -q
```

預期：

```text
7 passed in 0.11s
```

**規格 Example 是 `s1-4 → s2-4`，我們的假頁只有 2 個元素所以是 `s1-1 → s2-1`。** 這條 Rule 要驗的是「世代 +1、位置不變」，所以測試才會拆成「前綴變成 `s2-`」加上「`-` 後面那一段完全不變」兩個斷言——這樣不管假頁有幾個元素，驗的都是同一件事。

`test_inspect_never_draws_anything` 是 `檢查頁面.feature` 那條 `#TODO` Rule（「呼叫後不畫任何 overlay 步驟」）的不變條件版本：規格沒給例子，我們就驗「`fake.calls` 裡永遠不會出現 `show`／`clear`／`done`」。**不要自己發明「inspect 應該回傳什麼提示字串」之類規格沒寫的需求。**

---

### Step 4：`truncated` 的頁面照樣要回傳

在檔案最後加上：

```python
# Rule: page.truncated 為 true 時仍回傳濃縮 page 供再看
async def test_inspect_returns_a_truncated_page(started):
    app, fake, first = started
    fake.add_page(
        MANY_URL,
        "Many Buttons",
        [{"role": "button", "name": f"Button {i}", "testid": ""} for i in range(151)],
    )
    fake.navigate(MANY_URL)

    result = await app.inspect_page(first["session_id"])

    assert result["error"] == ""
    assert result["page"]["truncated"] is True
    assert len(result["page"]["elements"]) == 150
    assert result["page"]["elements"][0]["uid"] == "s2-1"
    assert result["page"]["elements"][-1]["uid"] == "s2-150"
```

跑：

```bash
uv run pytest tests/test_tool_inspect.py -q
```

預期：

```text
8 passed in 0.12s
```

`FakeBrowser.snapshot()` 會把 151 個元素全部編號後回給我們，是 `build_page()`（A03）把它砍成前 150 並把 `truncated` 設成 `True`。這條測試證明「截斷發生在 Python 這一層，而且 `inspect_page` 沒有因為截斷就改回錯誤」——規格要的是**仍然回傳**（`error` 是空字串），讓 agent 自己決定要不要再看。

---

### Step 5：SHOWING 時不能 inspect（這一步會先紅）

在檔案最後加上：

```python
# Rule: session 狀態不是 READY 時操作失敗（error 字串是 OQ1；A 的設計決定，可改）
async def test_inspect_while_showing_returns_show_step_in_progress(started):
    app, fake, first = started
    app.store.current().state = State.SHOWING

    result = await app.inspect_page(first["session_id"])

    assert result["error"] == "show_step_in_progress"
    assert result["page"] is None
    # 被擋下來就什麼都不做：沒有重拍、沒有畫東西
    assert app.store.current().snapshot_no == 1
    assert not any(call == ("snapshot", 2) for call in fake.calls)
    assert not any(call[0] == "show" for call in fake.calls)
    # 場次還在，state 也沒被改掉（第一個 show_step 要繼續等）
    assert app.store.current().state is State.SHOWING
```

跑：

```bash
uv run pytest tests/test_tool_inspect.py -q
```

預期紅燈，重點行是：

```text
E       AssertionError: assert '' == 'show_step_in_progress'
...
1 failed, 8 passed in 0.12s
```

把 `showme/app.py` 的 `inspect_page` 整個換成最終版：

```python
    async def inspect_page(self, session_id: str) -> dict:
        session = self.store.get(session_id)
        if session is None:
            return {"page": None, "error": "session_not_found"}
        if session.state is State.SHOWING:
            # OQ1（A 的設計決定，可改）：已定案的六個錯誤碼裡沒有 not_ready，
            # 所以 SHOWING 時的 inspect 沿用 show_step_in_progress，不新增錯誤碼。
            return {"page": None, "error": "show_step_in_progress"}
        page = await self._take_snapshot(session)
        return {"page": page, "error": ""}
```

跑：

```bash
uv run pytest tests/test_tool_inspect.py -q
```

預期：

```text
9 passed in 0.12s
```

**這是 A 的設計決定（可改），不是規格。** `檢查頁面.feature` 的「session 狀態不是 READY 時操作失敗」只有 `#TODO`，沒有 Example；design §17 的 open question 1 也只寫「傾向：先回 `show_step_in_progress`，避免新碼」。所以測試只驗兩件規格真的有寫的事：**操作失敗**（`error` 非空、`page` 是 `None`），以及**不會有副作用**（不重拍、不畫、state 不變）。錯誤字串本身如果之後改了，改這一個常數與這一條測試即可。

**測試裡為什麼可以直接寫 `app.store.current().state = State.SHOWING`？** 因為要走到真正的 SHOWING 需要 A12 的阻塞 `show_step`，那還沒寫。`Session` 是 `@dataclass`，欄位可以直接指派；這叫「把系統擺到我要測的狀態」，是單元測試很常見的做法。A15 的真瀏覽器端到端測試會用真的 `show_step` 再走一次。

---

### Step 6：跑完整套件並 commit

```bash
uv run pytest -m "not browser" -q
```

預期最後一行類似：

```text
63 passed, 1 skipped in 0.70s
```

```bash
git add showme/app.py tests/test_tool_inspect.py
git commit -m "feat: inspect_page re-snapshots the page without drawing"
```

預期輸出類似：

```text
[main 3c4d5e6] feat: inspect_page re-snapshots the page without drawing
 2 files changed, 96 insertions(+), 2 deletions(-)
 create mode 100644 tests/test_tool_inspect.py
```

---

## 8. 驗收清單

- [ ] `uv run pytest tests/test_tool_inspect.py -q` 是 9 passed。
- [ ] `uv run pytest -m "not browser" -q` 全綠（只有 A09 那一條 skip）。
- [ ] `inspect_page` 的方法本體只有 6 行左右：`get` → `None` 檢查 → SHOWING 檢查 → `_take_snapshot` → 回傳。
- [ ] `inspect_page` 裡**沒有**任何 `browser.show(...)`／`browser.clear(...)`／`browser.done(...)`。
- [ ] 回傳永遠只有 `page` 與 `error` 兩個鍵。
- [ ] 失敗時 `page` 是 `None`，而且 `snapshot_no` 沒有被加。
- [ ] 成功時 `session.latest_page` 換成了新的 page（下一次 `show_step` 的 uid 驗證要用它）。
- [ ] `show_step`、`end_tutorial` 還是佔位。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `KeyError: 'page'` | `inspect_page` 還是佔位 | 照 Step 2 貼上最小實作 |
| uid 還是 `s1-*` | 你在 `inspect_page` 裡自己組了 page，沒有走 `_take_snapshot()` | 一定要用 `_take_snapshot()`，snapshot# 的遞增只准寫在那裡 |
| `snapshot_no` 一次跳 2 | `inspect_page` 裡先呼叫了 `_take_snapshot()` 又呼叫一次，或 `_take_snapshot()` 裡加了兩次 | 一次呼叫只拍一次 |
| `test_inspect_sees_the_page_the_user_moved_to` 的 title 是 `""` | `navigate()` 的網址跟 `add_page()` 註冊的不一樣（少了斜線、多了 query） | 用檔案上方的常數，不要手打網址 |
| `truncated` 是 `False` 但元素有 151 個 | `build_page()` 沒有把 `len > 150` 算進 `truncated` | 回 A03 修 `build_page()`，不要在 `inspect_page` 裡補 |
| SHOWING 的測試綠了，但 `state` 被改成 READY | 你在 `inspect_page` 裡順手改了 state | 被擋下來的呼叫不可以有任何副作用；第一個 `show_step` 還在等 |
| `AttributeError: 'NoneType' object has no attribute 'state'` | 先 `store.current()` 再檢查 `None`，順序寫反了 | 一定是先 `get()`、先判 `None`，再看 `state` |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/features/檢查頁面.feature` | Rule：成功時回傳新鮮的濃縮 page（只有 `#TODO`） | `test_inspect_replaces_the_latest_page`、`test_inspect_sees_the_page_the_user_moved_to`（測不變條件：每次都重拍、`latest_page` 換新） |
| 同上 | Rule：成功時回傳的 page 其 uid snapshot# 比上一份加一（Example：開始教學之後第一次檢查頁面，`s1-4 → s2-4`） | `test_inspect_bumps_the_snapshot_number` |
| 同上 | Rule：session 不存在時操作失敗且錯誤為 session_not_found（Example：`s_missing`） | `test_inspect_without_a_session_returns_session_not_found`、`test_inspect_with_an_unknown_session_id_returns_session_not_found` |
| 同上 | Rule：呼叫後不畫任何 overlay 步驟（只有 `#TODO`） | `test_inspect_never_draws_anything`（測不變條件：`calls` 裡沒有 `show`／`clear`／`done`） |
| 同上 | Rule：page.truncated 為 true 時仍回傳濃縮 page 供再看（只有 `#TODO`） | `test_inspect_returns_a_truncated_page`（151 → 150 且 `truncated is True`，`error` 仍是 `""`） |
| 同上 | Rule：session 狀態不是 READY 時操作失敗（只有 `#TODO`） | `test_inspect_while_showing_returns_show_step_in_progress`；錯誤字串是 OQ1 的 **A 的設計決定（可改）**，測試同時驗「無副作用」這個規格真的有寫的部分 |
| `docs/spec/.clarify/resolved/features/檢查頁面_session不存在時的錯誤碼為何.md` | 答案 A：與 `show_step` 相同，`session_not_found` | `store.get()` 回 `None` 就回這個碼（含假 id） |
| `docs/spec/.clarify/resolved/data/PageElement_uid的snapshot編號何時遞增.md` | 答案 A：`inspect_page` 成功時 +1 | `test_inspect_bumps_the_snapshot_number`、`test_inspect_never_draws_anything`（連拍兩次變成 3） |
| `docs/spec/.clarify/resolved/data/Page_elements超過上限時如何截斷並標記truncated.md` | 答案 B：硬上限 150，依 DOM 走訪順序取前 150 | `test_inspect_returns_a_truncated_page` |
| `docs/spec/.clarify/resolved/data/Session_各狀態允許呼叫哪些MCP工具.md` | 答案 A：僅 READY 可 inspect | Step 5 的 SHOWING 檢查 |
| `docs/spec/erm.dbml` | `Page`（session_id/url/title/truncated）、`PageElement`（uid/role/name/testid）、`Session` Note「inspect_page 僅在 state 為 READY 時可成功」 | 回傳形狀與兩道前置檢查 |
| `docs/design/showme.md` §7.2 | 前置：Session 存在且 READY；成功：新鮮 page、snapshot# +1、不呼叫 `__showme.show`；失敗：`session_not_found`／第 17 節 open | 整篇 |
| `docs/design/showme.md` §10 | 計數器在 Python Session；`inspect_page` 成功 +1 | `_take_snapshot()` 是唯一會動 `snapshot_no` 的地方 |
| `docs/design/showme.md` §17 open question 1 | 規格空隙；傾向（非決策）：先回 `show_step_in_progress`，避免新碼 | Step 5 的註解與測試註解都標「OQ1，A 的設計決定，可改」 |
