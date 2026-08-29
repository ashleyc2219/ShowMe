"""A15 加碼：真瀏覽器 + B 的真 overlay 端到端（S7 里程碑）。

跟 tests/test_e2e_fake_overlay.py 的差別只有一個：這裡 **不傳 overlay_path**，
所以注入的是 B 的產品 overlay（showme/browser.py 的預設值 overlay/overlay.js）。

因此「人做完了沒」不再由測試手動 emit，而是真 overlay 自己判斷：
kind="click" 時它會監聽 hashchange / pushState / 目標被移除隱藏，
自己呼叫 window.__showme_emit({kind:"step_done", ...})。
測試只做「人會做的事」——page.click——不碰 __showme_emit。

    uv run pytest -m browser tests/test_e2e_real_overlay.py -q
"""

from __future__ import annotations

import asyncio

import pytest

from showme.app import ShowMeApp
from showme.browser import PlaywrightBrowser
from showme.session import DONE_BANNER_TEXT, State

pytestmark = [pytest.mark.anyio, pytest.mark.browser]


@pytest.fixture
async def real_app():
    """用預設 overlay_path（= B 的 overlay/overlay.js）的 headless ShowMeApp。"""
    app = ShowMeApp(browser_factory=lambda: PlaywrightBrowser(headless=True))
    try:
        yield app
    finally:
        await app.shutdown()


def _collect_console(page) -> list[str]:
    """把頁面的 console 訊息收進 list，測試失敗時當診斷用。"""
    messages: list[str] = []
    page.on("console", lambda msg: messages.append(f"{msg.type}: {msg.text}"))
    return messages


def _link_named(page: dict, name: str) -> dict:
    """真 overlay 的 name 走簡化版 accessible name，用寬鬆比對找連結。"""
    for element in page["elements"]:
        if element["role"] == "link" and name in element["name"]:
            return element
    raise AssertionError(f"page.elements 裡找不到 role=link 且含 {name!r} 的元素：{page['elements']}")


def _button_named(page: dict, name: str) -> dict:
    for element in page["elements"]:
        if element["role"] == "button" and name in element["name"]:
            return element
    raise AssertionError(f"page.elements 裡找不到 role=button 且含 {name!r} 的元素：{page['elements']}")


async def _wait_until_showing(app: ShowMeApp, timeout_s: float = 2.0) -> None:
    """輪詢等 Session 進入 SHOWING（show_step 已經走到畫 overlay 這一步）。"""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        session = app.store.current()
        if session is not None and session.state is State.SHOWING:
            return
        await asyncio.sleep(0.02)
    raise AssertionError(f"等了 {timeout_s} 秒，Session 還沒進入 SHOWING")


async def _wait_for_highlight(page, console: list[str], timeout_s: float = 3.0) -> None:
    """輪詢等 Driver.js 的 popover 出現。

    popover 出現代表 show() 已經在頁面裡跑完 highlight()，
    而 overlay 的 observe()（掛完成條件的 listener）就緊接在 highlight() 之後，
    所以這時候再去「點」才不會點在 listener 掛好之前。
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    while loop.time() < deadline:
        if await page.evaluate("() => !!document.querySelector('.driver-popover')"):
            return
        await asyncio.sleep(0.05)
    raise AssertionError(f"等了 {timeout_s} 秒，Driver.js 的 popover 沒出現。console={console}")


# --------------------------------------------------------------------------
# 主線（S7）：人真的去點，真 overlay 自己 emit，show_step 才回來
# --------------------------------------------------------------------------


async def test_real_overlay_end_to_end_user_clicks_settings(real_app, static_server):
    app = real_app
    url = f"{static_server}/dashboard.html"

    # ---- start_tutorial：真 overlay 的 snapshot ----
    start = await app.start_tutorial(url, "open settings")

    assert start["error"] == ""
    page_data = start["page"]
    assert page_data["url"].endswith("/dashboard.html")
    for element in page_data["elements"]:
        assert set(element) == {"uid", "role", "name", "testid"}
        assert element["uid"].startswith("s1-")

    settings = _link_named(page_data, "Settings")
    uid = settings["uid"]

    browser_page = app._browser.page
    console = _collect_console(browser_page)

    # ---- show_step：真 overlay 用 Driver.js 高亮，然後 Python 卡住 ----
    task = asyncio.create_task(
        app.show_step(start["session_id"], uid, "Click Settings", "click", 1, 1, timeout_s=5)
    )
    await _wait_until_showing(app)
    await _wait_for_highlight(browser_page, console)

    assert not task.done(), f"show_step 應該還卡著等真 overlay emit。console={console}"

    # ---- 模擬「人的動作」：真的去點那個連結 ----
    # location.hash 會變 → 真 overlay 的 hashchange 監聽 → 它自己 emit step_done
    await browser_page.click('a[href="#settings"]')
    result = await task

    assert result["event"] == "step_done", f"真 overlay 沒有 emit。console={console}"
    assert result["error"] == ""
    assert result["page"]["url"].endswith("#settings")
    assert all(element["uid"].startswith("s2-") for element in result["page"]["elements"])
    assert app.store.current().state is State.READY

    # ---- end_tutorial：真 overlay 的 clear() + done() ----
    ended = await app.end_tutorial(start["session_id"], "whatever")

    assert ended["ok"] is True
    body_text = await browser_page.evaluate("() => document.body.innerText")
    assert DONE_BANNER_TEXT in body_text, f"完成 banner 沒出現在畫面上。console={console}"

    # ---- 再 end 一次：Session 已經刪掉了 ----
    again = await app.end_tutorial(start["session_id"], "whatever")

    assert again["ok"] is False
    assert again["error"] == "session_not_found"
    assert app.store.current() is None


# --------------------------------------------------------------------------
# 支線：沒人動作 → Python 自己 timeout，真 overlay 的 clear() 不會炸
# --------------------------------------------------------------------------


async def test_real_overlay_timeout_clears_without_error(real_app, static_server):
    app = real_app

    start = await app.start_tutorial(f"{static_server}/dashboard.html", "create a project")
    uid = _button_named(start["page"], "New Project")["uid"]

    browser_page = app._browser.page
    console = _collect_console(browser_page)

    task = asyncio.create_task(
        app.show_step(
            start["session_id"], uid, "Click New Project", "click", 1, 1, timeout_s=1
        )
    )
    await _wait_until_showing(app)
    await _wait_for_highlight(browser_page, console)

    # 什麼都不點，讓 Python 這邊的計時器到期
    result = await task

    assert result["event"] == "timeout", f"不該有人 emit。console={console}"
    assert result["error"] == "", "timeout 是 event，不是 error；clear() 也不該炸"
    assert result["elapsed_s"] >= 1
    assert app.store.current().state is State.READY

    # 真 overlay 的 clear() 會 teardown Driver.js，高亮要消失
    assert await browser_page.evaluate(
        "() => !document.querySelector('.driver-popover')"
    ), f"clear() 之後 Driver.js 的 popover 應該不見了。console={console}"
