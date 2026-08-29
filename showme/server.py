"""MCP stdio 進入點：只做轉接，邏輯全在 showme/app.py。

四個 tool 的回傳註記是 `dict[str, object]` 而不是裸 `dict`：
mcp 2.1.1 從回傳型別註記推導 output schema，裸 `dict` 推不出 schema，
`structured_content` 就會是 None（A01 Step 10 實測；見
docs/plan/report/2026-08-29-階段1_A01環境建置-REP.md）。
寫成 `dict[str, object]` 才會拿到裸 dict（不包 {"result": ...}）。
"""

from mcp.server import MCPServer

from showme.app import ShowMeApp

INSTRUCTIONS = """You are TEACHING the user how to use the app; you never act for them.
- You have no click/type/navigate tools. You only look (start_tutorial / inspect_page) and point (show_step).
- Plan 3-8 steps in your head, but pick each step's uid from the LATEST page.elements only. Never reuse a uid from an older snapshot.
- One show_step at a time; wait for it to return before deciding the next step.
- instruction: second person, one sentence, use the words visible on screen (e.g. "Click New Project").
- If event is "stuck": call show_step again with the SAME uid and a plainer instruction.
- If error is "uid_not_in_snapshot": re-pick a uid from the returned page.
- Call end_tutorial only when the page shows the goal is achieved.
"""

mcp = MCPServer("showme", instructions=INSTRUCTIONS)

_app: ShowMeApp | None = None


def get_app() -> ShowMeApp:
    global _app
    if _app is None:
        _app = ShowMeApp()
    return _app


def set_app(app: ShowMeApp | None) -> None:   # 測試用：換成用 FakeBrowser 的 app
    global _app
    _app = app


@mcp.tool()
async def start_tutorial(url: str, goal: str) -> dict[str, object]:
    """Open the app in a headed browser, inject the overlay, start (or restart) the single tutorial session, and return the first condensed page snapshot (uids s1-*)."""
    return await get_app().start_tutorial(url, goal)


@mcp.tool()
async def inspect_page(session_id: str) -> dict[str, object]:
    """Re-snapshot the current page (snapshot# +1) without drawing anything. Use it when a uid was rejected or the page changed."""
    return await get_app().inspect_page(session_id)


@mcp.tool()
async def show_step(session_id: str, uid: str, instruction: str, kind: str, step_index: int, step_total: int,
                    expect_text: str = "", timeout_s: float = 120) -> dict[str, object]:
    """Highlight one uid from the latest page and BLOCK until the user finishes the step (event=step_done), presses I'm stuck (stuck), or timeout_s elapses (timeout). Returns a fresh page. kind: click|input|select|observe (observe needs expect_text)."""
    return await get_app().show_step(session_id, uid, instruction, kind, step_index, step_total, expect_text, timeout_s)


@mcp.tool()
async def end_tutorial(session_id: str, summary: str) -> dict[str, object]:
    """Clear the overlay, show the fixed done banner, and delete the session."""
    return await get_app().end_tutorial(session_id, summary)
