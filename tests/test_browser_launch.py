"""A04：PlaywrightBrowser 開得起來、走得到頁、開不了時丟 NavigationFailed。

這裡的測試會真的啟動一顆 headless 瀏覽器，所以標了 browser marker：
    uv run pytest -m browser            只跑會開瀏覽器的
    uv run pytest -m "not browser"      跳過它們（平常寫邏輯時用這個，比較快）
"""

from __future__ import annotations

import pytest

from showme.browser import NavigationFailed, PlaywrightBrowser

pytestmark = [pytest.mark.anyio, pytest.mark.browser]


@pytest.fixture
async def browser():
    """每個測試給一顆乾淨的 headless 瀏覽器，測完一定關掉。"""
    b = PlaywrightBrowser(headless=True)
    await b.launch()
    try:
        yield b
    finally:
        await b.close()


async def test_launched_browser_is_alive(browser):
    assert await browser.is_alive() is True


async def test_open_static_page_reports_url_and_title(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    assert await browser.current_url() == f"{static_server}/dashboard.html"
    assert await browser.title() == "Dashboard"


async def test_open_unreachable_url_raises_navigation_failed(browser):
    with pytest.raises(NavigationFailed):
        await browser.open("http://localhost:1")


async def test_is_alive_is_false_after_close(browser):
    await browser.close()

    assert await browser.is_alive() is False
