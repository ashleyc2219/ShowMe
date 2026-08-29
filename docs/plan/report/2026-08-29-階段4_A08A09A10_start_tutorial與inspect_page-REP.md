# 階段 4｜A08 + A09 + A10：start_tutorial（新建＋覆蓋）與 inspect_page

> 對應計劃：`docs/plan/finish/A08_start_tutorial.md`、`A09_start_tutorial覆蓋場次.md`、`A10_inspect_page.md`
> 日期：2026-08-29

---

## 實作邏輯

這一階段把 `ShowMeApp` 四個 tool 裡的前兩個，從 A07 的佔位 `{"error": "not_implemented"}` 換成真的邏輯。兩個方法都只是「把 A02–A07 已經寫好的零件串起來」，沒有新增任何模組。

### `start_tutorial(url, goal)`

```text
_ensure_browser()          沒有瀏覽器或 is_alive() 是 False → factory() + launch()
     │
session = store.current()  ← 只在這裡取一次；後面靠這個變數判斷「新建」還是「覆蓋」
     │
     ├─ session 不是 None（覆蓋場次）
     │     ├─ SHOWING 且 pending 還沒 done → pending.set_result({"kind":"cancelled",...})   OQ2
     │     └─ browser.clear()（包 try/except Exception: pass，善後失敗不擋新教學）
     │
browser.open(url)
     └─ NavigationFailed → store.delete() → error="navigation_failed"、session_id=""、page=None
     │
     ├─ session is None → store.create(goal)        新 id、READY、steps_shown=0、snapshot_no=0
     └─ 否則           → 就地覆寫欄位              id 不變，goal/state/steps_shown/snapshot_no/
     │                                              pending/latest_page 全部重設
_take_snapshot(session)    snapshot_no 0 → 1，uid 又是 s1-*
     │
回傳 {session_id, goal, page, next_action, error}   五個鍵，一個不多一個不少
```

三個關鍵細節：

- **覆蓋不是「刪掉重建」**：沒有 `store.delete()` + `store.create()` 的寫法，因為那會產生新的 `session_id`，違反「場次識別不變」。
- **`snapshot_no = 0` 而不是 1**：`_take_snapshot()` 自己會 `+= 1`。設成 1 的話 uid 會變 `s2-*`。
- **`latest_page = None`**：舊頁的 uid 必須整份丟掉，否則 `show_step` 會放行陳舊 uid，那正是 snapshot 世代機制要防的事。

### `inspect_page(session_id)`

```text
store.get(session_id) is None ──▶ {"page": None, "error": "session_not_found"}   不碰瀏覽器
session.state is SHOWING      ──▶ {"page": None, "error": "show_step_in_progress"}（OQ1）不碰瀏覽器
否則 _take_snapshot(session)  ──▶ {"page": {...}, "error": ""}                   snapshot_no += 1
```

方法本體六行，只有 `page` 與 `error` 兩個鍵，**完全不呼叫** `browser.show()` / `clear()` / `done()`。
`store.get()` 已經把「沒有場次」與「id 對不上」合成同一個 `None`，所以不需要寫兩個 `if`。

---

## 步驟

照三篇文件的 §7 逐步做，每一步先寫測試看紅、再實作看綠：

| # | 篇章 | 做了什麼 | 紅→綠 |
|---|---|---|---|
| 1 | A08 Step 1–2 | 建 `tests/test_tool_start.py`，寫「goal 原樣回傳」；實作最小版 start | 紅（`KeyError: 'goal'`）→ 1 passed |
| 2 | A08 Step 3–5 | 補 page 形狀、uid 世代、testid 鍵、五個鍵、Session 狀態、空 goal 六條回歸測試 | 不用改實作，7 passed |
| 3 | A08 Step 6 | `navigation_failed` 兩條 | 紅（例外炸出測試外）→ 加 `try/except NavigationFailed` → 9 passed |
| 4 | A08 Step 7–8 | 瀏覽器只 launch 一次、不檢查 host | 不用改實作，11 passed |
| 5 | A09 Step 1 | 測試檔加 `import asyncio` 與 `make_dashboard_browser()` helper | 11 passed |
| 6 | A09 Step 2–3 | 覆蓋五條測試 | 紅（4 failed, 12 passed）→ 實作 `if session is None / else 覆寫` → 16 passed |
| 7 | A09 Step 4 | 覆蓋前 `clear()` | 紅 → 加 `if session is not None: try clear()` → 17 passed |
| 8 | A09 Step 5–6 | 死掉的瀏覽器重 launch、覆蓋時導航失敗刪 Session | 不用改實作，19 passed |
| 9 | A09 Step 7 | OQ2：把卡住的 future 用 `cancelled` 解掉 | 紅 → 加三行 → 20 passed |
| 10 | A09 Step 8 | OQ2 端到端測試，先 `@pytest.mark.skip`（A12 打開） | 20 passed, 1 skipped |
| 11 | A10 Step 1–2 | 建 `tests/test_tool_inspect.py`，`session_not_found` 兩條 | 紅 → 最小實作 → 2 passed |
| 12 | A10 Step 3–4 | snapshot# +1、不畫東西、使用者換頁、只有兩個鍵、truncated | 不用改實作，8 passed |
| 13 | A10 Step 5 | SHOWING 時回 `show_step_in_progress`（OQ1） | 紅 → 加一個 `if` → 9 passed |

另外照 A07 交接的提醒，把 `tests/test_fakes.py` 最後那個 parametrize 裡的 `start_tutorial`（A08 後）與 `inspect_page`（A10 後）兩行刪掉；`show_step`、`end_tutorial` 兩行留給 A12／A13。

