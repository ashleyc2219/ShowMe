"""start_tutorial 的行為測試。全部用 FakeBrowser，不開瀏覽器。"""

from __future__ import annotations

import asyncio

import pytest

from fakes import FakeBrowser
from showme.app import ShowMeApp
from showme.session import START_NEXT_ACTION, State

pytestmark = pytest.mark.anyio

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"
BAD_URL = "http://localhost:1/"


def make_dashboard_browser(*, fail_urls: set[str] | None = None) -> FakeBrowser:
    """跟 conftest 的 fake_browser 一樣的兩頁，但可以自己指定 fail_urls。"""
    browser = FakeBrowser(fail_urls=fail_urls)
    browser.add_page(
        DASHBOARD_URL,
        "Dashboard",
        [
            {"role": "button", "name": "New Project", "testid": "new-project"},
            {"role": "link", "name": "Settings", "testid": ""},
        ],
    )
    browser.add_page(
        NEW_PROJECT_URL,
        "New Project",
        [
            {"role": "heading", "name": "New Project", "testid": ""},
            {"role": "textbox", "name": "Project name", "testid": "project-name"},
            {"role": "button", "name": "Create", "testid": "create"},
        ],
    )
    return browser


# Rule: 成功開始後回傳的 goal 等於傳入的 goal
async def test_start_returns_the_same_goal(app):
    result = await app.start_tutorial(DASHBOARD_URL, "create a project")

    assert result["goal"] == "create a project"
    assert result["error"] == ""
    assert result["session_id"] != ""


# Rule: 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1
async def test_start_returns_the_first_page(started):
    app, fake, result = started

    page = result["page"]
    assert page["url"] == DASHBOARD_URL
    assert page["title"] == "Dashboard"
    assert page["truncated"] is False
    assert page["elements"] == [
        {"uid": "s1-1", "role": "button", "name": "New Project", "testid": "new-project"},
        {"uid": "s1-2", "role": "link", "name": "Settings", "testid": ""},
    ]


# Rule: 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1
async def test_start_uids_are_the_first_generation(started):
    app, fake, result = started

    uids = [element["uid"] for element in result["page"]["elements"]]
    assert uids != []
    assert all(uid.startswith("s1-") for uid in uids)


# Rule: page.elements 的 testid 鍵永遠存在，沒有 data-testid 時為空字串
async def test_start_elements_always_have_a_testid_key(started):
    app, fake, result = started

    settings = [e for e in result["page"]["elements"] if e["name"] == "Settings"][0]
    assert "testid" in settings
    assert settings["testid"] == ""
    for element in result["page"]["elements"]:
        assert set(element) == {"uid", "role", "name", "testid"}


# Rule: 成功開始後回傳的 next_action 與 error（回傳形狀固定）
async def test_start_result_has_all_five_keys(started):
    app, fake, result = started

    assert set(result) == {"session_id", "goal", "page", "next_action", "error"}
    assert result["next_action"] == START_NEXT_ACTION
    assert result["error"] == ""


# Rule: 成功開始後 session 狀態為 READY
async def test_start_leaves_the_session_ready(started):
    app, fake, result = started

    session = app.store.current()
    assert session is not None
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 1
    assert session.session_id == result["session_id"]
    assert session.session_id.startswith("s_")
    assert session.goal == "create a project"
    assert session.latest_page == result["page"]
    assert session.pending is None


# Rule: goal 為空字串時仍成功開始
async def test_start_accepts_an_empty_goal(app):
    result = await app.start_tutorial(DASHBOARD_URL, "")

    assert result["error"] == ""
    assert result["goal"] == ""
    assert app.store.current().state is State.READY
    assert app.store.current().goal == ""


# Rule: 目標 url 無法開啟時操作失敗且錯誤為 navigation_failed
async def test_start_returns_navigation_failed_when_the_url_cannot_open():
    browser = FakeBrowser(fail_urls={BAD_URL})
    app = ShowMeApp(browser_factory=lambda: browser)

    result = await app.start_tutorial(BAD_URL, "create a project")

    assert result["error"] == "navigation_failed"
    assert result["session_id"] == ""
    assert result["page"] is None
    assert result["next_action"] == ""
    assert result["goal"] == "create a project"
    # A 的設計決定（可改）：導航失敗不留下 Session
    assert app.store.current() is None


# Rule: 目標 url 無法開啟時操作失敗且錯誤為 navigation_failed
async def test_start_failure_does_not_take_a_snapshot():
    browser = FakeBrowser(fail_urls={BAD_URL})
    app = ShowMeApp(browser_factory=lambda: browser)

    await app.start_tutorial(BAD_URL, "create a project")

    assert not any(call[0] == "snapshot" for call in browser.calls)
    assert not any(call[0] == "show" for call in browser.calls)


# Rule: 啟動或重用 Chrome 並開啟傳入的 url（feature 只有 #TODO，這裡測不變條件）
async def test_start_twice_reuses_the_same_browser(app, fake_browser):
    launches: list[str] = []
    original_launch = fake_browser.launch

    async def counting_launch() -> None:
        launches.append("launch")
        await original_launch()

    fake_browser.launch = counting_launch

    await app.start_tutorial(DASHBOARD_URL, "create a project")
    await app.start_tutorial(DASHBOARD_URL, "create a project")

    assert launches == ["launch"]
    assert fake_browser.calls.count(("open", DASHBOARD_URL)) == 2


