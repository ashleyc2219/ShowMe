"""A15：真瀏覽器端到端（Python 側）。

開一顆真的 headless Chromium，注入「A 側的測試替身」fake_overlay.js，
走完 start_tutorial → show_step(step_done) → end_tutorial → 再 end_tutorial。

⚠️ tests/fixtures/fake_overlay.js 不是 B 的產品 overlay。
   它只實作 window.__showme 的四個方法、不畫 Driver.js 箭頭、不自己判定完成；
   emit 由測試用 page.evaluate 手動觸發。
   要驗 B 的真 overlay 走完整條流程，看 tests/test_e2e_real_overlay.py。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from showme.app import ShowMeApp
from showme.browser import PlaywrightBrowser
from showme.session import DONE_BANNER_TEXT, STEP_NEXT_ACTION, State

pytestmark = [pytest.mark.anyio, pytest.mark.browser]

FAKE_OVERLAY = Path(__file__).parent / "fixtures" / "fake_overlay.js"


@pytest.fixture
async def e2e_app():
    """一個用真 PlaywrightBrowser（headless + 假 overlay）的 ShowMeApp。

    每個測試各拿一顆自己的瀏覽器，測完一定關掉。
    """
    app = ShowMeApp(
        browser_factory=lambda: PlaywrightBrowser(
            overlay_path=FAKE_OVERLAY, headless=True
        )
    )
    try:
        yield app
    finally:
        await app.shutdown()


def _uid_of(page: dict, name: str) -> str:
    """從 page.elements 裡照 a11y name 找 uid。不要在測試裡硬寫 's1-1'。"""
    return _element_of(page, name)["uid"]


def _element_of(page: dict, name: str) -> dict:
    for element in page["elements"]:
        if element["name"] == name:
            return element
    raise AssertionError(f"page.elements 裡找不到 name={name!r}：{page['elements']}")


async def _wait_until_showing(page, uid: str, timeout_s: float = 5.0) -> None:
    """輪詢等到 body 的 data-showme-showing 變成這個 uid。

    show() 要跨行程送到瀏覽器再執行，有真實的 IO 延遲，
    所以不能只用 await asyncio.sleep(0) 讓一下就假設它畫好了。
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout_s
    seen = None
    while loop.time() < deadline:
        seen = await page.evaluate("() => document.body.dataset.showmeShowing || ''")
        if seen == uid:
            return
        await asyncio.sleep(0.05)
    raise AssertionError(
        f"等了 {timeout_s} 秒，body 的 data-showme-showing 還是 {seen!r}，不是 {uid!r}"
    )


async def _read_banner(page) -> str | None:
    return await page.evaluate(
        "() => { const el = document.getElementById('showme-banner');"
        " return el ? el.textContent : null; }"
    )


# --------------------------------------------------------------------------
# 主線：start → show_step（人做完）→ end → 再 end
# --------------------------------------------------------------------------


async def test_end_to_end_happy_path(e2e_app, static_server):
    app = e2e_app
    url = f"{static_server}/dashboard.html"

    # ---- start_tutorial：開頁、注入 overlay、拍第一份 snapshot ----
    start = await app.start_tutorial(url, "create a project")

    assert start["error"] == ""
    assert start["goal"] == "create a project"
    assert start["session_id"].startswith("s_")

    page_data = start["page"]
    assert page_data["url"].endswith("/dashboard.html")
    assert page_data["title"] == "Dashboard"
    assert page_data["truncated"] is False

    new_project = _element_of(page_data, "New Project")
    settings = _element_of(page_data, "Settings")
    assert new_project["role"] == "button"
    assert new_project["testid"] == "new-project"
    assert settings["role"] == "link"
    assert settings["testid"] == "", "沒有 data-testid 時鍵仍在、值是空字串"
    assert all(el["uid"].startswith("s1-") for el in page_data["elements"])

    uid = new_project["uid"]
    browser_page = app._browser.page  # 測試才這樣摸私有屬性，產品程式碼不會

    # ---- show_step：畫出來、卡住等 emit ----
    task = asyncio.create_task(
        app.show_step(
            start["session_id"], uid, "Click New Project", "click", 1, 3, timeout_s=5
        )
    )
    await _wait_until_showing(browser_page, uid)

    assert not task.done(), "show_step 應該還卡在等 emit"
    assert app.store.current().state is State.SHOWING
    assert app.store.current().steps_shown == 1

    # ---- 模擬「人做完了」：頁面呼叫 window.__showme_emit ----
    await browser_page.evaluate(
        "() => window.__showme_emit({kind: 'step_done', url: location.href, ts: Date.now()})"
    )
    result = await task

    assert result["event"] == "step_done"
    assert result["error"] == ""
    assert result["signal"] == ""
    assert result["next_action"] == STEP_NEXT_ACTION
    assert isinstance(result["elapsed_s"], float)
    assert all(
        el["uid"].startswith("s2-") for el in result["page"]["elements"]
    ), "show_step 回傳的一定是新一代 snapshot"
    assert app.store.current().state is State.READY

    # ---- end_tutorial：清 overlay、貼固定 banner、刪 Session ----
    ended = await app.end_tutorial(start["session_id"], "invite a member")

    assert ended["ok"] is True
    assert ended["error"] == ""
    assert await _read_banner(browser_page) == DONE_BANNER_TEXT, (
        "banner 文案固定，summary（invite a member）不進橫幅"
    )
    assert (
        await browser_page.evaluate("() => document.body.dataset.showmeShowing || ''")
        == ""
    ), "end 之前先 clear()，箭頭標記要被拿掉"

    # ---- 再 end 一次：Session 已經刪掉了 ----
    again = await app.end_tutorial(start["session_id"], "invite a member")

    assert again["ok"] is False
    assert again["error"] == "session_not_found"
    assert app.store.current() is None

    # 瀏覽器還活著（A 的設計決定 A-2，可改）：人要留在畫面上看 banner
    assert not browser_page.is_closed()


# --------------------------------------------------------------------------
# 支線：沒有人來 emit，Python 這邊自己計時
# --------------------------------------------------------------------------


async def test_show_step_times_out_and_clears_the_overlay(e2e_app, static_server):
    app = e2e_app
    url = f"{static_server}/dashboard.html"

    start = await app.start_tutorial(url, "create a project")
    uid = _uid_of(start["page"], "New Project")
    browser_page = app._browser.page

    task = asyncio.create_task(
        app.show_step(
            start["session_id"], uid, "Click New Project", "click", 1, 3, timeout_s=0.5
        )
    )
    await _wait_until_showing(browser_page, uid)

    # 什麼都不做，等 Python 這邊的計時器到期
    result = await task

    assert result["event"] == "timeout"
    assert result["error"] == "", "timeout 是 event，不是 error"
    assert result["elapsed_s"] >= 0.5
    assert result["page"] is not None
    assert all(el["uid"].startswith("s2-") for el in result["page"]["elements"])
    assert app.store.current().state is State.READY

    # timeout 之後要清 overlay（A 的設計決定 A-3，可改）
    assert (
        await browser_page.evaluate("() => document.body.dataset.showmeShowing || ''")
        == ""
    )
