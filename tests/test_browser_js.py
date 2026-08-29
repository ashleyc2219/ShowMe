"""A06：snapshot / show / clear / done 四個 evaluate 包裝。

注入的是 tests/fixtures/fake_overlay.js（A 側測試替身），不是 B 的產品 overlay。
所以這個檔在 B 完成之前就能全綠。

    uv run pytest -m browser tests/test_browser_js.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

from showme.browser import PlaywrightBrowser

pytestmark = [pytest.mark.anyio, pytest.mark.browser]

FAKE_OVERLAY = Path(__file__).parent / "fixtures" / "fake_overlay.js"
DONE_TEXT = "✅ Done — you created a project"


@pytest.fixture
async def browser():
    b = PlaywrightBrowser(overlay_path=FAKE_OVERLAY, headless=True)
    await b.launch()
    try:
        yield b
    finally:
        await b.close()


async def test_snapshot_returns_elements_with_all_four_keys(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    raw = await browser.snapshot(1)

    assert raw["truncated"] is False
    assert raw["elements"] == [
        {"uid": "s1-1", "role": "button", "name": "New Project", "testid": "new-project"},
        {"uid": "s1-2", "role": "link", "name": "Settings", "testid": ""},
    ]


async def test_snapshot_number_flows_into_uid(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    raw = await browser.snapshot(2)

    assert [element["uid"] for element in raw["elements"]] == ["s2-1", "s2-2"]


async def test_snapshot_writes_uid_back_to_dom(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")
    await browser.snapshot(1)

    attribute = await browser.page.evaluate(
        "document.querySelector('button').getAttribute('data-showme-uid')"
    )

    assert attribute == "s1-1"


async def test_element_without_a11y_name_still_listed(browser, static_server):
    await browser.open(f"{static_server}/new_project.html")

    raw = await browser.snapshot(1)

    assert [element["role"] for element in raw["elements"]] == ["heading", "textbox", "button"]
    assert raw["elements"][1] == {
        "uid": "s1-2",
        "role": "textbox",
        "name": "",
        "testid": "project-name",
    }


async def test_snapshot_truncates_at_150(browser, static_server):
    await browser.open(f"{static_server}/many_buttons.html")

    raw = await browser.snapshot(1)

    assert len(raw["elements"]) == 150
    assert raw["truncated"] is True
    assert raw["elements"][0]["name"] == "Button 1"
    assert raw["elements"][-1]["uid"] == "s1-150"
    assert raw["elements"][-1]["name"] == "Button 150"


async def test_show_marks_the_page_and_clear_removes_it(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")
    await browser.snapshot(1)

    await browser.show(
        {
            "uid": "s1-1",
            "instruction": "Click New Project",
            "kind": "click",
            "index": 1,
            "total": 4,
            "expect": "",
        }
    )
    showing = await browser.page.evaluate(
        "document.body.getAttribute('data-showme-showing')"
    )

    await browser.clear()
    cleared = await browser.page.evaluate(
        "document.body.getAttribute('data-showme-showing')"
    )

    assert showing == "s1-1"
    assert cleared is None


async def test_show_receives_all_six_keys(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")
    opts = {
        "uid": "s1-2",
        "instruction": "Read the heading",
        "kind": "observe",
        "index": 3,
        "total": 5,
        "expect": "Settings",
    }

    await browser.show(opts)

    recorded = await browser.page.evaluate(
        "window.__showme._calls.filter((c) => c[0] === 'show').map((c) => c[1])"
    )
    assert recorded == [opts]


async def test_done_inserts_the_banner(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    await browser.done(DONE_TEXT)

    text = await browser.page.evaluate(
        "document.getElementById('showme-banner').textContent"
    )
    assert text == DONE_TEXT
