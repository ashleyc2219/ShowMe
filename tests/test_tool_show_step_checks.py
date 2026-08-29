"""show_step 六道前置檢查的測試。全部用 FakeBrowser，不開瀏覽器。

六關都過的路徑在 A12 之後會真的畫箭頭並阻塞等待，所以那幾條測試都帶 timeout_s=0.2，
用「等 0.2 秒沒人 emit → error="" 且 event="timeout"」來證明「沒有被前置檢查擋下來」。
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

    # 六關都過了：真的畫出來、等 0.2 秒沒人 emit → timeout（A12 之後的行為）
    assert result["error"] == ""
    assert result["event"] == "timeout"
    assert app.store.current().steps_shown == MAX_STEPS   # 11 + 1 = 12


# 檢查順序：state 比 steps_shown 先檢查
async def test_state_is_checked_before_the_step_count(started):
    app, fake, first = started
    session = app.store.current()
    session.state = State.SHOWING
    session.steps_shown = MAX_STEPS

    result = await app.show_step(first["session_id"], "s1-1", "Click New Project", "click", 1, 4)

    assert result["error"] == "show_step_in_progress"


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

    # 六關都過了
    assert result["error"] == ""
    assert result["event"] == "timeout"


# Rule: kind 為 observe 且 expect_text 為空時操作失敗（其他 kind 不受這條限制）
async def test_click_without_expect_text_passes_the_pre_checks(started):
    app, fake, first = started

    result = await app.show_step(
        first["session_id"], "s1-1", "Click New Project", "click", 1, 4,
        expect_text="", timeout_s=0.2,
    )

    # 六關都過了（click 不需要 expect_text）
    assert result["error"] == ""
    assert result["event"] == "timeout"


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
    # 用新鮮 uid 重試就過得了第五關；六關都過 → 等 0.2 秒 → timeout
    assert retried["error"] == ""
    assert retried["event"] == "timeout"


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
