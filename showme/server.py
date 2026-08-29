"""MCP stdio entry. Fill tool bodies in later slices; do not raise — return `error`."""

from mcp.server import MCPServer

mcp = MCPServer(
    "showme",
    instructions=(
        "Teach by pointing. Do not click or type for the user. "
        "One show_step at a time. uid must come from the latest page."
    ),
)


@mcp.tool()
async def start_tutorial(url: str, goal: str) -> dict:
    """Open the app and return the first page snapshot."""
    return {"error": "not_implemented"}


@mcp.tool()
async def inspect_page(session_id: str) -> dict:
    """Re-snapshot the current page without drawing an overlay."""
    return {"error": "not_implemented"}


@mcp.tool()
async def show_step(
    session_id: str,
    uid: str,
    instruction: str,
    kind: str,
    step_index: int,
    step_total: int,
    expect_text: str = "",
    timeout_s: float = 120,
) -> dict:
    """Highlight one uid and wait until the user finishes, is stuck, or times out."""
    return {"error": "not_implemented"}


@mcp.tool()
async def end_tutorial(session_id: str, summary: str) -> dict:
    """Clear overlay, show the done banner, delete the session."""
    return {"error": "not_implemented"}
