"""A05：overlay 注入與 emit 橋。用的是 B 目前的 overlay/overlay.js（stub）。

這兩件事過了，A 和 B 才可以分頭做（docs/handoff.md「過了再分頭」）：
1. reload 之後 window.__showme 仍在
2. 頁面呼叫 window.__showme_emit(...)，Python 收得到

    uv run pytest -m browser tests/test_browser_inject.py -q
"""

from __future__ import annotations

import pytest

from showme.browser import PlaywrightBrowser

pytestmark = [pytest.mark.anyio, pytest.mark.browser]


@pytest.fixture
async def browser():
    """用預設的 overlay_path（也就是 B 的 overlay/overlay.js）。"""
    b = PlaywrightBrowser(headless=True)
    await b.launch()
    try:
        yield b
    finally:
        await b.close()


async def test_overlay_is_injected(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    assert await browser.page.evaluate("typeof window.__showme") == "object"
    assert await browser.page.evaluate("typeof window.__showme.snapshot") == "function"


async def test_overlay_survives_reload(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    await browser.page.reload()

    assert await browser.page.evaluate("typeof window.__showme") == "object"
    assert await browser.page.evaluate("typeof window.__showme.show") == "function"


async def test_emit_function_exists_in_page(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    assert await browser.page.evaluate("typeof window.__showme_emit") == "function"


async def test_emit_reaches_python(browser, static_server):
    received: list[dict] = []
    browser.set_emit_handler(received.append)
    await browser.open(f"{static_server}/dashboard.html")

    await browser.page.evaluate(
        "window.__showme_emit({kind: 'step_done', url: location.href, ts: 1})"
    )

    assert len(received) == 1
    assert received[0]["kind"] == "step_done"
    assert received[0]["ts"] == 1
    assert received[0]["url"].endswith("/dashboard.html")


async def test_emit_still_works_after_reload(browser, static_server):
    received: list[dict] = []
    browser.set_emit_handler(received.append)
    await browser.open(f"{static_server}/dashboard.html")
    await browser.page.reload()

    await browser.page.evaluate(
        "window.__showme_emit({kind: 'stuck', url: location.href, ts: 2})"
    )

    assert [event["kind"] for event in received] == ["stuck"]


async def test_emit_without_handler_does_not_raise(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    result = await browser.page.evaluate(
        "window.__showme_emit({kind: 'step_done', url: location.href, ts: 3})"
    )

    assert result is None
