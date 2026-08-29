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
