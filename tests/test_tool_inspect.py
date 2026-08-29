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
