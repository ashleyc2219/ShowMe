"""showme/rules.py 的行為測試。

全部是純函數：不開瀏覽器、不需要 asyncio，直接呼叫、直接斷言。
"""

from showme.rules import (
    ELEMENT_KEYS,
    KINDS,
    MAX_ELEMENTS,
    build_page,
    empty_page,
    expect_text_missing,
    normalize_kind,
    normalize_timeout_s,
    uid_in_page,
)
from showme.session import DEFAULT_TIMEOUT_S


def test_constants_match_the_spec():
    # design §7.3：kind 只有這四個
    assert KINDS == ("click", "input", "select", "observe")
    # clarified（Page_elements超過上限…）：硬上限 150
    assert MAX_ELEMENTS == 150
    # clarified（PageElement_元素沒有data-testid…）：每筆元素固定四個鍵
    assert ELEMENT_KEYS == ("uid", "role", "name", "testid")


# --- normalize_timeout_s --------------------------------------------------


def test_timeout_none_falls_back_to_the_default():
    # clarified（Step_timeout_s為0或負值…）：未傳 → 120
    assert normalize_timeout_s(None) == 120.0


def test_timeout_zero_falls_back_to_the_default():
    # 顯示步驟.feature Example「傳入 0」→ 此步的 timeout_s 為 120
    assert normalize_timeout_s(0) == 120.0


def test_timeout_negative_falls_back_to_the_default():
    # clarified：負值也改用預設，不是「立即 timeout」、也不是操作失敗
    assert normalize_timeout_s(-5) == 120.0


def test_timeout_default_is_the_same_number_as_the_session_constant():
    # rules.py 裡寫死 120.0；這條把它綁在 session.DEFAULT_TIMEOUT_S 上，
    # 哪天有人只改一邊，這條會紅。
    assert normalize_timeout_s(0) == DEFAULT_TIMEOUT_S


def test_timeout_positive_value_is_kept_as_a_float():
    # 顯示步驟.feature Example「剛好等於 timeout_s」用的就是 120
    assert normalize_timeout_s(120) == 120.0
    assert isinstance(normalize_timeout_s(120), float)


def test_timeout_small_positive_value_is_kept():
    # A12 的等待測試會用 0.2 秒，不能被當成非法值換成 120（那條測試會跑 2 分鐘）
    assert normalize_timeout_s(0.2) == 0.2


# --- normalize_kind -------------------------------------------------------


def test_legal_kinds_are_kept():
    for kind in KINDS:
        assert normalize_kind(kind) == kind


def test_kind_illegal_string_becomes_observe():
    # 顯示步驟.feature：「kind 不屬於 click、input、select、observe 時視為 observe」
    assert normalize_kind("tap") == "observe"


def test_kind_uppercase_becomes_observe():
    # 我們不做大小寫轉換：CLICK 不在白名單裡，所以走 observe。
    # 這樣「模型亂打」的每一種情況都落在同一條路上，行為好預測。
    assert normalize_kind("CLICK") == "observe"


def test_kind_none_becomes_observe():
    assert normalize_kind(None) == "observe"


def test_kind_empty_string_becomes_observe():
    assert normalize_kind("") == "observe"


# --- expect_text_missing --------------------------------------------------


def test_expect_text_missing_for_observe_with_empty_string():
    # 顯示步驟.feature Example「等文字出現但沒帶文字」→ expect_text_required
    assert expect_text_missing("observe", "") is True


def test_expect_text_missing_for_observe_with_none():
    # MCP 那邊 expect_text 有預設值 ""，但內部呼叫可能給 None，兩種都要擋
    assert expect_text_missing("observe", None) is True


def test_expect_text_missing_for_illegal_kind_treated_as_observe():
    # 顯示步驟.feature Example「傳入 tap 且 expect_text 為空」→ expect_text_required
    assert expect_text_missing("tap", "") is True


def test_expect_text_present_for_observe_with_text():
    assert expect_text_missing("observe", "New Project") is False


def test_expect_text_not_required_for_the_other_kinds():
    # click / input / select 各有自己的完成條件，不需要 expect_text
    assert expect_text_missing("click", "") is False
    assert expect_text_missing("input", None) is False
    assert expect_text_missing("select", "") is False


# --- build_page / uid_in_page / empty_page --------------------------------


def _raw_element(index: int) -> dict:
    """做一筆假的 overlay 元素（第 1 份 snapshot 的第 index 個）。"""
    return {
        "uid": f"s1-{index}",
        "role": "button",
        "name": f"Button {index}",
        "testid": "",
    }


def test_build_page_wraps_url_and_title_around_the_elements():
    # 開始教學.feature：回傳的 page 要有 url / title / elements / truncated
    # url 與 title 是 Python 這邊補的（page.url、page.title()），不是 overlay 給的
    page = build_page(
        {"elements": [], "truncated": False},
        "http://localhost:3000/",
        "Dashboard",
    )

    assert page == {
        "url": "http://localhost:3000/",
        "title": "Dashboard",
        "elements": [],
        "truncated": False,
    }


