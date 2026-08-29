"""Playwright 瀏覽器層：ShowMe 唯一碰瀏覽器的檔案。

上層（showme/app.py）只依賴 BrowserLike 這個介面，所以測試可以換成
tests/fakes.py 的 FakeBrowser，不必真的開瀏覽器。

本檔在 A04 建立（開頁），A05 補注入與 emit 橋，A06 補四個 JS 呼叫。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from playwright.async_api import async_playwright

OVERLAY_PATH = Path(__file__).resolve().parent.parent / "overlay" / "overlay.js"
EMIT_FUNCTION_NAME = "__showme_emit"
EmitHandler = Callable[[dict], None]


class NavigationFailed(Exception):
    """page.goto 丟錯時由 open() 轉成這個。"""


class BrowserLike(Protocol):
    """app.py 只依賴這個介面；真的 PlaywrightBrowser 與測試用 FakeBrowser 都實作它。"""

    async def launch(self) -> None: ...
    async def is_alive(self) -> bool: ...
    async def open(self, url: str) -> None: ...
    async def current_url(self) -> str: ...
    async def title(self) -> str: ...
    async def snapshot(self, n: int) -> dict: ...
    async def show(self, opts: dict) -> None: ...
    async def clear(self) -> None: ...
    async def done(self, text: str) -> None: ...
    def set_emit_handler(self, handler: EmitHandler | None) -> None: ...
    async def close(self) -> None: ...


class PlaywrightBrowser:
    def __init__(self, overlay_path: Path = OVERLAY_PATH, headless: bool = False) -> None:
        self.overlay_path = overlay_path
        self.headless = headless
        self.page = None        # playwright Page；測試會直接用它 evaluate
        self._pw = None
        self._browser = None
        self._context = None
        self._emit_handler: EmitHandler | None = None

    async def launch(self) -> None:
        self._pw = await async_playwright().start()
        try:
            self._browser = await self._pw.chromium.launch(
                channel="chrome", headless=self.headless
            )
        except Exception:
            self._browser = await self._pw.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context()
        await self._context.add_init_script(path=self.overlay_path)
        await self._context.expose_function(EMIT_FUNCTION_NAME, self._on_emit)
        self.page = await self._context.new_page()

    def _on_emit(self, event: dict) -> None:
        if self._emit_handler is None:
            return
        self._emit_handler(event)

    async def is_alive(self) -> bool:
        if self.page is None or self._browser is None:
            return False
        return not self.page.is_closed() and self._browser.is_connected()

    async def open(self, url: str) -> None:
        try:
            await self.page.goto(url)
        except Exception as exc:
            raise NavigationFailed(str(exc)) from exc

    async def current_url(self) -> str:
        return self.page.url

    async def title(self) -> str:
        return await self.page.title()

    async def snapshot(self, n: int) -> dict:
        return await self.page.evaluate("(n) => window.__showme.snapshot(n)", n)

    async def show(self, opts: dict) -> None:
        await self.page.evaluate("(o) => window.__showme.show(o)", opts)

    async def clear(self) -> None:
        await self.page.evaluate("() => window.__showme.clear()")

    async def done(self, text: str) -> None:
        await self.page.evaluate("(t) => window.__showme.done(t)", text)

    def set_emit_handler(self, handler: EmitHandler | None) -> None:
        self._emit_handler = handler

    async def close(self) -> None:
        for closeable in (self._context, self._browser):
            if closeable is None:
                continue
            try:
                await closeable.close()
            except Exception:
                pass
        if self._pw is not None:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self.page = None
        self._context = None
        self._browser = None
        self._pw = None