三篇做完後把計劃文件從 `docs/plan/unfinish/` 搬到 `docs/plan/finish/`（`git mv`，未 commit）。

---

## 測試方式

全部用 `FakeBrowser`，**一個瀏覽器視窗都沒開**，三十條測試跑不到 0.1 秒。

- **`app` fixture**（乾淨、還沒 start）用在「要從零開始」的測試；**`started` fixture**（已經 start 過、`(app, fake, result)`）用在「要有一場現成教學」的測試。一個測試只做一件事，才不會不小心把 uid 拍成 `s2-*`。
- **不想用 conftest 那顆假瀏覽器時**（例如要指定 `fail_urls`、或要數 factory 被叫幾次），用 A09 加的 `make_dashboard_browser()` 自己造一顆。
- **驗「沒做某件事」用 `fake.calls`**：`assert not any(call[0] == "show" for call in fake.calls)` 就是「inspect 絕對不畫東西」的機械化驗收。
- **把系統擺到要測的狀態**：`app.store.current().state = State.SHOWING` 直接指派（`Session` 是 dataclass），因為真正進入 SHOWING 要等 A12。
- **數 launch 次數用 monkeypatch**：把 `fake_browser.launch` 換成會計數的 async 函數，測完就丟，不用改 `tests/fakes.py`。

---

## 遇到的問題與怎麼解決

1. **A10 Step 1 的紅燈訊息跟文件寫的不一樣。** 文件預期 `KeyError: 'page'`，實際是
   `AssertionError: assert 'not_implemented' == 'session_not_found'`——因為佔位回的 dict 裡
   `error` 這個鍵是存在的，測試先斷言 `error` 才碰 `page`，所以先炸的是斷言。已把 A10 §7 Step 1
   那個預期輸出區塊改成實際訊息。行為完全正確（就是紅的），只是訊息不同。

2. **文件裡的方法簽名寫 `-> dict`。** A01 實測過：mcp 2.1.1 從回傳型別註記推導 output schema，
   裸 `dict` 推不出來、`structured_content` 會變 `None`。實作一律用 `dict[str, object]`，
   並把 A08／A09／A10 三篇文件裡那 8 行簽名一起改掉。

3. **文件裡「全套件 N passed」的累積數字是估的。** A08 §3 寫 34、Step 9 寫 45；A09 寫 54；A10 寫 63。
   實際是 74 / 84 / 93 / 101（前面幾篇實際寫的測試比估的多）。已把四處改成實際數字。

4. **A08／A10 的 §5「會動到的檔案」漏了 `tests/test_fakes.py`。** 刪佔位那一行是 A07 報告交代的事，
   但兩篇文件的檔案表與 commit 指令都沒寫。已補進表格與 `git add` 那一行。

5. **`except Exception: pass` 只出現在一個地方。** 就是覆蓋時的 `browser.clear()`——那是善後動作，
   頁面早就跳走、overlay 不在了也不該擋住新教學。`browser.open()` 那邊嚴格只接 `NavigationFailed`，
   絕不寫成 `except Exception`，否則 `_take_snapshot()` 裡真正的程式錯誤會被偽裝成 `navigation_failed`。

6. **`pending.set_result()` 前一定要先問 `not pending.done()`。** 對已經有答案的 Future 再放答案會丟
   `asyncio.InvalidStateError`。這跟 A07 `_on_emit()` 的「先問再放」是同一招，也就是規格
   「每步只取第一筆事件」的實作方式。

---

## 測試結果

```text
$ uv run pytest tests/test_tool_start.py -q
20 passed, 1 skipped in 0.06s

$ uv run pytest tests/test_tool_inspect.py -q
9 passed in 0.01s

$ uv run pytest -m "not browser" -q
101 passed, 1 skipped, 18 deselected in 0.62s

$ uv run pytest -m browser -q
18 passed, 102 deselected in 20.47s
```

**那 1 個 skipped 是 A09 的 OQ2 端到端測試**
（`tests/test_tool_start.py::test_restart_ends_the_blocked_show_step_as_timeout`，
skip 理由「A12 完成 show_step 阻塞等待後打開」）：它要驗「被 start_tutorial 覆蓋掉的那次
`show_step` 回 `event="timeout"`、`page=None`、`error=""`」，而 `show_step` 的阻塞等待要
A12 才寫。**A12 的最後一步要把那行 `@pytest.mark.skip(...)` 刪掉，並讓這條測試綠。**

---

## 給下一篇（A11／A12）的交接

1. **`start_tutorial` 與 `inspect_page` 已完成，不要再動它們。** `show_step`、`end_tutorial`
   還是 `{"error": "not_implemented"}` 佔位。
2. **`tests/test_fakes.py` 的 parametrize 現在剩兩行**（`show_step`、`end_tutorial`）：
   A12 刪 `show_step` 那行、A13 刪 `end_tutorial` 那行，A13 之後整個
   `test_tool_methods_are_placeholders_for_now` 就沒了。
3. **A12 要打開 A09 的 skip 測試**（見上方測試結果）。那條測試依賴的約定是：
   `show_step` `await` 的 future 若拿到 `{"kind": "cancelled", "url": "", "ts": 0}`，
   就回 `event="timeout"`、`page=None`、`error=""`、`next_action=""`，而且**不再碰瀏覽器與 Session**
   （那些已經被 `start_tutorial` 換掉了）。
4. **前置檢查的寫法已經定型**：`store.get(session_id)` → `None` 就 `session_not_found`；
   `state is State.SHOWING` 就 `show_step_in_progress`。A13 的 `end_tutorial` 照抄同一組。
5. **`_take_snapshot()` 是唯一會動 `snapshot_no` 的地方**，A11／A12 回傳新鮮 page 時也要走它，
   不要自己組 page。