def test_build_page_fills_a_missing_testid_with_an_empty_string():
    # 開始教學.feature Example「Settings 沒有 testid」＋
    # clarified（PageElement_元素沒有data-testid…）：鍵永遠存在，值為空字串
    raw = {"elements": [{"uid": "s1-7", "role": "link", "name": "Settings"}], "truncated": False}

    page = build_page(raw, "http://localhost:3000/", "Dashboard")

    assert page["elements"] == [
        {"uid": "s1-7", "role": "link", "name": "Settings", "testid": ""}
    ]


def test_build_page_fills_a_missing_name_with_an_empty_string():
    # 開始教學.feature：「沒有 a11y name 的互動元素仍列出且 name 為空字串」
    raw = {"elements": [{"uid": "s1-2", "role": "button", "testid": ""}], "truncated": False}

    page = build_page(raw, "http://localhost:3000/", "Dashboard")

    assert page["elements"][0]["name"] == ""
    assert set(page["elements"][0]) == set(ELEMENT_KEYS)


def test_build_page_drops_keys_that_are_not_element_keys():
    # G2（design §3）：模型不准寫 CSS selector，所以就算 overlay 多給了 selector
    # 之類的欄位，也不會流到 agent 手上
    raw = {
        "elements": [
            {
                "uid": "s1-1",
                "role": "button",
                "name": "New Project",
                "testid": "new-project",
                "selector": "#new-project",
            }
        ],
        "truncated": False,
    }

    page = build_page(raw, "http://localhost:3000/", "Dashboard")

    assert set(page["elements"][0]) == set(ELEMENT_KEYS)
    assert "selector" not in page["elements"][0]


def test_build_page_does_not_invent_a_uid():
    # uid 是 overlay 組的（A 只給世代號 n）。缺 uid 是 overlay 的 bug，
    # 我們不補一個假的來蓋住它——沒有 uid 的元素就是選不到，會走 uid_not_in_snapshot。
    raw = {"elements": [{"role": "button", "name": "Mystery"}], "truncated": False}

    page = build_page(raw, "http://localhost:3000/", "Dashboard")

    assert page["elements"][0] == {"role": "button", "name": "Mystery", "testid": ""}
    assert "uid" not in page["elements"][0]


def test_build_page_keeps_exactly_150_elements_without_truncating():
    # 開始教學.feature Example「不多於 150 個時 truncated 為 false」
    raw = {"elements": [_raw_element(i) for i in range(1, 151)], "truncated": False}

    page = build_page(raw, "http://localhost:3000/", "Dashboard")

    assert len(page["elements"]) == 150
    assert page["truncated"] is False


def test_build_page_cuts_151_elements_down_to_150_and_marks_truncated():
    # 開始教學.feature Example「超過 150 個時只留前 150 且 truncated 為 true」
    # clarified：依 DOM 走訪順序取前 150，不分 viewport → 留的是最前面那些
    raw = {"elements": [_raw_element(i) for i in range(1, 152)], "truncated": False}

    page = build_page(raw, "http://localhost:3000/", "Dashboard")

    assert len(page["elements"]) == 150
    assert page["truncated"] is True
    assert page["elements"][0]["uid"] == "s1-1"
    assert page["elements"][-1]["uid"] == "s1-150"


def test_build_page_passes_through_truncated_from_the_overlay():
    # overlay 自己就砍到 150 並回 truncated=true 時，Python 不可以把它變回 false
    raw = {"elements": [_raw_element(1)], "truncated": True}

    page = build_page(raw, "http://localhost:3000/", "Dashboard")

    assert page["truncated"] is True


def test_build_page_survives_a_raw_snapshot_with_no_keys():
    # overlay 還是 stub（或 B 那邊出錯）時可能只回 {}；
    # 這裡不能爆炸，要回一份鍵齊全的空 page，讓 agent 自己去 inspect_page
    page = build_page({}, "http://localhost:3000/", "Dashboard")

    assert page == {
        "url": "http://localhost:3000/",
        "title": "Dashboard",
        "elements": [],
        "truncated": False,
    }


def test_uid_in_page_finds_a_uid_from_the_latest_snapshot():
    page = build_page({"elements": [_raw_element(4)], "truncated": False}, "u", "t")

    assert uid_in_page("s1-4", page) is True


def test_uid_in_page_rejects_a_uid_from_an_older_snapshot():
    # clarified（PageElement_uid的snapshot編號何時遞增）：
    # 陳舊 snapshot# 的 uid 必然不在最新 page.elements → show_step 回 uid_not_in_snapshot
    page = build_page({"elements": [_raw_element(4)], "truncated": False}, "u", "t")

    assert uid_in_page("s0-4", page) is False


def test_uid_in_page_is_false_when_there_is_no_page_yet():
    assert uid_in_page("s1-4", None) is False


def test_uid_in_page_is_false_on_an_empty_page():
    assert uid_in_page("s1-4", empty_page()) is False


def test_empty_page_has_every_key():
    # 回傳形狀的鍵永遠都在，agent 不用寫 if
    assert empty_page() == {"url": "", "title": "", "elements": [], "truncated": False}


def test_empty_page_returns_a_fresh_dict_each_time():
    # 如果不小心寫成模組層級的常數字典，改到一份就會污染全部
    first = empty_page()
    first["elements"].append({"uid": "s1-1"})

    assert empty_page()["elements"] == []
