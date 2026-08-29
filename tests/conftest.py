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

PAGES_DIR = Path(__file__).parent / "fixtures" / "pages"


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
