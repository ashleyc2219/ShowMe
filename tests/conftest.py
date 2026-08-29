"""pytest 共用設定。

A01 只放 anyio_backend；後面的篇章會往這裡加 fixture：
- A04：static_server（用 http.server 起一個本機靜態站，給瀏覽器測試用）
- A07：fake_browser / app / started（不開瀏覽器的測試替身）
- A14：mcp_client（in-memory MCP client）
"""

import pytest


@pytest.fixture
def anyio_backend() -> str:
    """告訴 anyio 的 pytest plugin：async 測試只跑 asyncio 這一種後端。

    anyio 本身也附了一個預設的 anyio_backend fixture，我們自己再寫一份，
    是為了把「只用 asyncio」這個決定寫在看得到的地方——這樣就算之後有人裝了
    trio，測試也不會突然變成每條跑兩輪。
    """
    return "asyncio"
