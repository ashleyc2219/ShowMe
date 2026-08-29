"""測試替身：不開瀏覽器的 BrowserLike 實作。

A08–A13 的所有 tool 測試都用它，所以那些測試不需要 browser marker，
跑一輪只要幾毫秒。真的瀏覽器測試在 tests/test_browser_*.py 與
tests/test_e2e_fake_overlay.py。
"""

from __future__ import annotations

from showme.browser import EmitHandler, NavigationFailed


class FakeBrowser:
    def __init__(self, *, fail_urls: set[str] | None = None) -> None:
        self.launched = False
        self.alive = True
        self.url = "about:blank"
        self.page_title = ""
        self.fail_urls = fail_urls or set()   # open() 遇到這些 url 就 raise NavigationFailed
        self.pages: dict[str, dict] = {}      # url → {"title": str, "raw": {"elements": [...], "truncated": bool}}
        self.calls: list[tuple] = []          # ("open", url) / ("snapshot", n) / ("show", opts) / ("clear",) / ("done", text) / ("close",)
        self._handler: EmitHandler | None = None

    # ---- BrowserLike ----

    async def launch(self) -> None:
        self.launched = True

    async def is_alive(self) -> bool:
        return self.alive

    async def open(self, url: str) -> None:
        if url in self.fail_urls:
            raise NavigationFailed(f"cannot open {url}")
        self.calls.append(("open", url))
        self.url = url

    async def current_url(self) -> str:
        return self.url

    async def title(self) -> str:
        return self.pages.get(self.url, {}).get("title", "")

    async def snapshot(self, n: int) -> dict:
        self.calls.append(("snapshot", n))
        raw = self.pages.get(self.url, {}).get("raw", {"elements": [], "truncated": False})
        elements = [dict(element, uid=f"s{n}-{i + 1}") for i, element in enumerate(raw["elements"])]
        return {"elements": elements, "truncated": raw.get("truncated", False)}

    async def show(self, opts: dict) -> None:
        self.calls.append(("show", opts))

    async def clear(self) -> None:
        self.calls.append(("clear",))

    async def done(self, text: str) -> None:
        self.calls.append(("done", text))

    def set_emit_handler(self, handler: EmitHandler | None) -> None:
        self._handler = handler

    async def close(self) -> None:
        self.calls.append(("close",))
        self.alive = False

    # ---- 測試專用的操控方法（BrowserLike 沒有這些，正式程式碼不會呼叫）----

    def emit(self, kind: str, url: str | None = None, ts: int = 0) -> None:
        """模擬頁面呼叫 window.__showme_emit({...})。"""
        if self._handler:
            self._handler({"kind": kind, "url": url or self.url, "ts": ts})

    def navigate(self, url: str) -> None:
        """模擬使用者自己點了什麼、頁面換了。不記進 calls（不是 ShowMe 做的）。"""
        self.url = url

    def add_page(self, url: str, title: str, elements: list[dict], truncated: bool = False) -> None:
        """登記一個假頁面。elements 只要 role/name/testid，uid 由 snapshot(n) 依 n 重編。"""
        self.pages[url] = {"title": title, "raw": {"elements": elements, "truncated": truncated}}
