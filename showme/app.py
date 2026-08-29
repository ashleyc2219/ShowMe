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
        browser = await self._ensure_browser()
        session = self.store.current()
        if session is not None:
            # OQ2（A 的設計決定，可改）：覆蓋時若有一次 show_step 正卡著等使用者，
            # 用 "cancelled" 把它的信箱解掉；那一次 show_step 會回 event="timeout"、page=None。
            pending = session.pending
            if session.state is State.SHOWING and pending is not None and not pending.done():
                pending.set_result({"kind": "cancelled", "url": "", "ts": 0})
            # 舊場次的箭頭還在畫面上，先擦掉再開新頁。這是善後動作，
            # 就算頁面已經跳走、overlay 不在了也不該擋住新的教學，所以吞掉例外。
            try:
                await browser.clear()
            except Exception:
                pass
        try:
            await browser.open(url)
        except NavigationFailed:
            # A 的設計決定（可改）：開不了頁就不留下 Session，回傳空的 session_id。
            self.store.delete()
            return {
                "session_id": "",
                "goal": goal,
                "page": None,
                "next_action": "",
                "error": "navigation_failed",
            }
        if session is None:
            session = self.store.create(goal)
        else:
            session.goal = goal
            session.state = State.READY
            session.steps_shown = 0
            session.snapshot_no = 0
            session.pending = None
            session.latest_page = None
        page = await self._take_snapshot(session)
        return {
            "session_id": session.session_id,
            "goal": session.goal,
            "page": page,
            "next_action": START_NEXT_ACTION,
            "error": "",
        }

    async def inspect_page(self, session_id: str) -> dict[str, object]:
        session = self.store.get(session_id)
        if session is None:
            return {"page": None, "error": "session_not_found"}
        if session.state is State.SHOWING:
            # OQ1（A 的設計決定，可改）：已定案的六個錯誤碼裡沒有 not_ready，
            # 所以 SHOWING 時的 inspect 沿用 show_step_in_progress，不新增錯誤碼。
            return {"page": None, "error": "show_step_in_progress"}
        page = await self._take_snapshot(session)
        return {"page": page, "error": ""}

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
        """對一個 uid 畫 overlay，然後阻塞等到 overlay emit 或 timeout_s 到期。

        回傳永遠有六個鍵：event / signal / elapsed_s / page / next_action / error。
        失敗寫在 error，不丟例外（MCP 呼叫本身仍算成功）。
        """
        # ---------- 前置檢查（A11；每一項都不畫、不加 steps_shown） ----------
        session = self.store.get(session_id)
        if session is None:
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "session_not_found"}
        if session.state is State.SHOWING:
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "show_step_in_progress"}
        if session.steps_shown >= MAX_STEPS:
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "max_steps_exceeded"}
        kind = normalize_kind(kind)
        if expect_text_missing(kind, expect_text):
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": None,
                    "next_action": "", "error": "expect_text_required"}
        if not uid_in_page(uid, session.latest_page):
            # 不畫、steps_shown 不加，但要附一份新鮮 page（snapshot# +1）讓 agent 重挑 uid。
            page = await self._take_snapshot(session)
            return {"event": "", "signal": "", "elapsed_s": 0.0, "page": page,
                    "next_action": "", "error": "uid_not_in_snapshot"}
        timeout_s = normalize_timeout_s(timeout_s)

        # ---------- 畫（A12） ----------
        browser = await self._ensure_browser()
        loop = asyncio.get_running_loop()
        session.pending = loop.create_future()
        session.state = State.SHOWING
        session.steps_shown += 1
        await browser.show({
            "uid": uid,
            "instruction": instruction,
            "kind": kind,
            "index": step_index,
            "total": step_total,
            "expect": expect_text or "",
        })

        # ---------- 等（A12） ----------
        started = loop.time()
        try:
            event = await asyncio.wait_for(asyncio.shield(session.pending), timeout=timeout_s)
        except asyncio.TimeoutError:
            event = None
        elapsed = loop.time() - started

        # 被 start_tutorial 覆蓋掉了（A 的設計決定 OQ2，可改）：
        # 這一次不再碰瀏覽器、也不再碰 Session，因為 start_tutorial 已經接手重設了。
        if event is not None and event.get("kind") == "cancelled":
            return {"event": "timeout", "signal": "", "elapsed_s": round(elapsed, 1),
                    "page": None, "next_action": "", "error": ""}

        if event is None or elapsed >= timeout_s:
            result_event = "timeout"
            await browser.clear()          # A 的設計決定 A-3：只有 timeout 才主動清
        else:
            result_event = event["kind"]   # "step_done" 或 "stuck"

        # ---------- 收尾（A12） ----------
        session.pending = None
        session.state = State.READY
        page = await self._take_snapshot(session)
        return {"event": result_event, "signal": "", "elapsed_s": round(elapsed, 1),
                "page": page, "next_action": STEP_NEXT_ACTION, "error": ""}

    async def end_tutorial(self, session_id: str, summary: str) -> dict[str, object]:
        """清掉 overlay、貼上固定的完成 banner、刪掉 Session。

        summary 只是給呼叫端自己記錄用的，規格明訂它不影響 banner 文案，
        所以這裡刻意完全不使用它。瀏覽器不關（A 的設計決定 A-2，可改）：
        人要留在畫面上看到那句 ✅。
        """
        session = self.store.get(session_id)
        if session is None:
            return {"ok": False, "error": "session_not_found"}

        # OQ1（A 的設計決定，可改）：正在等人做事就不准收攤，重用既有的錯誤碼。
        if session.state is State.SHOWING:
            return {"ok": False, "error": "show_step_in_progress"}

        browser = await self._ensure_browser()
        await browser.clear()
        await browser.done(DONE_BANNER_TEXT)
        self.store.delete()
        return {"ok": True, "error": ""}

    # ---- 收尾 ----

    async def shutdown(self) -> None:
        """關瀏覽器（process 結束時用）。"""
        if self._browser is None:
            return
        await self._browser.close()
        self._browser = None
