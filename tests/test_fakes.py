"""A07：FakeBrowser 的行為，以及 ShowMeApp 骨架的三個內部方法。

這些測試不開瀏覽器，所以沒有 browser marker：
    uv run pytest tests/test_fakes.py -q
"""

from __future__ import annotations

import asyncio

import pytest

from fakes import FakeBrowser
from showme.browser import BrowserLike, NavigationFailed
from showme.session import State

pytestmark = pytest.mark.anyio

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"

# BrowserLike 要求的方法（showme/browser.py 的 Protocol），照抄一份在這裡當檢查表。
BROWSER_LIKE_METHODS = (
    "launch",
    "is_alive",
    "open",
    "current_url",
    "title",
    "snapshot",
    "show",
    "clear",
    "done",
    "set_emit_handler",
    "close",
)


# ---------------------------------------------------------------- FakeBrowser


def test_fake_browser_has_every_browser_like_method():
    browser: BrowserLike = FakeBrowser()   # 型別註記：讓型別檢查器也幫忙盯

    missing = [name for name in BROWSER_LIKE_METHODS if not callable(getattr(browser, name, None))]

    assert missing == []


async def test_open_records_the_call_and_updates_url(fake_browser):
    await fake_browser.open(DASHBOARD_URL)

    assert fake_browser.calls == [("open", DASHBOARD_URL)]
    assert await fake_browser.current_url() == DASHBOARD_URL
    assert await fake_browser.title() == "Dashboard"


async def test_open_raises_navigation_failed_for_fail_urls():
    browser = FakeBrowser(fail_urls={"http://localhost:1"})

    with pytest.raises(NavigationFailed):
        await browser.open("http://localhost:1")

    assert browser.calls == []
    assert await browser.current_url() == "about:blank"


async def test_snapshot_numbers_uids_by_n(fake_browser):
    await fake_browser.open(DASHBOARD_URL)

    first = await fake_browser.snapshot(1)
    second = await fake_browser.snapshot(2)

    assert [element["uid"] for element in first["elements"]] == ["s1-1", "s1-2"]
    assert [element["uid"] for element in second["elements"]] == ["s2-1", "s2-2"]
    assert first["elements"][0] == {
        "uid": "s1-1",
        "role": "button",
        "name": "New Project",
        "testid": "new-project",
    }
    assert first["truncated"] is False
    assert fake_browser.calls == [("open", DASHBOARD_URL), ("snapshot", 1), ("snapshot", 2)]


async def test_snapshot_on_unknown_url_returns_empty(fake_browser):
    result = await fake_browser.snapshot(1)   # 還停在 about:blank

    assert result == {"elements": [], "truncated": False}


async def test_navigate_switches_the_page_without_recording_a_call(fake_browser):
    await fake_browser.open(DASHBOARD_URL)
    fake_browser.navigate(NEW_PROJECT_URL)

    result = await fake_browser.snapshot(2)

    assert await fake_browser.title() == "New Project"
    assert [element["name"] for element in result["elements"]] == [
        "New Project",
        "Project name",
        "Create",
    ]
    assert ("open", NEW_PROJECT_URL) not in fake_browser.calls


def test_emit_forwards_to_the_handler(fake_browser):
    received: list[dict] = []
    fake_browser.set_emit_handler(received.append)

    fake_browser.emit("step_done", ts=1756400000)

    assert received == [{"kind": "step_done", "url": "about:blank", "ts": 1756400000}]


def test_emit_without_handler_does_nothing(fake_browser):
    fake_browser.emit("stuck")   # 不該丟例外


async def test_close_records_the_call_and_marks_it_dead(fake_browser):
    await fake_browser.close()

    assert fake_browser.calls == [("close",)]
    assert await fake_browser.is_alive() is False


# ------------------------------------------------------- ShowMeApp 骨架


async def test_ensure_browser_launches_once_and_registers_the_handler(app, fake_browser):
    first = await app._ensure_browser()
    second = await app._ensure_browser()

    assert first is fake_browser
    assert second is fake_browser
    assert fake_browser.launched is True
    assert fake_browser._handler == app._on_emit


async def test_take_snapshot_bumps_snapshot_no_and_stores_latest_page(app, fake_browser):
    session = app.store.create("create a project")
    fake_browser.navigate(DASHBOARD_URL)

    page = await app._take_snapshot(session)

    assert session.snapshot_no == 1
    assert page["url"] == DASHBOARD_URL
    assert page["title"] == "Dashboard"
    assert page["truncated"] is False
    assert [element["uid"] for element in page["elements"]] == ["s1-1", "s1-2"]
    assert session.latest_page == page


async def test_take_snapshot_twice_goes_from_s1_to_s2(app, fake_browser):
    session = app.store.create("create a project")
    fake_browser.navigate(DASHBOARD_URL)

    await app._take_snapshot(session)
    fake_browser.navigate(NEW_PROJECT_URL)
    page = await app._take_snapshot(session)

    assert session.snapshot_no == 2
    assert page["title"] == "New Project"
    assert [element["uid"] for element in page["elements"]] == ["s2-1", "s2-2", "s2-3"]
    assert session.latest_page == page


async def test_on_emit_sets_the_result_only_while_showing(app):
    session = app.store.create("create a project")
    session.pending = asyncio.get_running_loop().create_future()

    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})
    assert session.pending.done() is False       # state 還是 READY → 忽略

    session.state = State.SHOWING
    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})

    assert session.pending.done() is True
    assert session.pending.result() == {"kind": "step_done", "url": DASHBOARD_URL, "ts": 1}


async def test_on_emit_ignores_the_second_event(app):
    session = app.store.create("create a project")
    session.state = State.SHOWING
    session.pending = asyncio.get_running_loop().create_future()

    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})
    app._on_emit({"kind": "stuck", "url": DASHBOARD_URL, "ts": 1})

    assert session.pending.result()["kind"] == "step_done"


async def test_on_emit_without_session_or_pending_does_nothing(app):
    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 1})   # 沒有 session

    session = app.store.create("create a project")
    session.state = State.SHOWING
    app._on_emit({"kind": "step_done", "url": DASHBOARD_URL, "ts": 2})   # 有 session、沒有 pending

    assert session.pending is None


async def test_shutdown_closes_the_browser(app, fake_browser):
    await app._ensure_browser()

    await app.shutdown()

    assert ("close",) in fake_browser.calls
    assert await fake_browser.is_alive() is False
    assert app._browser is None


async def test_shutdown_without_browser_does_nothing(app):
    await app.shutdown()   # 不該丟例外


@pytest.mark.parametrize(
    "call",
    [
        lambda app: app.show_step("s_8f2a", "s1-1", "Click New Project", "click", 1, 4),
        lambda app: app.end_tutorial("s_8f2a", "done"),
    ],
)
async def test_tool_methods_are_placeholders_for_now(app, call):
    """A08–A13 會一個一個換掉；換掉之後這個測試會被那一篇刪掉對應的那一行。"""
    assert await call(app) == {"error": "not_implemented"}
