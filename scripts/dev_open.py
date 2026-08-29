"""手動驗證用：開一個 headed 瀏覽器、走到指定 url、停 10 秒再關。

用法：
    uv run python scripts/dev_open.py http://localhost:3000
    uv run python scripts/dev_open.py https://example.com
"""

from __future__ import annotations

import asyncio
import sys

from showme.browser import NavigationFailed, PlaywrightBrowser


async def main(url: str) -> int:
    browser = PlaywrightBrowser(headless=False)
    await browser.launch()
    try:
        await browser.open(url)
    except NavigationFailed as exc:
        print(f"navigation_failed: {exc}")
        await browser.close()
        return 1
    print(f"opened : {await browser.current_url()}")
    print(f"title  : {await browser.title()}")
    print("視窗會停留 10 秒，請用眼睛確認畫面。")
    await asyncio.sleep(10)
    await browser.close()
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法：uv run python scripts/dev_open.py <url>")
        raise SystemExit(2)
    raise SystemExit(asyncio.run(main(sys.argv[1])))
