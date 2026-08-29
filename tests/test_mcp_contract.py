"""A14：MCP 契約測試。

用官方 SDK 的 in-memory Client 連上 showme server，驗「對外露出的形狀」：
四個 tool、沒有 wait_for_user、失敗走 error 欄不走 protocol error、
show_step 的參數 schema、instructions 有帶。

不開瀏覽器（mcp_client fixture 已經把 app 換成用 FakeBrowser 的）。
"""

from __future__ import annotations

import pytest

from showme.server import INSTRUCTIONS

pytestmark = pytest.mark.anyio

TOOL_NAMES = {"start_tutorial", "inspect_page", "show_step", "end_tutorial"}

SHOW_STEP_PARAMS = {
    "session_id", "uid", "instruction", "kind",
    "step_index", "step_total", "expect_text", "timeout_s",
}
SHOW_STEP_REQUIRED = {
    "session_id", "uid", "instruction", "kind", "step_index", "step_total",
}


def payload(result) -> dict:
    """把 CallToolResult 攤成 tool 實際回傳的那個 dict。

    官方文件（https://py.sdk.modelcontextprotocol.io/v2/servers/structured-output）：
    「Dictionaries with string keys are treated as JSON objects and are not wrapped
    in a result object.」——所以 structured_content 就是我們 return 的那個 dict；
    純量／list／tuple 才會被包成 {"result": ...}。

    **本專案實測（mcp 2.1.1）**：四個 tool 的回傳註記是 `dict[str, object]`，
    `structured_content` 就是**裸 dict**（例如 {'page': None, 'error': 'session_not_found'}），
    沒有被包成 {"result": ...}。註記若寫成沒有型別參數的裸 `dict`，SDK 推不出
    output schema，`structured_content` 會直接變 `None`——見
    docs/plan/report/2026-08-29-階段1_A01環境建置-REP.md Step 10。

    這裡仍然接受被包一層的形狀：契約測試該鎖的是 error 欄位的值，不是 SDK 的包裝細節。
    """
    sc = result.structured_content
    assert sc is not None, (
        f"structured_content 是 None，代表 tool 丟了例外或回傳註記推不出 schema。"
        f"content={result.content}"
    )
    return sc["result"] if isinstance(sc, dict) and set(sc) == {"result"} else sc


async def _tools_by_name(client) -> dict:
    listed = await client.list_tools()
    return {tool.name: tool for tool in listed.tools}


# --------------------------------------------------------------------------
# 有哪些 tool
# --------------------------------------------------------------------------

async def test_server_exposes_exactly_the_four_tools(mcp_client):
    tools = await _tools_by_name(mcp_client)

    assert set(tools) == TOOL_NAMES
    assert len(tools) == 4


async def test_there_is_no_wait_for_user_tool(mcp_client):
    """MVP 的 Non-Goal：不做第五個 tool、不做 wait_for_user、不做輪詢。"""
    tools = await _tools_by_name(mcp_client)

    assert "wait_for_user" not in tools


async def test_every_tool_has_a_description(mcp_client):
    """docstring 就是 agent 看到的 description，空的等於沒告訴 agent 怎麼用。"""
    tools = await _tools_by_name(mcp_client)

    for name, tool in tools.items():
        assert tool.description, f"{name} 沒有 description（server.py 的 docstring 掉了？）"


# --------------------------------------------------------------------------
# 錯誤走 error 欄，不走 protocol error
# --------------------------------------------------------------------------

async def test_unknown_session_is_a_normal_result_not_a_protocol_error(mcp_client):
    """規格：操作失敗寫在回傳的 error，MCP 呼叫本身仍算成功。"""
    result = await mcp_client.call_tool("inspect_page", {"session_id": "s_missing"})

    assert result.is_error is not True, (
        f"tool 不該丟例外。content={result.content}"
    )
    data = payload(result)
    assert data["error"] == "session_not_found"
    assert data["page"] is None


async def test_end_tutorial_with_unknown_session_also_returns_an_error_field(mcp_client):
    result = await mcp_client.call_tool(
        "end_tutorial", {"session_id": "s_missing", "summary": "create a project"}
    )

    assert result.is_error is not True
    data = payload(result)
    assert data["ok"] is False
    assert data["error"] == "session_not_found"


# --------------------------------------------------------------------------
# show_step 的參數 schema
# --------------------------------------------------------------------------

async def test_show_step_input_schema_has_all_eight_parameters(mcp_client):
    tools = await _tools_by_name(mcp_client)
    schema = tools["show_step"].input_schema

    properties = schema["properties"]
    assert set(properties) == SHOW_STEP_PARAMS
    assert len(properties) == 8


async def test_show_step_expect_text_and_timeout_s_are_optional(mcp_client):
    """expect_text 與 timeout_s 有預設值，agent 可以不傳。"""
    tools = await _tools_by_name(mcp_client)
    schema = tools["show_step"].input_schema

    required = set(schema.get("required", []))
    assert "expect_text" not in required
    assert "timeout_s" not in required
    assert required == SHOW_STEP_REQUIRED


async def test_other_tools_have_the_expected_parameters(mcp_client):
    tools = await _tools_by_name(mcp_client)

    assert set(tools["start_tutorial"].input_schema["properties"]) == {"url", "goal"}
    assert set(tools["inspect_page"].input_schema["properties"]) == {"session_id"}
    assert set(tools["end_tutorial"].input_schema["properties"]) == {"session_id", "summary"}


# --------------------------------------------------------------------------
# instructions
# --------------------------------------------------------------------------

async def test_server_instructions_are_not_empty(mcp_client):
    """instructions 是 SHOW protocol：教、不代做、一次一步、uid 來自最新 page。"""
    assert INSTRUCTIONS.strip() != ""
    assert "you never act for them" in INSTRUCTIONS
    assert "One show_step at a time" in INSTRUCTIONS
    assert "LATEST page.elements" in INSTRUCTIONS
    assert "end_tutorial" in INSTRUCTIONS

    # 這一版 SDK 的 Client 若有把 initialize 的結果留下來，順便確認 instructions
    # 真的送到了對面。官方文件沒有寫死這個屬性名，所以用 getattr 探測，探不到就跳過。
    init = getattr(mcp_client, "initialize_result", None)
    if init is not None and getattr(init, "instructions", None):
        assert init.instructions == INSTRUCTIONS


# --------------------------------------------------------------------------
# 走一次真的 tool call（證明薄殼有接到 app）
# --------------------------------------------------------------------------

async def test_start_tutorial_through_the_mcp_layer(mcp_client):
    result = await mcp_client.call_tool(
        "start_tutorial",
        {"url": "http://localhost:3000/", "goal": "create a project"},
    )

    assert result.is_error is not True
    data = payload(result)
    assert data["error"] == ""
    assert data["goal"] == "create a project"
    assert data["session_id"].startswith("s_")
    assert data["page"]["title"] == "Dashboard"
    assert all(el["uid"].startswith("s1-") for el in data["page"]["elements"])
