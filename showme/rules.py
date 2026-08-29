"""純函數規則：把 agent 傳進來的參數收乾淨、把 overlay 回來的資料補完整。

這個模組刻意保持「純」：
- 不 import 專案裡任何其他模組
- 不碰瀏覽器、不碰 Session、不做 I/O
- 同樣的輸入永遠給同樣的輸出

所以它可以直接呼叫、直接測，不需要任何前置準備。
"""

from __future__ import annotations

# show_step 的 kind 白名單（design §7.3）
KINDS = ("click", "input", "select", "observe")

# page.elements 的硬上限（clarified：依 DOM 走訪順序取前 150，不分 viewport）
MAX_ELEMENTS = 150

# 每一筆元素固定就這四個鍵，一個都不能少（clarified：testid 鍵永遠存在）
ELEMENT_KEYS = ("uid", "role", "name", "testid")


def normalize_timeout_s(value: float | int | None) -> float:
    """把 timeout_s 收成秒數。

    clarified（Step_timeout_s為0或負值時如何處理）：未傳、0、負值都改用預設 120，
    不新增錯誤碼、也不立即 timeout。

    120.0 這個數字同時定義在 showme.session.DEFAULT_TIMEOUT_S；
    這裡刻意寫死而不 import，是為了讓 rules.py 保持「不相依任何模組」。
    tests/test_rules.py 有一條測試把兩邊綁在一起，走鐘會紅。
    """
    if value is None:
        return 120.0
    seconds = float(value)
    if seconds <= 0:
        return 120.0
    return seconds


def normalize_kind(kind: str | None) -> str:
    """把 kind 收成四選一。

    clarified（顯示步驟_kind不屬於四選一時是否操作失敗）：不屬於四者時視為 observe。
    大小寫不同（例如 "CLICK"）也不在白名單裡，一樣走 observe——
    這樣所有「模型亂打」的情況都落在同一條路上，行為好預測。
    """
    if kind in KINDS:
        return kind
    return "observe"


def expect_text_missing(kind: str, expect_text: str | None) -> bool:
    """observe（含由非法 kind 轉入的）卻沒給 expect_text 時回 True。

    呼叫端看到 True 就回 error="expect_text_required"，而且不畫、steps_shown 不加。
    """
    if normalize_kind(kind) != "observe":
        return False
    return expect_text is None or expect_text == ""


def build_page(raw: dict, url: str, title: str) -> dict:
    """把 overlay 回的原始 snapshot 補成一份標準 Page。

    raw 是 window.__showme.snapshot(n) 的回傳：{"elements": [...], "truncated": bool}
    url 與 title 由 Python 這邊補（page.url、await page.title()）。

    做三件事（clarified）：
    1. 只留前 MAX_ELEMENTS（150）筆，依 overlay 給的（＝DOM 走訪）順序，不分 viewport。
    2. 每筆只保留 ELEMENT_KEYS 四個鍵；缺的補空字串——但 uid 缺就不補，
       因為 uid 是 overlay 負責組的，我們不該發明一個。
    3. truncated＝overlay 說截斷了，或原本筆數就超過 150。
    """
    raw_elements = raw.get("elements") or []

    elements = []
    for item in raw_elements[:MAX_ELEMENTS]:
        element = {}
        for key in ELEMENT_KEYS:
            if key in item:
                element[key] = item[key]
            elif key != "uid":
                element[key] = ""
        elements.append(element)

    truncated = bool(raw.get("truncated")) or len(raw_elements) > MAX_ELEMENTS

    return {"url": url, "title": title, "elements": elements, "truncated": truncated}


def uid_in_page(uid: str, page: dict | None) -> bool:
    """uid 是不是這份 page 裡某一筆元素的 uid。

    還沒拍過 page（None）一律 False；呼叫端會回 uid_not_in_snapshot 並附一份新鮮 page。
    """
    if page is None:
        return False
    return any(element.get("uid") == uid for element in page.get("elements", []))


def empty_page() -> dict:
    """一份鍵齊全但沒有元素的 Page。

    每次都回新的 dict，呼叫端改它不會污染下一次。
    """
    return {"url": "", "title": "", "elements": [], "truncated": False}
