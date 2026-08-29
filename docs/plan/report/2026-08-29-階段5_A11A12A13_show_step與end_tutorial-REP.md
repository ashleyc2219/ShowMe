# 階段 5｜A11 + A12 + A13：show_step（前置檢查＋阻塞等待）與 end_tutorial

> 對應計劃：`docs/plan/unfinish/A11_show_step前置檢查.md`、`A12_show_step阻塞等待.md`、`A13_end_tutorial.md`
> 日期：2026-08-29

---

## 實作邏輯

這一階段把 `ShowMeApp` 剩下的兩個 tool 從佔位換成真的邏輯。做完之後 `grep -rn not_implemented showme/` 沒有輸出，四個 tool 全部有肉。

### `show_step`：先驗六關，再畫、再等

```text
show_step(session_id, uid, instruction, kind, step_index, step_total, expect_text="", timeout_s=120)
  │
  │ ── 前置六關（A11）：任何一關被擋 → 不畫、steps_shown 不加、state 不變 ──
  ├─(1) store.get(session_id) is None      ─▶ session_not_found        page=None
  ├─(2) state is SHOWING                   ─▶ show_step_in_progress    page=None（第一次繼續等）
  ├─(3) steps_shown >= MAX_STEPS(12)       ─▶ max_steps_exceeded       page=None
  ├─(4) kind = normalize_kind(kind)
  │     expect_text_missing(kind, expect)  ─▶ expect_text_required     page=None
  ├─(5) uid 不在 session.latest_page       ─▶ uid_not_in_snapshot      page=新鮮 page（snapshot# +1）
  ├─(6) timeout_s = normalize_timeout_s(timeout_s)   未傳／0／負 → 120.0（不會失敗）
  │
  │ ── 畫（A12）──
  ├─ pending = loop.create_future()   ← 信箱，先建好才畫，避免 emit 比信箱早到
  ├─ state = SHOWING ; steps_shown += 1
  ├─ browser.show({uid, instruction, kind, index, total, expect})   ← 鍵名是接縫鎖死的
  │
  │ ── 等（A12）──
  ├─ started = loop.time()（單調時鐘）
  ├─ event = await wait_for(shield(pending), timeout=timeout_s)     ← TimeoutError → event=None
  ├─ elapsed = loop.time() - started
  │
  ├─ event.kind == "cancelled"（被 start_tutorial 覆蓋，OQ2）
  │      ─▶ {"event": "timeout", "page": None, "next_action": "", "error": ""}   不再碰瀏覽器與 Session
  ├─ event is None 或 elapsed >= timeout_s ─▶ event="timeout" + browser.clear()
  └─ 否則                                  ─▶ event = emit 的 kind（step_done / stuck），不 clear
        │
        └─ pending=None、state=READY、_take_snapshot()（snapshot# +1）
           ─▶ {"event", "signal": "", "elapsed_s": round(x,1), "page", "next_action": STEP_NEXT_ACTION, "error": ""}
```

三個關鍵細節：

- **`shield` 不是裝飾品**：`wait_for` 逾時時會取消它在等的東西。沒有 `shield`，被取消的就是 `session.pending` 本人；等使用者晚一步做完、overlay emit 進來，`_on_emit` 的 `set_result()` 就會丟 `InvalidStateError` 炸在 Playwright 的 callback 裡。有 `shield`，被取消的是外面那層假殼，晚到的 `set_result` 安靜成功、然後隨 `pending = None` 被丟掉。`test_emit_that_arrives_after_the_deadline_is_still_timeout` 就是在守這件事。
- **`elapsed >= timeout_s` 這個 `or` 條件**：規格明寫「經過時間大於等於 timeout_s 就是 timeout，含剛好相等」。實務上幾乎不會單獨成立，但把規則寫進程式，之後誰改都不會改壞。
- **只有 timeout 才 `clear()`**：`step_done` / `stuck` 之後不清，overlay 自己處理，而且下一次 `show()` 本來就會先清。

### `end_tutorial`：清、貼、刪

```text
end_tutorial(session_id, summary)
  ├─ store.get(session_id) is None ─▶ {"ok": False, "error": "session_not_found"}
  ├─ state is SHOWING              ─▶ {"ok": False, "error": "show_step_in_progress"}（OQ1）
  ├─ browser.clear()               ← 先拿掉箭頭
  ├─ browser.done(DONE_BANNER_TEXT) ← 再貼橫幅；summary 完全不用
  ├─ store.delete()                ← 兩個 await 之後才刪：clear 炸了 Session 還在，agent 可以重試
  └─ {"ok": True, "error": ""}     ← 不 close()，人要留在畫面上看那句 ✅
```

