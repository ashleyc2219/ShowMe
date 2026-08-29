"""ShowMe 的教學邏輯：Session、瀏覽器生命週期、snapshot 世代、等待完成訊號。

showme/server.py 只是把 MCP 的四個 tool 轉呼叫到這裡。
本檔在 A07 建立骨架（內部方法完整、四個 tool 方法先佔位），
A08–A13 一篇換掉一個 tool 方法。

四個 tool 方法的回傳註記寫成 `dict[str, object]` 而不是裸 `dict`：
mcp 2.1.1 是從回傳型別註記推導 output schema 的，裸 `dict` 推不出來，
`structured_content` 會變成 None（實測見
docs/plan/report/2026-08-29-階段1_A01環境建置-REP.md Step 10）。
server.py 那邊必須這樣寫，這裡跟著一致。
"""

from __future__ import annotations

import asyncio
from typing import Callable

from showme.browser import BrowserLike, NavigationFailed, PlaywrightBrowser
from showme.rules import (
    build_page,
    expect_text_missing,
    normalize_kind,
    normalize_timeout_s,
    uid_in_page,
)
from showme.session import (
    DEFAULT_TIMEOUT_S,
    DONE_BANNER_TEXT,
    MAX_STEPS,
    START_NEXT_ACTION,
    STEP_NEXT_ACTION,
    Session,
    SessionStore,
    State,
)

BrowserFactory = Callable[[], BrowserLike]


class ShowMeApp:
    def __init__(self, browser_factory: BrowserFactory = PlaywrightBrowser) -> None:
        self.store = SessionStore()
        self._browser_factory = browser_factory
        self._browser: BrowserLike | None = None

    # ---- 內部：瀏覽器、事件、snapshot ----

    async def _ensure_browser(self) -> BrowserLike:
        """沒有瀏覽器或已死 → 用 factory 建一個、launch()、登記 emit handler。"""
        if self._browser is not None and await self._browser.is_alive():
            return self._browser
        browser = self._browser_factory()
        await browser.launch()
        browser.set_emit_handler(self._on_emit)
        self._browser = browser
        return browser

    def _on_emit(self, event: dict) -> None:
        """只有 current session 在 SHOWING 且 pending 未 done 時才 set_result；

        其他一律忽略（= 每步只取第一筆事件）。
        """
        session = self.store.current()
        if session is None or session.state != State.SHOWING:
            return
        pending = session.pending
        if pending is None or pending.done():
            return
        pending.set_result(event)

    async def _take_snapshot(self, session: Session) -> dict:
        """世代 +1 → 請瀏覽器掃一次 → 組成 Page → 存進 session.latest_page。"""
        browser = await self._ensure_browser()
        session.snapshot_no += 1
        raw = await browser.snapshot(session.snapshot_no)
        page = build_page(raw, await browser.current_url(), await browser.title())
        session.latest_page = page
        return page

    # ---- 四個 MCP tool（A08–A13 逐一實作）----

    async def start_tutorial(self, url: str, goal: str) -> dict[str, object]:
        return {"error": "not_implemented"}

    async def inspect_page(self, session_id: str) -> dict[str, object]:
        return {"error": "not_implemented"}

    async def show_step(
        self,
        session_id: str,
        uid: str,
        instruction: str,
        kind: str,
        step_index: int,
        step_total: int,
        expect_text: str = "",
        timeout_s: float = DEFAULT_TIMEOUT_S,
    ) -> dict[str, object]:
        return {"error": "not_implemented"}

    async def end_tutorial(self, session_id: str, summary: str) -> dict[str, object]:
        return {"error": "not_implemented"}

    # ---- 收尾 ----

    async def shutdown(self) -> None:
        """關瀏覽器（process 結束時用）。"""
        if self._browser is None:
            return
        await self._browser.close()
        self._browser = None
