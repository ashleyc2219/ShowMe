"""showme/session.py 的行為測試。

純 Python：不開瀏覽器、不需要 asyncio 事件迴圈，所以全部是普通的 def。
"""

import re

from showme.session import (
    DEFAULT_TIMEOUT_S,
    DONE_BANNER_TEXT,
    MAX_STEPS,
    START_NEXT_ACTION,
    STEP_NEXT_ACTION,
    Session,
    SessionStore,
    State,
    new_session_id,
)


# --- 常數 -----------------------------------------------------------------


def test_constants_match_the_spec_numbers():
    # erm.dbml（Session Note）：硬限制 max_steps = 12、step_timeout = 120 s
    assert MAX_STEPS == 12
    assert DEFAULT_TIMEOUT_S == 120.0


def test_done_banner_text_is_the_fixed_sentence():
    # 結束教學.feature：「成功結束後顯示完成 banner，文案固定且忽略 summary」
    # 中間是 em dash（—），不是減號，也不是 en dash
    assert DONE_BANNER_TEXT == "✅ Done — you created a project"


def test_next_action_hints_point_at_the_right_next_tool():
    # design §5：next_action 沿用 draft 的舉例字串，不是 .feature 的驗收字，
    # 所以這裡只確認它有把 agent 指去正確的下一個動作。
    assert "show_step" in START_NEXT_ACTION
    assert "page.elements" in START_NEXT_ACTION
    assert "show_step" in STEP_NEXT_ACTION
    assert "end_tutorial" in STEP_NEXT_ACTION


# --- session_id -----------------------------------------------------------


def test_new_session_id_looks_like_the_spec_example():
    # 規格舉例是 s_8f2a：前綴 s_ 加 4 個小寫十六進位字元
    assert re.fullmatch(r"s_[0-9a-f]{4}", new_session_id())


def test_new_session_id_is_not_always_the_same():
    # 每次都一樣的話，「end 之後再 start 拿到新場次」就沒有意義了
    assert len({new_session_id() for _ in range(20)}) > 1


# --- Session 本身 ---------------------------------------------------------


def test_state_has_exactly_the_two_runtime_states():
    # design §8：實務狀態只有 READY 與 SHOWING。
    # erm 的 IDLE 是「沒有 Session 物件」，end_tutorial 之後也不留 DONE。
    assert [state.value for state in State] == ["READY", "SHOWING"]
    assert State.READY == "READY"  # str Enum 可以直接跟字串比


def test_new_session_starts_ready_with_zero_counters():
    # 開始教學.feature：「成功開始後 session 狀態為 READY」、steps_shown 為 0
    session = Session(session_id="s_8f2a", goal="create a project")

    assert session.session_id == "s_8f2a"
    assert session.goal == "create a project"
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 0  # 還沒拍過任何 snapshot；start 成功後才變 1
    assert session.latest_page is None
    assert session.pending is None


def test_uids_is_empty_when_there_is_no_page_yet():
    session = Session(session_id="s_8f2a", goal="")

    assert session.uids() == set()


def test_uids_lists_every_uid_in_the_latest_page():
    # show_step 就是拿這個集合來判斷 uid_not_in_snapshot
    session = Session(session_id="s_8f2a", goal="")
    session.latest_page = {
        "url": "http://localhost:3000/",
        "title": "Dashboard",
        "elements": [
            {"uid": "s1-4", "role": "button", "name": "New Project", "testid": "new-project"},
            {"uid": "s1-7", "role": "link", "name": "Settings", "testid": ""},
        ],
        "truncated": False,
    }

    assert session.uids() == {"s1-4", "s1-7"}


def test_uids_ignores_an_element_without_a_uid():
    # build_page（A03）遇到沒有 uid 的元素不會補一個假的，這裡不能因此爆掉
    session = Session(session_id="s_8f2a", goal="")
    session.latest_page = {
        "url": "http://localhost:3000/",
        "title": "Dashboard",
        "elements": [
            {"role": "button", "name": "Mystery", "testid": ""},
            {"uid": "s1-2", "role": "button", "name": "New Project", "testid": ""},
        ],
        "truncated": False,
    }

    assert session.uids() == {"s1-2"}


# --- SessionStore ---------------------------------------------------------


def test_store_is_empty_before_create():
    # erm：「IDLE」＝沒有 Session 物件。此時任何 tool 都會是 session_not_found。
    store = SessionStore()

    assert store.current() is None
    assert store.get("s_8f2a") is None


def test_create_returns_a_ready_session_that_becomes_the_current_one():
    # 開始教學.feature：「成功開始後 session 狀態為 READY」
    store = SessionStore()

    session = store.create("create a project")

    assert store.current() is session  # 就是同一個物件，沒有偷偷複製
    assert session.goal == "create a project"
    assert session.state is State.READY
    assert session.steps_shown == 0
    assert session.snapshot_no == 0


def test_create_accepts_an_empty_goal():
    # clarified（開始教學_goal為空字串時是否操作失敗）：允許空 goal，不 trim、不失敗
    store = SessionStore()

    session = store.create("")

    assert session.goal == ""
    assert session.state is State.READY


def test_create_replaces_the_previous_session():
    # clarified（Session_既有進行中場次…）：同一 process 只允許一個 Session。
    # 注意：真正的 start_tutorial 覆蓋是「沿用同一個 session_id」（A09 處理），
    # store.create() 則是「從無到有」用的，它一定會換掉舊的那個。
    store = SessionStore()
    first = store.create("create a project")

    second = store.create("invite a member")

    assert store.current() is second
    assert store.get(first.session_id) is None


def test_get_returns_the_session_when_the_id_matches():
    store = SessionStore()
    session = store.create("create a project")

    assert store.get(session.session_id) is session


def test_get_returns_none_when_the_id_does_not_match():
    # 檢查頁面.feature / 結束教學.feature：用假的場次識別 → session_not_found
    store = SessionStore()
    store.create("create a project")

    assert store.get("s_missing") is None


def test_delete_removes_the_session():
    # 結束教學.feature：「成功結束後刪除 Session」；再呼叫一次要 session_not_found
    store = SessionStore()
    session = store.create("create a project")

    store.delete()

    assert store.current() is None
    assert store.get(session.session_id) is None


def test_delete_is_safe_when_there_is_no_session():
    # end_tutorial 失敗路徑不該因為「刪一個不存在的東西」而爆炸
    store = SessionStore()

    store.delete()

    assert store.current() is None


def test_create_after_delete_makes_a_brand_new_session():
    # 結束教學之後再 start_tutorial：Session 已刪除 → 新建（erm Session Note）
    store = SessionStore()
    store.create("create a project")
    store.delete()

    fresh = store.create("create a project")

    assert store.current() is fresh
    assert fresh.state is State.READY
    assert fresh.steps_shown == 0