---

## 步驟

照三篇文件的 §7 逐步做，每一步先寫測試看紅、再實作看綠：

| # | 篇章 | 做了什麼 | 紅→綠 |
|---|---|---|---|
| 1 | A11 Step 1–2 | 建 `tests/test_tool_show_step_checks.py`，寫前三關（session / state / steps）六條 | 紅（5 failed, 1 passed）→ 6 passed |
| 2 | A11 Step 3–4 | 加 kind／expect_text 四條 | 紅（2 failed, 8 passed）→ 10 passed |
| 3 | A11 Step 5–6 | 加 uid 五條（含「失敗仍附新鮮 page」「六個鍵都在」） | 紅（3 failed, 12 passed）→ 15 passed |
| 4 | A11 Step 7 | 全套件；順手刪 `tests/test_fakes.py` 的 `show_step` 佔位行（見下方問題 1） | 115 passed, 1 skipped |
| 5 | A12 Step 1 | 建 `tests/test_tool_show_step_wait.py`（11 條：畫出瞬間／三種 event／只收第一筆／並發） | 紅（11 failed）|
| 6 | A12 Step 2–3 | 把佔位換成「畫 + 等 + 收尾」 | 11 passed；全套件如文件預期出現 4 條紅 |
| 7 | A12 Step 5 | 更新 A11 留下的 4 條佔位斷言（`not_implemented` → `error == ""` + `event == "timeout"`） | 15 passed |
| 8 | A12 Step 6 | 刪掉 `tests/test_tool_start.py` 的 `@pytest.mark.skip`（A09 的 OQ2 測試） | 21 passed、0 skipped |
| 9 | A13 Step 1–3 | 建 `tests/test_tool_end.py`（11 條）；實作 `end_tutorial` | 紅（10 failed, 1 passed）→ 11 passed |
| 10 | A13 收尾 | 刪掉 `tests/test_fakes.py` 的 `test_tool_methods_are_placeholders_for_now`（parametrize 空了，整個函數拿掉） | 全套件全綠 |

沒有做 A13 Step 4（REPL 手感確認，文件標「可選」）——`tests/test_tool_end.py` 已經把同一條路徑測過了。**照主控指示沒有 commit。**

---

## 測試方式

全部用 `FakeBrowser`，**一個瀏覽器視窗都沒開**，37 條新測試連同兩條真的等 0.2／0.3 秒的 timeout 測試在內，跑不到 2 秒。

- **阻塞測試的固定招式**：`task = asyncio.create_task(app.show_step(...))` 把它丟到背景 → `await asyncio.sleep(0)` 連做 5 次讓它跑到等待點 → `fake.emit("step_done")` → `await task`。除了「就是要測 timeout」那兩條以外，一律這樣寫；直接 `await app.show_step(...)` 會讓測試自己也卡住，最後被 pytest-timeout 砍掉。
- **驗「還在等」用 `assert not task.done()`**，這是「真的阻塞了」唯一機械化的證據。
- **驗「沒做某件事」用 `fake.calls`**：`assert not any(call[0] == "show" for call in fake.calls)`（被擋下來不可以畫）、`assert ("close",) not in fake.calls`（end 不關瀏覽器）、`assert fake.calls[-2:] == [("clear",), ("done", DONE_BANNER_TEXT)]`（順序是驗收項目）。
- **`elapsed_s` 用 `>=` 不用 `==`**：浮點數加 `round(x, 1)`，實際會是 `0.2` 或 `0.3`。
- **banner 文字一律 import `DONE_BANNER_TEXT` 常數**，不在測試裡重打一次（中間那條是 em dash `—`，用眼睛比對不出來）。

---

## 遇到的問題與怎麼解決

1. **`tests/test_fakes.py` 的 `show_step` 佔位行在 A11 就過期了，不是 A12。** 那條測試斷言 `await app.show_step(...) == {"error": "not_implemented"}`，但 A11 一實作前置檢查，沒有 Session 的呼叫就變成回六個鍵的 `session_not_found`，A11 Step 7 的全套件就紅了。已在 A11 刪掉那一行，並把 A11 §5 的檔案表、Step 7 的 `git add` 與驗收清單補上這件事（原本文件把它排在 A12）。`end_tutorial` 那一行照計劃留到 A13 才刪，刪完 parametrize 沒有案例了，整個測試函數一起拿掉。