# Rule: 開始教學不因 url 不是 localhost 而操作失敗（feature 只有 #TODO，這裡測不變條件）
async def test_start_does_not_check_the_host(app, fake_browser):
    result = await app.start_tutorial("http://example.test/", "create a project")

    assert result["error"] == ""
    assert result["page"]["url"] == "http://example.test/"
    assert result["page"]["title"] == ""
    assert result["page"]["elements"] == []
    assert result["page"]["truncated"] is False
    assert ("open", "http://example.test/") in fake_browser.calls


# Rule: 同一時間只允許一個教學場次，再次開始教學時場次識別不變並覆蓋目標與網址
async def test_restart_keeps_the_session_id_and_overwrites_the_goal(started):
    app, fake, first = started

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert second["error"] == ""
    assert second["session_id"] == first["session_id"]
    assert second["goal"] == "invite a member"
    assert second["next_action"] == START_NEXT_ACTION


# Rule: 同一時間只允許一個教學場次，再次開始教學時場次識別不變並覆蓋目標與網址
async def test_restart_opens_the_new_url(started):
    app, fake, first = started

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert ("open", NEW_PROJECT_URL) in fake.calls
    assert second["page"]["url"] == NEW_PROJECT_URL
    assert second["page"]["title"] == "New Project"


# Rule: 同一時間只允許一個教學場次…（Example：進行中再開始另一個目標，steps_shown 為 0）
async def test_restart_resets_steps_shown(started):
    app, fake, first = started
    app.store.current().steps_shown = 3

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    session = app.store.get(first["session_id"])
    assert session is not None
    assert session.steps_shown == 0


# Rule: 成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1（含覆蓋既有場次）
async def test_restart_restarts_snapshot_numbering(started):
    app, fake, first = started

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    uids = [element["uid"] for element in second["page"]["elements"]]
    assert uids != []
    assert all(uid.startswith("s1-") for uid in uids)
    session = app.store.get(first["session_id"])
    assert session is not None
    assert session.snapshot_no == 1
    assert fake.calls.count(("snapshot", 1)) == 2


# Rule: 同一時間只允許一個教學場次…（Example：進行中再開始另一個目標，state 為 READY）
async def test_restart_leaves_the_session_ready(started):
    app, fake, first = started
    app.store.current().state = State.SHOWING

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    session = app.store.get(first["session_id"])
    assert session is not None
    assert session.state is State.READY
    assert session.pending is None
    assert session.latest_page == app.store.current().latest_page


# design §7.1 覆蓋時：關掉進行中的完成觀察、clear() overlay、再 goto 新 url
async def test_restart_clears_the_previous_overlay(started):
    app, fake, first = started

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert fake.calls.count(("clear",)) == 1
    assert fake.calls.index(("clear",)) < fake.calls.index(("open", NEW_PROJECT_URL))


# design §7.1：同一 Browser/Page 若仍活著則 goto 新 url；死掉則重 launch
async def test_restart_relaunches_a_dead_browser():
    made: list[FakeBrowser] = []

    def factory() -> FakeBrowser:
        browser = make_dashboard_browser()
        made.append(browser)
        return browser

    app = ShowMeApp(browser_factory=factory)
    first = await app.start_tutorial(DASHBOARD_URL, "create a project")
    assert len(made) == 1

    made[0].alive = False
    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert len(made) == 2
    assert made[1].launched is True
    assert ("open", NEW_PROJECT_URL) in made[1].calls
    assert second["error"] == ""
    assert second["session_id"] == first["session_id"]


# A 的設計決定（可改）：導航失敗不留下 Session（成功的 start 才有 Session）
async def test_restart_navigation_failure_deletes_the_session():
    browser = make_dashboard_browser(fail_urls={BAD_URL})
    app = ShowMeApp(browser_factory=lambda: browser)
    first = await app.start_tutorial(DASHBOARD_URL, "create a project")
    assert first["error"] == ""

    second = await app.start_tutorial(BAD_URL, "invite a member")

    assert second["error"] == "navigation_failed"
    assert second["session_id"] == ""
    assert second["page"] is None
    assert app.store.current() is None
    assert app.store.get(first["session_id"]) is None


# A 的設計決定（可改）：OQ2 —— 覆蓋時把還在等的 future 用 cancelled 解掉
async def test_restart_resolves_a_pending_future_with_cancelled(started):
    app, fake, first = started
    session = app.store.current()
    loop = asyncio.get_running_loop()
    pending = loop.create_future()
    session.pending = pending
    session.state = State.SHOWING

    await app.start_tutorial(NEW_PROJECT_URL, "invite a member")

    assert pending.done() is True
    assert pending.result() == {"kind": "cancelled", "url": "", "ts": 0}
    assert app.store.current().pending is None
    assert app.store.current().state is State.READY


# A 的設計決定（可改）：OQ2 —— 被覆蓋的那次 show_step 回 event="timeout"、page=None、error=""
@pytest.mark.skip(reason="A12 完成 show_step 阻塞等待後打開")
async def test_restart_ends_the_blocked_show_step_as_timeout(started):
    app, fake, first = started
    session_id = first["session_id"]

    task = asyncio.create_task(
        app.show_step(session_id, "s1-1", "Click New Project", "click", 1, 4)
    )
    for _ in range(100):
        if app.store.current().state is State.SHOWING:
            break
        await asyncio.sleep(0.01)
    assert app.store.current().state is State.SHOWING

    second = await app.start_tutorial(NEW_PROJECT_URL, "invite a member")
    step = await asyncio.wait_for(task, timeout=5)

    assert step["event"] == "timeout"
    assert step["page"] is None
    assert step["error"] == ""
    assert step["next_action"] == ""
    assert second["error"] == ""
    assert second["session_id"] == session_id
    assert app.store.current().state is State.READY
    assert app.store.current().steps_shown == 0
