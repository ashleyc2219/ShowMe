"""教學場次（Session）的資料模型與存放處。

規格重點（docs/spec/erm.dbml、docs/design/showme.md §8）：
- 同一個 process 同時只有一個 Session，存在記憶體裡，不是資料庫。
- 沒有 ttl：場次不會自己過期。
- end_tutorial 成功後直接刪除 Session，不保留 DONE 狀態。

這個模組是整包最底層：不 import 專案內其他模組、不做 I/O、不碰瀏覽器。
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass
from enum import Enum

# 一場教學最多畫幾步（erm.dbml：max_steps = 12）
MAX_STEPS = 12

# show_step 沒給 timeout_s（或給 0、負值）時用的秒數（erm.dbml：step_timeout = 120 s）
DEFAULT_TIMEOUT_S = 120.0

# end_tutorial 的完成橫幅，文案固定、忽略 summary（結束教學.feature）
DONE_BANNER_TEXT = "✅ Done — you created a project"

# 回給 agent 的下一步提示（design §5：沿用 draft 舉例字串，不是驗收字）
START_NEXT_ACTION = (
    "Plan 3–8 steps in your head, then call show_step for the FIRST step "
    "using a uid from page.elements."
)
STEP_NEXT_ACTION = (
    "If the goal is not yet achieved, call show_step for the next step using a uid "
    "from page.elements. If the page shows the goal is achieved, call end_tutorial."
)


class State(str, Enum):
    """場次的實務狀態。

    只有兩個：READY（可以 inspect / show / end）與 SHOWING（正在等使用者）。
    erm 裡的 IDLE 代表「根本沒有 Session 物件」，不是這裡的一個值；
    也沒有 DONE——end_tutorial 成功後 Session 直接被刪掉。
    """

    READY = "READY"
    SHOWING = "SHOWING"


@dataclass
class Session:
    """一場教學。欄位對應 erm.dbml 的 Session 表，外加三個實作用的握把。"""

    session_id: str
    goal: str
    state: State = State.READY
    steps_shown: int = 0
    # 目前最新 snapshot 的世代號。start_tutorial 成功後是 1，之後每拍一次 +1。
    snapshot_no: int = 0
    # 最新那份濃縮 page：{"url", "title", "elements": [...], "truncated"}
    latest_page: dict | None = None
    # SHOWING 時等待 overlay 事件的信箱；不在等待時是 None。
    pending: asyncio.Future | None = None

    def uids(self) -> set[str]:
        """最新 page 裡所有 uid；還沒拍過 page 時是空集合。

        show_step 用它判斷 agent 給的 uid 是不是還活著（不是陳舊世代的）。
        """
        if self.latest_page is None:
            return set()
        return {
            element["uid"]
            for element in self.latest_page.get("elements", [])
            if "uid" in element
        }


def new_session_id() -> str:
    """產生一個場次識別，形如 s_8f2a（前綴 s_ 加 4 個十六進位字元）。

    design §5：沿用規格舉例的長相，演算法不鎖定。
    """
    return "s_" + secrets.token_hex(2)


class SessionStore:
    """同一 process 至多一個 Session 的存放處。

    刻意不用 dict：規格說「同一時間只允許一個教學場次」，
    用 dict 會讓「不小心存了兩個」變成可能。
    """

    def __init__(self) -> None:
        self._session: Session | None = None

    def current(self) -> Session | None:
        """目前這場（沒有就是 None）。"""
        return self._session

    def get(self, session_id: str) -> Session | None:
        """依 id 取場次。沒有 Session、或 id 對不上，都回 None。

        呼叫端拿到 None 就回 error="session_not_found"。
        """
        session = self._session
        if session is None or session.session_id != session_id:
            return None
        return session

    def create(self, goal: str) -> Session:
        """建立新場次（新 id、READY、steps_shown=0、snapshot_no=0）並取代舊的。"""
        self._session = Session(session_id=new_session_id(), goal=goal)
        return self._session

    def delete(self) -> None:
        """刪掉場次。之後任何 inspect / show / end 都會是 session_not_found。"""
        self._session = None
