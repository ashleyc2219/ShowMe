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
