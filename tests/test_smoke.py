"""A01 煙霧測試：確認現有骨架真的接得起來。

用 in-memory client（不開子行程、不走 stdio）連上 showme 的 MCPServer，
確認它剛好註冊四個 tool，而且沒有 wait_for_user。
"""

import pytest
from mcp import Client

from showme.server import mcp

pytestmark = pytest.mark.anyio

# design §7：Server 名稱 showme，只有這四個工具
EXPECTED_TOOLS = {"start_tutorial", "inspect_page", "show_step", "end_tutorial"}


async def test_server_exposes_exactly_the_four_tools():
    # docs/spec/features/開始教學.feature、顯示步驟.feature、檢查頁面.feature、結束教學.feature
    # 各對應一個 tool；多一個少一個都是契約壞掉
    async with Client(mcp) as client:
        result = await client.list_tools()

    assert {tool.name for tool in result.tools} == EXPECTED_TOOLS


async def test_server_does_not_expose_wait_for_user():
    # docs/spec/features/等待使用者.feature：
    # 「MVP 不提供 wait_for_user，顯示步驟改為畫出 overlay 後阻塞直到完成或逾時」
    async with Client(mcp) as client:
        result = await client.list_tools()

    assert "wait_for_user" not in {tool.name for tool in result.tools}
