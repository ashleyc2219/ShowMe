"""pytest 共用設定。

A01 只放 anyio_backend；後面的篇章會往這裡加 fixture：
- A04：static_server（用 http.server 起一個本機靜態站，給瀏覽器測試用）
- A07：fake_browser / app / started（不開瀏覽器的測試替身）
- A14：mcp_client（in-memory MCP client）
"""

from __future__ import annotations

import http.server
import threading
from functools import partial
from pathlib import Path

import pytest
from mcp import Client

from fakes import FakeBrowser
from showme.app import ShowMeApp
from showme.server import mcp as server_mcp
from showme.server import set_app

PAGES_DIR = Path(__file__).parent / "fixtures" / "pages"

DASHBOARD_URL = "http://localhost:3000/"
NEW_PROJECT_URL = "http://localhost:3000/projects/new"


@pytest.fixture
def anyio_backend() -> str:
    """告訴 anyio 的 pytest plugin：async 測試只跑 asyncio 這一種後端。

    anyio 本身也附了一個預設的 anyio_backend fixture，我們自己再寫一份，
    是為了把「只用 asyncio」這個決定寫在看得到的地方——這樣就算之後有人裝了
    trio，測試也不會突然變成每條跑兩輪。
    """
    return "asyncio"


@pytest.fixture(scope="session")
def static_server():
    """在 127.0.0.1 的隨機 port 上，用一條背景執行緒送出 tests/fixtures/pages/ 底下的檔案。

    yield 出來的是網址前綴，例如 "http://127.0.0.1:52341"。
    測試裡這樣用：await browser.open(f"{static_server}/dashboard.html")
    """
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(PAGES_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def fake_browser() -> FakeBrowser:
    """預先放好兩個假頁面：Dashboard 與 New Project。

    元素只寫 role / name / testid；uid 由 FakeBrowser.snapshot(n) 依 n 重編。
    """
    browser = FakeBrowser()
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


@pytest.fixture
def app(fake_browser: FakeBrowser) -> ShowMeApp:
    """一個用 FakeBrowser 的 ShowMeApp。factory 每次都回同一顆假瀏覽器，

    所以測試可以直接對 fake_browser 下指令（emit / navigate），
    也可以讀它的 calls。
    """
    return ShowMeApp(browser_factory=lambda: fake_browser)


@pytest.fixture
async def started(app: ShowMeApp, fake_browser: FakeBrowser):
    """已經 start_tutorial 過的 (app, fake_browser, result)。

    注意：A07 的 start_tutorial 還是佔位版本（回 {"error": "not_implemented"}），
    所以這個 fixture 要到 A08 之後才真的有用。先建好，A08 起就直接拿來用。
    """
    result = await app.start_tutorial(DASHBOARD_URL, "create a project")
    return app, fake_browser, result


@pytest.fixture
async def mcp_client(app: ShowMeApp):
    """一個連上 showme server 的 in-memory MCP client（A14）。

    server.py 的 tool 走的是 module-level 的 get_app()，預設會 new 一個
    用真 PlaywrightBrowser 的 ShowMeApp。這裡先用 set_app() 把它換成
    上面的 `app` fixture（用 FakeBrowser），所以契約測試不會開瀏覽器。
    測完再 set_app(None) 還原，免得污染其他測試。
    """
    set_app(app)
    try:
        async with Client(server_mcp) as client:
            yield client
    finally:
        set_app(None)