2. **A12 的測試檔實際是 11 條，文件寫 10 條。** 文件 Step 3 與驗收清單的 `10 passed` 是估的（檔案裡實際貼了 11 個測試函數）。已把 A12 的紅燈預期（`10 failed` → `11 failed`）、Step 3 與驗收清單改成 11。

3. **文件的 `create_task` + `sleep(0)` 寫法很穩，不用換成輪詢 `session.state`。** 事前擔心讓出次數不夠會抓不到 SHOWING；實際上 `FakeBrowser` 的 `is_alive()` / `show()` 都不會真的讓出 event loop，所以背景 task 第一次 `sleep(0)` 就一路跑到 `wait_for`，5 次綽綽有餘。11 條測試連跑多次都沒有 flake，維持文件原寫法。

4. **文件裡的方法簽名寫 `-> dict`。** 沿用 A08–A10 已經確立的差異：mcp 2.1.1 從回傳型別註記推導 output schema，裸 `dict` 推不出來、`structured_content` 會變 `None`。實作一律 `dict[str, object]`，並把 A11／A12／A13 三篇文件那 6 行簽名一起改掉。

5. **文件裡「全套件 N passed」的累積數字是估的**（A11 寫 78、A12 寫 40／51／58）。已改成實際：A11 完成時 115 passed 1 skipped、A12 完成時 127 passed、A13 完成時 147 passed（不含 browser）。A12 那個「4 failed 是預期中的」中間狀態確實一模一樣地發生了，紅的就是文件點名的那四條。

6. **B 的真 overlay emit 多帶一個 `signal` 鍵。** `_on_emit` 與 `show_step` 都只讀 `event["kind"]`，多出來的鍵自然被忽略，Python 側一行都不用改；回傳的 `signal` 照規格固定給 `""`（完成判定只看 `event`）。已把這件事寫進 A12 的「對照規格」表。

7. **平行的 A14 agent 同時在改 `tests/conftest.py` 並新增 `tests/test_mcp_contract.py`。** 中途 `test_end_tutorial_with_unknown_session_also_returns_an_error_field` 是紅的——它等的就是 `end_tutorial` 的實作，A13 一寫完就自己綠了。沒有互相搶檔。

---

## 測試結果

```text
$ uv run pytest tests/test_tool_show_step_checks.py -q
15 passed in 0.87s

$ uv run pytest tests/test_tool_show_step_wait.py -q
11 passed in 0.53s

$ uv run pytest tests/test_tool_end.py -q
11 passed in 0.02s

$ uv run pytest -m "not browser" -q
147 passed, 18 deselected in 1.58s

$ uv run pytest -q
165 passed in 23.50s

$ grep -rn not_implemented showme/
（沒有輸出）
```

**0 skipped**：A09 留下的 OQ2 測試（`tests/test_tool_start.py::test_restart_ends_the_blocked_show_step_as_timeout`）已在 A12 Step 6 打開並跑綠——被 `start_tutorial` 覆蓋掉的那次 `show_step` 回 `event="timeout"`、`page=None`、`error=""`、`next_action=""`。

---

## 給下一篇（A15）的交接

1. **四個 tool 的邏輯全部完成**，`showme/app.py` 不再有任何佔位。A15 的端到端測試可以直接串 `start_tutorial → show_step → end_tutorial`。
2. **`show_step` 真的會阻塞最長 `timeout_s` 秒。** A15 寫真瀏覽器測試時，每一條都要給小的 `timeout_s`（例如 2–5 秒），否則沒人 emit 就是等 120 秒。
3. **timeout 之後會呼叫 `browser.clear()`，`step_done` / `stuck` 之後不會**——真 overlay 的 e2e 斷言 `("clear",)` 時要注意這個差別（真瀏覽器沒有 `fake.calls`，要改看畫面或 `evaluate`）。
4. **真 overlay 的 emit payload 多一個 `signal` 鍵**，Python 只看 `kind`，`StepResult.signal` 永遠回 `""`，不要在 e2e 裡斷言它有值。
5. **`end_tutorial` 不關瀏覽器**，A15 的 e2e 收尾要自己 `await app.shutdown()`，否則 headless Chromium 會留著。
