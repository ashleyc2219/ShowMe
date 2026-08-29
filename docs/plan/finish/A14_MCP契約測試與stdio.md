# A14｜MCP 契約測試與 stdio 接線

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：[A13_end_tutorial.md](A13_end_tutorial.md)　｜　下一篇：[A15_真瀏覽器端到端.md](A15_真瀏覽器端到端.md)
> 對應設計：`docs/design/showme.md` §7、§13、§14（第 3 層「MCP 契約」）、§16 ｜ 對應切片：S5 收尾
> 預估時間：45–60 分鐘

---

## 1. 這一篇要做什麼

前面十三篇都是「直接呼叫 `ShowMeApp` 的方法」。這一篇第一次**從 MCP client 的角度**看 ShowMe：
用官方 SDK 的 in-memory `Client` 連上我們的 `MCPServer`，確認對外露出的契約沒歪掉——**恰好四個 tool、沒有 `wait_for_user`、失敗不會變成 protocol error、`show_step` 的參數 schema 正確、instructions 有帶上**。
然後把它真的用 stdio 跑起來，手動打一次 JSON-RPC，最後寫下 Qoder 這一端的設定。

---

## 2. 做完會看到什麼

### 2.1 兩種連線方式，同一個 server 物件

```text
  (A) 測試用：in-memory，沒有 subprocess、沒有網路、沒有 stdio
  ┌──────────────────────────┐         ┌───────────────────────────┐
  │ tests/test_mcp_contract  │         │ showme/server.py          │
  │   async with Client(mcp) │<=======>│   mcp = MCPServer("showme")│
  │     list_tools()         │  直接    │   @mcp.tool() x 4          │
  │     call_tool(...)       │  函數呼叫 │   → get_app() → ShowMeApp │
  └──────────────────────────┘         └───────────────────────────┘
                                            ↑ set_app(app) 換成用
                                              FakeBrowser 的 app

  (B) 正式用：stdio，Qoder 開一個子行程，兩邊用「一行一個 JSON」講話
  ┌──────────┐  stdin  (JSON-RPC request)  ┌─────────────────────────┐
  │  Qoder   │ ──────────────────────────> │ uv run showme           │
  │  Agent   │ <────────────────────────── │  = showme.__main__:main │
  └──────────┘  stdout (JSON-RPC response) │  = mcp.run("stdio")     │
                                           └─────────────────────────┘
     ※ stderr 給人看 log；stdout 只准放 JSON-RPC，印錯地方會把協定弄壞
```

### 2.2 一次 stdio 握手的訊息流

```text
  Qoder                                              ShowMe (uv run showme)
    │                                                        │
    │ ── {"method":"initialize", ...} ─────────────────────>  │
    │ <─ {"result":{"serverInfo":{"name":"showme"},           │
    │                "instructions":"You are TEACHING ..."}} ─│
    │                                                        │
    │ ── {"method":"notifications/initialized"} ───────────>  │  （通知，沒有回應）
    │                                                        │
    │ ── {"method":"tools/list"} ─────────────────────────>   │
    │ <─ {"result":{"tools":[start_tutorial, inspect_page,    │
    │                        show_step, end_tutorial]}} ──────│
    │                                                        │
    │ ── {"method":"tools/call","params":{                    │
    │        "name":"start_tutorial","arguments":{...}}} ──>  │
    │ <─ {"result":{"content":[...],                          │
    │               "structuredContent":{...},"isError":false}}│
    │                                                        │
```

### 2.3 「失敗」有兩種，我們只用其中一種

```text
   ① 規格上的操作失敗（我們用這種）        ② protocol error（我們絕不用）
   ------------------------------        ---------------------------------
   tool handler  return {"error": ...}    tool handler  raise SomethingError
        │                                      │
        v                                      v
   CallToolResult(                       CallToolResult(
     is_error = False                      is_error = True
     structured_content = {                content = [TextContent("Error executing
       "page": None,                                   tool inspect_page: ...")]
       "error": "session_not_found"}       structured_content = None
   )                                     )
        │                                      │
   agent 讀得懂、知道怎麼補救           agent 只拿到一段英文字串，很難自動處理
```

---

## 3. 開始前先確認

A01–A13 都已完成並且測試全綠：

- [ ] `uv run pytest -m "not browser" -q` 全綠、0 skipped。
- [ ] `showme/server.py` 已經是 A07 的薄殼：`mcp = MCPServer("showme", instructions=INSTRUCTIONS)`、`get_app()` / `set_app()`、四個 `@mcp.tool()` 各自轉呼叫 `ShowMeApp` 的同名方法。
- [ ] `showme/app.py` 的四個方法都已完成（A08–A13）。
- [ ] `tests/conftest.py` 有 `anyio_backend`、`fake_browser`、`app`、`started`。
- [ ] `pyproject.toml` 的 `[project.scripts]` 有 `showme = "showme.__main__:main"`，dependencies 有 `mcp[cli]`。

跑這兩行確認 server 模組長對了：

```bash
cd /Users/linjunting/hackathonQoder
uv run python -c "
from showme.server import mcp, INSTRUCTIONS, set_app, get_app
print('server ok:', type(mcp).__name__)
print('instructions chars:', len(INSTRUCTIONS))
"
```

預期輸出：

```text
server ok: MCPServer
instructions chars: 793
```

（字數不一定剛好 793，只要是幾百個字、不是 0 就對了。）

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| MCP | Model Context Protocol。IDE／agent 跟外部工具講話的標準協定。訊息格式是 JSON-RPC 2.0。 |
| JSON-RPC 2.0 | 一種「送一個 JSON 物件、收一個 JSON 物件」的遠端呼叫格式。有 `id` 的叫 request（會有回應），沒有 `id` 的叫 notification（不會有回應）。 |
| stdio transport | 傳輸方式是「子行程的標準輸入／輸出」。Qoder 開一個 `uv run showme` 子行程，把 JSON 寫進它的 stdin，從 stdout 讀回來。**一行一個 JSON**。 |
| `MCPServer` | 官方 Python SDK v2 的高階 server 類別。第一個位置參數是 `name`，其餘一律用關鍵字傳（v2 把 `title` / `description` / `version` 排在位置參數，不用關鍵字會把 `instructions` 塞錯欄位）。 |
| `instructions` | server 給 agent 的「使用說明書」，在 `initialize` 的回應裡送出去。我們用它寫 SHOW protocol（教、不代做、一次一步、uid 來自最新 page）。 |
| in-memory `Client` | 官方 SDK 提供的測試用 client：`async with Client(mcp) as c`。直接跟 server 物件講話，不開子行程、不走 stdio，所以測試很快。 |
| `CallToolResult` | `call_tool()` 的回傳。三個欄位：`content`（給模型看的文字區塊清單）、`structured_content`（給程式用的 JSON）、`is_error`（tool 執行有沒有炸掉）。 |
| `structured_content` | tool 回傳值的 JSON 版本。**tool 回傳 dict（字串 key）時就是那個 dict 本身，不會被包成 `{"result": ...}`**；純量／list／tuple 才會被包（見 §7 Step 1 的查證結論，以及 A01 Step 10 的實測）。 |
| `is_error` | `True` 代表 tool handler 丟了例外（protocol 層級的失敗）。我們的四個 tool **永遠 return dict**，所以這個欄位永遠不該是 `True`。 |
| `input_schema` | tool 的參數 JSON Schema，SDK 從 type hints 自動產生。`properties` 是全部參數，`required` 是**沒有預設值**的那些。 |
| allow list | Qoder／IDE 那邊「不用每次問人就可以直接呼叫」的工具白名單。我們要加 `mcp__showme__*`。 |
| Request Timeout | IDE 等一個 MCP tool 回應的上限。ShowMe 的 `show_step` 會卡住等人操作（預設 120 秒），所以這個值一定要調高。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 新增（測試） | `tests/test_mcp_contract.py` | 從 MCP client 角度驗契約：四個 tool、schema、錯誤通道、instructions |
| 修改（測試） | `tests/conftest.py` | 加一個 `mcp_client` fixture（把 server 的 app 換成用 FakeBrowser 的） |
| 新增（文件） | 無 | Qoder 設定與逾時量測結果記在 `A16_與B合流與Demo演練.md` 的 checklist 裡 |

**不會動到：** `showme/**`（本篇一行產品程式碼都不改）、`overlay/**`。

---

## 6. 介面約定

### 6.1 用到（來自前面幾篇，簽名不可改）

```python
# showme/server.py（A07 已完成）
INSTRUCTIONS = """You are TEACHING the user how to use the app; you never act for them.
- You have no click/type/navigate tools. You only look (start_tutorial / inspect_page) and point (show_step).
- Plan 3-8 steps in your head, but pick each step's uid from the LATEST page.elements only. Never reuse a uid from an older snapshot.
- One show_step at a time; wait for it to return before deciding the next step.
- instruction: second person, one sentence, use the words visible on screen (e.g. "Click New Project").
- If event is "stuck": call show_step again with the SAME uid and a plainer instruction.
- If error is "uid_not_in_snapshot": re-pick a uid from the returned page.
- Call end_tutorial only when the page shows the goal is achieved.
"""

mcp = MCPServer("showme", instructions=INSTRUCTIONS)

def get_app() -> ShowMeApp: ...
def set_app(app: ShowMeApp | None) -> None: ...   # 測試用：換成用 FakeBrowser 的 app
```

四個 tool 的簽名（= 對外的 schema）：

```python
async def start_tutorial(url: str, goal: str) -> dict
async def inspect_page(session_id: str) -> dict
async def show_step(session_id: str, uid: str, instruction: str, kind: str,
                    step_index: int, step_total: int,
                    expect_text: str = "", timeout_s: float = 120) -> dict
async def end_tutorial(session_id: str, summary: str) -> dict
```

### 6.2 提供（給後面幾篇）

- `tests/conftest.py` 的 `mcp_client` fixture：一個已連上 server、而且 server 的 app 已被換成用 `FakeBrowser` 的 `Client`。
- 一份可以貼進 Qoder 的 MCP 設定 JSON（見 Step 5）。
- Request Timeout 的實測數字（填進 A16 的 demo checklist）。🙋 **需要 Qoder IDE ＋ 真人，留給使用者手動；見 Step 7。**

---

## 7. 步驟

### Step 1：先把官方 API 查清楚（10 分鐘，這一步就是「不要憑記憶猜」）

用 Context7 查 MCP Python SDK v2（library id `/websites/py_sdk_modelcontextprotocol_io_v2`）。以下是**已經查證過的結論**，寫測試時直接照用；如果你想自己再確認一次，查詢字串用「in-memory testing Client list_tools call_tool CallToolResult」與「structured output dict return type」。

| 問題 | 查到的答案 | 來源 |
|---|---|---|
| 怎麼做 in-memory 測試？ | `from mcp import Client`；`async with Client(mcp) as client: ...`。搭配 pytest + anyio：`@pytest.mark.anyio` + 一個回 `"asyncio"` 的 `anyio_backend` fixture。v1 的 `create_connected_server_and_client_session` 在 v2 已移除。 | https://py.sdk.modelcontextprotocol.io/v2/get-started/testing |
| `list_tools()` 回什麼？ | 一個 `ListToolsResult`。用 `result.tools` 拿清單，每個 tool 有 `.name`、`.title`、`.description`、`.input_schema`。 | https://py.sdk.modelcontextprotocol.io/v2/client |
| `call_tool()` 回什麼？ | 一個 `CallToolResult`，三個欄位：`.content`（給模型看的區塊清單，例如 `TextContent`）、`.structured_content`（tool 回傳值的 JSON）、`.is_error`（tool 有沒有丟例外）。 | https://py.sdk.modelcontextprotocol.io/v2/client |
| **tool 回傳 `dict` 時，`structured_content` 是那個 dict 本身，還是被包成 `{"result": ...}`？** | **是 dict 本身，不會被包。** 官方原文：「Dictionaries with string keys are treated as JSON objects and are not wrapped in a result object.」對照組：回傳純量（str / int / float / bool / None）、list、tuple 時**才會**被包成 `{"result": ...}`（所以官方入門範例的 `add` 才會斷言 `result.structured_content == {"result": 3}`）。**本專案實測（mcp 2.1.1，見下方方框）：四個 tool 的註記是 `dict[str, object]`，`structured_content` 就是裸 dict。** | https://py.sdk.modelcontextprotocol.io/v2/servers/structured-output |
| tool handler 丟例外會怎樣？ | client 拿到 `is_error = True`、`content` 是一段 `"Error executing tool ...: ..."` 的文字、`structured_content` 是 `None`。**這就是我們規格明訂要避開的路**：四個 tool 永遠 `return dict`。 | https://py.sdk.modelcontextprotocol.io/v2/servers/handling-errors |
| stdio 怎麼跑？ | `mcp.run()`，transport 參數在 `run()` 不在建構子；不給參數預設就是 stdio。我們寫成 `mcp.run(transport="stdio")` 讓意圖明顯。 | https://py.sdk.modelcontextprotocol.io/v2/run |
| 有沒有互動式 Inspector？ | 有：`uv run mcp dev <python 檔>[:<物件名>]`。它會啟動 MCP Inspector（需要 `mcp[cli]` extra，而且會用 `npx` 拉 Inspector，所以本機要有 Node）。 | https://py.sdk.modelcontextprotocol.io/v2/get-started/first-steps 、https://py.sdk.modelcontextprotocol.io/v2/api/mcp/cli/cli |

> **關於「裸 `dict`」這件事，已經有實測結論了（A01 Step 10 + A07），照下面這段走。**
>
> A01 Step 10 實測的結果**不是**計劃預期的兩種形狀，而是**第三種：`structured_content` 是 `None`**。
> 原因：mcp 2.1.1 是**從回傳型別註記推導 output schema** 的，沒有型別參數的裸 `dict` 推不出 schema，沒有 schema 就沒有 `structured_content`（dict 的內容並沒有掉，它被序列化成 JSON 放在 `content[0].text`）。
>
> | 回傳註記 | `output_schema` | `structured_content` |
> |---|---|---|
> | `-> dict`（裸的） | `None` | `None` ❌ |
> | `-> dict[str, object]` | `{'additionalProperties': True, 'type': 'object', ...}` | `{'error': ...}` ✅ 裸 dict |
> | 完全不寫註記 | `None` | `None` ❌ |
>
> **所以 A07 已經把 `showme/server.py`（與 `showme/app.py`）四個 tool 的回傳註記寫成 `dict[str, object]`。** 本篇不必再改任何產品程式碼，`structured_content` 拿到的就是我們 `return` 的那個裸 dict。細節見 `docs/plan/report/2026-08-29-階段1_A01環境建置-REP.md` 的「遇到的問題」第 1 點。
>
> Step 3 的測試檔仍保留一個 `payload()` 小工具，**兩種形狀（裸 dict / 被包一層）都能過**——契約測試該鎖的是 `error` 欄位的值，不該因為 SDK 對回傳註記的包裝細節而變紅。它同時會在 `structured_content is None` 時給出「註記推不出 schema」的提示訊息。

### Step 2：在 conftest 加 `mcp_client` fixture

打開 `tests/conftest.py`，在檔案最上面的 import 區加上：

```python
from mcp import Client

from showme.server import mcp as server_mcp
from showme.server import set_app
```

然後在檔案最後面加上這個 fixture：

```python
@pytest.fixture
async def mcp_client(app):
    """一個連上 showme server 的 in-memory MCP client。

    server.py 的 tool 走的是 module-level 的 get_app()，預設會 new 一個
    用真 PlaywrightBrowser 的 ShowMeApp。這裡先用 set_app() 把它換成
    conftest 的 `app` fixture（用 FakeBrowser），所以契約測試不會開瀏覽器。
    測完再 set_app(None) 還原，免得污染其他測試。
    """
    set_app(app)
    try:
        async with Client(server_mcp) as client:
            yield client
    finally:
        set_app(None)
```

### Step 3：寫契約測試（紅→綠一次到位）

建立 `tests/test_mcp_contract.py`，整份貼上：

```python
"""A14：MCP 契約測試。

用官方 SDK 的 in-memory Client 連上 showme server，驗「對外露出的形狀」：
四個 tool、沒有 wait_for_user、失敗走 error 欄不走 protocol error、
show_step 的參數 schema、instructions 有帶。

不開瀏覽器（mcp_client fixture 已經把 app 換成用 FakeBrowser 的）。
"""

from __future__ import annotations

import pytest

from showme.server import INSTRUCTIONS

pytestmark = pytest.mark.anyio

TOOL_NAMES = {"start_tutorial", "inspect_page", "show_step", "end_tutorial"}

SHOW_STEP_PARAMS = {
    "session_id", "uid", "instruction", "kind",
    "step_index", "step_total", "expect_text", "timeout_s",
}
SHOW_STEP_REQUIRED = {
    "session_id", "uid", "instruction", "kind", "step_index", "step_total",
}


def payload(result) -> dict:
    """把 CallToolResult 攤成 tool 實際回傳的那個 dict。

    官方文件（https://py.sdk.modelcontextprotocol.io/v2/servers/structured-output）：
    「Dictionaries with string keys are treated as JSON objects and are not wrapped
    in a result object.」——所以 structured_content 就是我們 return 的那個 dict；
    純量／list／tuple 才會被包成 {"result": ...}。

    **本專案實測（mcp 2.1.1）**：四個 tool 的回傳註記是 `dict[str, object]`，
    `structured_content` 就是**裸 dict**（例如 {'page': None, 'error': 'session_not_found'}），
    沒有被包成 {"result": ...}。註記若寫成沒有型別參數的裸 `dict`，SDK 推不出
    output schema，`structured_content` 會直接變 `None`——見
    docs/plan/report/2026-08-29-階段1_A01環境建置-REP.md Step 10。

    這裡仍然接受被包一層的形狀：契約測試該鎖的是 error 欄位的值，不是 SDK 的包裝細節。
    """
    sc = result.structured_content
    assert sc is not None, (
        f"structured_content 是 None，代表 tool 丟了例外或回傳註記推不出 schema。"
        f"content={result.content}"
    )
    return sc["result"] if isinstance(sc, dict) and set(sc) == {"result"} else sc


async def _tools_by_name(client) -> dict:
    listed = await client.list_tools()
    return {tool.name: tool for tool in listed.tools}


# --------------------------------------------------------------------------
# 有哪些 tool
# --------------------------------------------------------------------------

async def test_server_exposes_exactly_the_four_tools(mcp_client):
    tools = await _tools_by_name(mcp_client)

    assert set(tools) == TOOL_NAMES
    assert len(tools) == 4


async def test_there_is_no_wait_for_user_tool(mcp_client):
    """MVP 的 Non-Goal：不做第五個 tool、不做 wait_for_user、不做輪詢。"""
    tools = await _tools_by_name(mcp_client)

    assert "wait_for_user" not in tools


async def test_every_tool_has_a_description(mcp_client):
    """docstring 就是 agent 看到的 description，空的等於沒告訴 agent 怎麼用。"""
    tools = await _tools_by_name(mcp_client)

    for name, tool in tools.items():
        assert tool.description, f"{name} 沒有 description（server.py 的 docstring 掉了？）"


# --------------------------------------------------------------------------
# 錯誤走 error 欄，不走 protocol error
# --------------------------------------------------------------------------

async def test_unknown_session_is_a_normal_result_not_a_protocol_error(mcp_client):
    """規格：操作失敗寫在回傳的 error，MCP 呼叫本身仍算成功。"""
    result = await mcp_client.call_tool("inspect_page", {"session_id": "s_missing"})

    assert result.is_error is not True, (
        f"tool 不該丟例外。content={result.content}"
    )
    data = payload(result)
    assert data["error"] == "session_not_found"
    assert data["page"] is None


async def test_end_tutorial_with_unknown_session_also_returns_an_error_field(mcp_client):
    result = await mcp_client.call_tool(
        "end_tutorial", {"session_id": "s_missing", "summary": "create a project"}
    )

    assert result.is_error is not True
    data = payload(result)
    assert data["ok"] is False
    assert data["error"] == "session_not_found"


# --------------------------------------------------------------------------
# show_step 的參數 schema
# --------------------------------------------------------------------------

async def test_show_step_input_schema_has_all_eight_parameters(mcp_client):
    tools = await _tools_by_name(mcp_client)
    schema = tools["show_step"].input_schema

    properties = schema["properties"]
    assert set(properties) == SHOW_STEP_PARAMS
    assert len(properties) == 8


async def test_show_step_expect_text_and_timeout_s_are_optional(mcp_client):
    """expect_text 與 timeout_s 有預設值，agent 可以不傳。"""
    tools = await _tools_by_name(mcp_client)
    schema = tools["show_step"].input_schema

    required = set(schema.get("required", []))
    assert "expect_text" not in required
    assert "timeout_s" not in required
    assert required == SHOW_STEP_REQUIRED


async def test_other_tools_have_the_expected_parameters(mcp_client):
    tools = await _tools_by_name(mcp_client)

    assert set(tools["start_tutorial"].input_schema["properties"]) == {"url", "goal"}
    assert set(tools["inspect_page"].input_schema["properties"]) == {"session_id"}
    assert set(tools["end_tutorial"].input_schema["properties"]) == {"session_id", "summary"}


# --------------------------------------------------------------------------
# instructions
# --------------------------------------------------------------------------

async def test_server_instructions_are_not_empty(mcp_client):
    """instructions 是 SHOW protocol：教、不代做、一次一步、uid 來自最新 page。"""
    assert INSTRUCTIONS.strip() != ""
    assert "you never act for them" in INSTRUCTIONS
    assert "One show_step at a time" in INSTRUCTIONS
    assert "LATEST page.elements" in INSTRUCTIONS
    assert "end_tutorial" in INSTRUCTIONS

    # 這一版 SDK 的 Client 若有把 initialize 的結果留下來，順便確認 instructions
    # 真的送到了對面。官方文件沒有寫死這個屬性名，所以用 getattr 探測，探不到就跳過。
    init = getattr(mcp_client, "initialize_result", None)
    if init is not None and getattr(init, "instructions", None):
        assert init.instructions == INSTRUCTIONS


# --------------------------------------------------------------------------
# 走一次真的 tool call（證明薄殼有接到 app）
# --------------------------------------------------------------------------

async def test_start_tutorial_through_the_mcp_layer(mcp_client):
    result = await mcp_client.call_tool(
        "start_tutorial",
        {"url": "http://localhost:3000/", "goal": "create a project"},
    )

    assert result.is_error is not True
    data = payload(result)
    assert data["error"] == ""
    assert data["goal"] == "create a project"
    assert data["session_id"].startswith("s_")
    assert data["page"]["title"] == "Dashboard"
    assert all(el["uid"].startswith("s1-") for el in data["page"]["elements"])
```

跑：

```bash
uv run pytest tests/test_mcp_contract.py -q
```

預期輸出：

```text
..........                                                          [100%]
10 passed in 0.5s
```

> 這一篇是**驗收既有實作**，所以第一次跑就該綠。如果紅了，代表 `showme/server.py` 的薄殼跟 brief 的簽名不一致——去 §9 的排錯表找對應症狀。
>
> **例外：本篇如果跟 A11–A13 平行做，`test_end_tutorial_with_unknown_session_also_returns_an_error_field` 會紅。**
> 它斷言的 `{"ok": False, "error": "session_not_found"}` 是 A13 才實作的形狀；A13 完成前 `app.end_tutorial()` 還回 `{"error": "not_implemented"}`，取 `data["ok"]` 會 `KeyError: 'ok'`。
> 這是**正確的紅燈**（測試先於實作），不要為了讓它綠而改測試——A13 一落地就自己變綠。
> 實測：A13 未完成時 `1 failed, 9 passed in 0.13s`（紅的就只有這一條）；A13 落地後重跑即為 `10 passed in 0.09s`。

再跑一次全部：

```bash
uv run pytest -m "not browser" -q
```

預期：全綠、0 skipped。

### Step 4：手動用 stdio 跑一次

契約測試走的是 in-memory，完全沒經過 stdin/stdout。真的接 Qoder 之前，一定要親手確認「這支程式真的會在 stdout 講 JSON-RPC」。

**做法 A：把三行指令灌進去（最快，但只驗得到 `initialize`）**

```bash
cd /Users/linjunting/hackathonQoder
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"manual","version":"0.0.1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | uv run showme
```

三行的意思：

1. **`initialize`**：握手。告訴 server「我是誰、我支援哪個協定版本」。
2. **`notifications/initialized`**：沒有 `id`，是通知，代表「握手完成，可以開始了」。協定規定要送這一則，不送的話有些 server 會拒絕後面的請求。
3. **`tools/list`**：列出工具。

stdin 送完就 EOF，server 會自己結束（exit 0）。

> ⚠️ **實測修正（mcp 2.1.1，跑三次結果一致）：這個做法只會印出「一行」——`id:1` 的 `initialize` 回應，`id:2` 的 `tools/list` 回應拿不到。**
> 原因：`printf` 一口氣寫完三行就關掉 stdin，server 讀到 EOF 就開始收攤，`tools/list` 還沒被處理完 process 就結束了。這是 EOF 跟請求處理在搶時間，不是 server 壞了。
> **所以「四個 tool 名」這一項要用下面的做法 A′ 驗**；做法 A 只夠用來確認「stdout 真的在講 JSON-RPC，而且 `serverInfo.name` 與 `instructions` 都對」。

第一行（`initialize` 的回應）裡一定找得到這些片段：

```json
{"jsonrpc":"2.0","id":1,"result":{
  "protocolVersion":"...",
  "capabilities":{"tools":{...}},
  "serverInfo":{"name":"showme","version":"..."},
  "instructions":"You are TEACHING the user how to use the app; you never act for them.\n- You have no click/type/navigate tools...."
}}
```

> `protocolVersion` 的實際字串以 server 回的為準：你送的版本跟它回的版本不一樣是**正常**的（協定會協商）。實測我們送 `2025-06-18`、server 也回 `2025-06-18`。
> JSON 的鍵在網路上是 camelCase（`structuredContent`、`inputSchema`、`isError`），在 Python 物件上是 snake_case（`.structured_content`、`.input_schema`、`.is_error`）。同一件事、兩種寫法。
> `serverInfo.version` 實測是空字串（`pyproject.toml` 沒把版本傳給 `MCPServer`），不影響 Qoder 接線。

**做法 A′：用 Python `subprocess` 撐住 stdin（推薦，三則訊息都驗得到）**

`printf | uv run showme` 的問題是 stdin 太早關掉；改成自己開子行程、把 stdin 留著、逐行讀 stdout、讀完再 `terminate()` 就沒這個問題。
順帶一提：**這台 macOS 沒有 `timeout` 也沒有 `gtimeout`**（`command -v timeout gtimeout` 兩個都空），所以不能用 `timeout 30 uv run showme` 之類的寫法來保底，超時控制要自己寫在 Python 裡。

把下面這支存成暫存檔（例如 `/tmp/stdio_check.py`，**不要進版控**）再 `uv run python /tmp/stdio_check.py`：

```python
import json, subprocess, threading

REPO = "/Users/linjunting/hackathonQoder"
MESSAGES = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18", "capabilities": {},
        "clientInfo": {"name": "manual", "version": "0.0.1"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
]

proc = subprocess.Popen(
    ["uv", "--directory", REPO, "run", "showme"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1,
)
lines: list[str] = []
t = threading.Thread(target=lambda: lines.extend(proc.stdout), daemon=True)
t.start()

for msg in MESSAGES:
    proc.stdin.write(json.dumps(msg) + "\n")
    proc.stdin.flush()

t.join(timeout=30)          # 讀不到就別無限等（本機沒有 timeout 指令）
proc.terminate()
proc.wait(timeout=10)

for raw in lines:
    result = json.loads(raw).get("result", {})
    if "serverInfo" in result:
        print("server name   :", result["serverInfo"]["name"])
        print("protocolVer   :", result.get("protocolVersion"))
        print("instructions? :", bool(result.get("instructions")))
    if "tools" in result:
        print("tools         :", [x["name"] for x in result["tools"]])
print("stderr:", proc.stderr.read()[:500])
print("exit  :", proc.returncode)
```

實測輸出（2026-08-29）：

```text
--- 收到 2 行 stdout ---
server name   : showme
server version:
protocolVer   : 2025-06-18
instructions? : True
instructions[0:60] : You are TEACHING the user how to use the app; you never act
tools         : ['start_tutorial', 'inspect_page', 'show_step', 'end_tutorial']
--- stderr（前 500 字）---

--- exit code: 143
```

四個 tool 名都在、**沒有** `wait_for_user`、`instructions` 有送到、**stderr 全空**（代表沒有人在產品程式碼裡 `print()` 髒東西）、exit 143 = 128+15 = 正常被 SIGTERM 收掉。

**做法 B：互動式打字**

```bash
uv run showme
```

游標會停在那裡不動（它在等 stdin）。把上面那三行**一行一行**貼進去、每行按 Enter，就會看到回應。結束按 `Ctrl-D`（送 EOF）或 `Ctrl-C`。

**做法 C：MCP Inspector（有 Node 才能用）**

官方 CLI 提供 `mcp dev`，它會開一個網頁版的 Inspector，可以用滑鼠點來點去呼叫 tool：

```bash
uv run mcp dev showme/server.py:mcp
```

- `showme/server.py:mcp` 是「檔案路徑 : 那個檔案裡的 server 物件名」。
- 這個指令來自 `mcp[cli]` extra（我們的 `pyproject.toml` 已經有），而且它會用 `npx` 去拉 Inspector，所以本機要有 Node。**沒有 Node 就跳過這一項，做法 A′ 已經足夠驗收。**
- 來源：https://py.sdk.modelcontextprotocol.io/v2/get-started/first-steps 、https://py.sdk.modelcontextprotocol.io/v2/api/mcp/cli/cli

> **本機實測（2026-08-29）：Node v22.22.3 / npx 10.9.8 有裝，但這一項還是跳過了。**
> `uv run mcp dev showme/server.py:mcp` 會先讓 npx 下載 `@modelcontextprotocol/inspector@2.4.0`（本機沒快取），35 秒還在裝，Inspector 的網址一直沒印出來。
> Inspector 是「用滑鼠玩玩看」的便利工具，不是驗收條件；**做法 A′ 已經把驗收清單裡的每一項都驗完了**，所以不等它。
> 想用的人自己在終端機跑一次、等 npm 裝完（第一次可能要好幾分鐘）即可，之後有快取就會快。

> ⚠️ 在 Inspector 或 Qoder 裡點 `start_tutorial` 會**真的開一個 Chrome 視窗**（那時候用的是真的 `PlaywrightBrowser`，不是 FakeBrowser）。心裡有數就好。

### Step 5：寫下 Qoder 的 MCP 設定

Qoder 這一端要告訴它「怎麼把 ShowMe 這個子行程叫起來」。設定內容長這樣：

```json
{
  "mcpServers": {
    "showme": {
      "command": "uv",
      "args": ["--directory", "/Users/linjunting/hackathonQoder", "run", "showme"]
    }
  }
}
```

三個重點：

- `--directory <repo 絕對路徑>` 一定要有。IDE 啟動子行程時的工作目錄不一定是 repo，`uv` 找不到 `pyproject.toml` 就跑不起來。
- 路徑寫**絕對路徑**，不要 `~` 也不要相對路徑。
- `uv` 本身要在 IDE 找得到的 `PATH` 上。如果 IDE 說 `command not found: uv`，就把 `"command"` 換成 `uv` 的完整路徑。**本機實測 `command -v uv` = `/opt/homebrew/bin/uv`（uv 0.11.32）**，所以備援寫法是：

```json
{
  "mcpServers": {
    "showme": {
      "command": "/opt/homebrew/bin/uv",
      "args": ["--directory", "/Users/linjunting/hackathonQoder", "run", "showme"]
    }
  }
}
```

**這份 JSON 要貼到哪個檔案，請以 Qoder 官方文件為準。** 本文件不猜設定檔路徑——猜錯只會浪費 demo 前的時間。在 Qoder 裡找「MCP」「Model Context Protocol」相關的設定頁面，或它文件裡的 MCP 章節。

接好之後，四個 tool 在 Qoder 裡的全名是：

```text
mcp__showme__start_tutorial
mcp__showme__inspect_page
mcp__showme__show_step
mcp__showme__end_tutorial
```

### Step 6：allow list

Demo 當天如果每呼叫一個 tool 就跳一次「要不要允許？」，四個 tool ×每步一次，人會按到崩潰，而且 `show_step` 卡住等人的時候還跳確認視窗會很混亂。

把這一條加進 Qoder 的工具允許清單：

```text
mcp__showme__*
```

（設計 §16 明列這是 demo 當日風險的處理方式。實際的設定欄位名稱一樣以 Qoder 文件為準。）

### Step 7：量 Request Timeout（設計 §16）

> 🙋 **這一步留給使用者手動做，agent 做不了。**
> 它需要「開著的 Qoder IDE」＋「一個真人在旁邊看時鐘、而且刻意什麼都不點」，兩樣都不是程式能代勞的東西。
> 實作 agent 已經把 Step 1–6 做完（契約測試綠、stdio 驗過、設定 JSON 與 allow list 寫好），**只剩這一步**。
> 量到的數字請自己填進 `A16_與B合流與Demo演練.md` 的「demo 前一天 checklist」。

`show_step` 會**卡住不回應**，預設最長 120 秒。IDE 那一端如果 30 秒就放棄，整個產品就 demo 不了。所以要先量出「IDE 到底肯等多久」。

量測步驟：

1. 先確認示範站有在跑（`http://localhost:3000`，見 `docs/sample-app.md`），或隨便一個能開的網頁也行。
2. 在 Qoder 對話裡讓 agent 呼叫：
   ```text
   start_tutorial(url="http://localhost:3000", goal="create a project")
   ```
   記下回傳的 `session_id` 與 `page.elements` 裡任一個 `uid`。
3. 再讓它呼叫（**把 `timeout_s` 設成 60，然後什麼都不要做**）：
   ```text
   show_step(session_id="<剛才那個>", uid="<剛才那個>", instruction="Click New Project",
             kind="click", step_index=1, step_total=4, timeout_s=60)
   ```
4. 開始看時鐘。三種結果：

   | 觀察到的現象 | 意思 | 處理 |
   |---|---|---|
   | 60 秒後 tool 正常回 `event: "timeout"` | IDE 肯等 ≥ 60 秒 | 再用 `timeout_s=120` 測一次，確認預設值也撐得過 |
   | 不到 60 秒 IDE 就報錯／請求中斷 | IDE 的 Request Timeout 比較短 | 記下那個秒數 `T`，去 Qoder 設定把 Request Timeout 調高到 ≥ 180 秒；調不了就在 demo 時**每一步都明確傳 `timeout_s`，並且設成小於 `T`** |
   | 完全沒反應也沒錯誤 | 可能根本沒接上 | 回 Step 4 用 stdio 手動確認 server 起得來 |

5. **把量到的數字寫進 `A16_與B合流與Demo演練.md` 的「demo 前一天 checklist」**，例如：「Qoder Request Timeout 實測：預設 ___ 秒；已調高到 ___ 秒；demo 用的 `timeout_s` = ___」。

> MVP **不會**因為這個問題去加第五個 tool 或做 `wait_for_user`（設計 §16 明寫：真的擋死再另開規格，不在這裡偷加）。真的調不動就縮短 `timeout_s`。

### Step 8：commit

```bash
git add tests/test_mcp_contract.py tests/conftest.py
git commit -m "test: pin the MCP tool contract (four tools, error field, show_step schema)"
```

> 本篇與 A11–A13 平行進行時，**這一步由主控在階段結束統一 commit**（見 `docs/plan/todo/2026-08-29-A11到A15實作-TODO.md`），平行 agent 自己不 commit。

---

## 8. 驗收清單

- [ ] `uv run pytest tests/test_mcp_contract.py -q` → 10 passed。（**與 A13 平行做時**，`test_end_tutorial_with_unknown_session_also_returns_an_error_field` 會紅到 A13 落地為止，其餘 9 條要綠。）
- [ ] `uv run pytest -m "not browser" -q` → 全綠、0 skipped。
- [ ] `list_tools()` 的名字集合**恰好**是 `{start_tutorial, inspect_page, show_step, end_tutorial}`，數量是 4。
- [ ] 沒有 `wait_for_user`。
- [ ] 四個 tool 都有非空的 `description`。
- [ ] `inspect_page` 傳假 `session_id` → `result.is_error` **不是** `True`，而且經過 `payload()` 取出的 dict 裡 `error` 是 `"session_not_found"`、`page` 是 `None`。
- [ ] `show_step` 的 `input_schema["properties"]` 恰好 8 個參數；`required` 不含 `expect_text` 與 `timeout_s`。
- [ ] `start_tutorial` / `inspect_page` / `end_tutorial` 的參數也對。
- [ ] `INSTRUCTIONS` 非空，而且含「you never act for them」「One show_step at a time」「LATEST page.elements」。
- [ ] 透過 MCP 層真的呼叫一次 `start_tutorial` 成功，`page.elements` 的 uid 是 `s1-*`。
- [ ] 手動 stdio（Step 4 **做法 A′**，Python subprocess）跑得出來：`server name : showme`、`instructions? : True`、四個 tool 名、stderr 全空。（做法 A 的 `printf | uv run showme` 只印得出 `initialize` 那一行，見 Step 4 的實測修正。）
- [ ] Qoder 的 MCP 設定 JSON 已寫好（`command: uv`、`args: ["--directory", "<repo 絕對路徑>", "run", "showme"]`），而且 Qoder 裡看得到 `showme` 這個 server。🙋 **需要 Qoder IDE，留給使用者手動。**
- [ ] allow list 已加 `mcp__showme__*`。🙋 **需要 Qoder IDE，留給使用者手動。**
- [ ] Request Timeout 已實測，數字已抄進 A16 的 checklist。🙋 **需要 Qoder IDE ＋ 真人看時鐘，留給使用者手動（見 Step 7 開頭的方框）。**
- [ ] `showme/**` 一行都沒改（本篇只加測試）。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `ImportError: cannot import name 'Client' from 'mcp'` | 裝到 v1 的 `mcp` | `uv run python -c "import mcp; print(mcp.__version__)"` 應該是 `2.x`；不是就檢查 `pyproject.toml` 的 `mcp[cli]` 並重跑 `uv sync` |
| `fixture 'mcp_client' not found` | Step 2 的 fixture 沒加進 `tests/conftest.py`，或加到別的檔 | 一定要在 `tests/conftest.py`；用 `uv run pytest --fixtures tests/test_mcp_contract.py \| grep mcp_client` 確認 |
| `test_start_tutorial_through_the_mcp_layer` 真的開了一個 Chrome | `set_app(app)` 沒生效——`server.py` 的 tool 沒有走 `get_app()`，而是在 module 載入時就 `ShowMeApp()` 了 | `server.py` 裡 tool body 必須是 `return await get_app().xxx(...)`，不可以在 module 頂層建 app |
| `payload()` 取出來的 dict 少了鍵、或整個是 `{"result": {...}}` 沒被攤開 | SDK 把回傳值當成純量包了一層，而且 `set(sc) == {"result"}` 沒成立（例如同時還有別的鍵） | 確認 `showme/server.py` 四個 tool 的回傳註記是 `dict[str, object]`（A07 已改），再跑一次 |
| `structured_content` 是 `None`，但 `is_error` 是 `False`，`content[0].text` 裡看得到完整的 JSON | 回傳註記推不出 output schema——多半是被改回沒有型別參數的裸 `-> dict`，或註記被拿掉了 | 改回 `-> dict[str, object]`（`showme/server.py` 與 `showme/app.py` 都要）。原因見 §7 Step 1 的方框與 A01 Step 10 |
| `structured_content` 是 `None`，`is_error` 是 `True` | tool handler 丟例外了 | 看 `result.content` 裡的錯誤字串，回頭修 `showme/app.py`；規格明訂**任何情況都要 return dict** |
| `test_end_tutorial_with_unknown_session_also_returns_an_error_field` 紅、`KeyError: 'ok'` | A13 還沒做完，`end_tutorial` 還回 `{"error": "not_implemented"}` | 正常的紅燈，等 A13 落地就綠。不要改測試 |
| 做法 A 的 `printf ... \| uv run showme` 只印出一行、拿不到 `tools/list` 的回應 | `printf` 寫完就關 stdin，server 讀到 EOF 就收攤，來不及回 `tools/list` | 改用 Step 4 的**做法 A′**（Python subprocess，把 stdin 留著、讀完才 terminate） |
| 想用 `timeout 30 uv run showme` 保底卻找不到指令 | macOS 預設沒有 GNU coreutils，`timeout` / `gtimeout` 都沒有 | 超時控制寫在 Python 裡（做法 A′ 的 `t.join(timeout=30)`），或裝 `brew install coreutils` |
| `assert required == SHOW_STEP_REQUIRED` 失敗 | 這版 SDK 對有預設值的參數處理方式不同 | 先確認 `"expect_text" not in required` 與 `"timeout_s" not in required` 這兩條有過（這兩條才是規格要求的）；`required` 的完整集合若真的不同，把那一行改成 `assert SHOW_STEP_REQUIRED <= required or required <= SHOW_STEP_PARAMS` 並在測試裡留註解說明 SDK 版本 |
| `input_schema` 這個屬性不存在（`AttributeError`） | 拿到的是序列化後的 dict 而不是 Tool 物件 | 官方 v2 的 Python 物件用 snake_case `.input_schema`；若你的物件是 dict，就改成 `tool["inputSchema"]` |
| `instructions` 是空的 | `MCPServer("showme", INSTRUCTIONS)` 用了位置參數 | 一定要寫成關鍵字：`MCPServer("showme", instructions=INSTRUCTIONS)`。v2 的第二、三個位置參數是 `title` / `description`，位置傳會塞錯欄位 |
| `uv run showme` 什麼都不印、看起來像當掉 | 這是正確行為，它在等 stdin | 貼 JSON 進去，或用做法 A 的 `printf ... \| uv run showme` |
| stdio 回應裡混進了 `print()` 的除錯訊息，Qoder 解析失敗 | 有人在產品程式碼裡 `print(...)` 到 stdout | stdout **只准**放 JSON-RPC。要印訊息一律用 `sys.stderr` 或 logging（預設就是 stderr） |
| `uv run mcp dev ...` 報 `npx not found` | 沒有 Node | 跳過 Inspector，用做法 A |
| Qoder 找不到 server / `command not found: uv` | IDE 的 PATH 跟終端機不一樣 | `which uv` 拿到完整路徑，填進 `"command"` |
| Qoder 每次呼叫都跳確認 | allow list 沒設 | 加 `mcp__showme__*` |
| `show_step` 在 Qoder 裡「還沒到 timeout_s 就失敗」 | IDE 的 Request Timeout 比 `timeout_s` 短 | 照 Step 7 調高；調不了就把 `timeout_s` 設得比它短 |
| 契約測試偶爾影響到別的測試 | `set_app(app)` 沒還原 | fixture 的 `finally: set_app(None)` 不能省 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `features/顯示步驟.feature` | Rule：操作失敗時寫在回傳的 error，不丟例外 | `test_unknown_session_is_a_normal_result_not_a_protocol_error`：`is_error is not True` 且 `error == "session_not_found"` |
| `features/檢查頁面.feature` | Rule：session 不存在時操作失敗且錯誤為 session_not_found（Example：`s_missing`） | 同上，而且是**透過真的 MCP 呼叫**驗的 |
| `features/結束教學.feature` | Rule：session 不存在時操作失敗且錯誤為 session_not_found | `test_end_tutorial_with_unknown_session_also_returns_an_error_field` |
| `features/顯示步驟.feature` | Rule：timeout_s 未傳或為 0 或負值時視為 120（「未傳」這一半） | `test_show_step_expect_text_and_timeout_s_are_optional`：schema 的 `required` 不含 `timeout_s`，所以 agent 真的可以不傳 |
| `features/顯示步驟.feature` | Rule：kind 為 observe 且 expect_text 為空時 expect_text_required（「可以不傳」這一半） | 同上，`required` 不含 `expect_text` |
| `features/等待使用者.feature` | Rule：MVP 不提供 wait_for_user，改用阻塞的 show_step | `test_there_is_no_wait_for_user_tool` |
| `.clarify/resolved/features/顯示步驟_錯誤是丟出ToolError還是寫在回傳值.md` | 錯誤通道 B：寫在回傳的 `error` 欄，MCP 呼叫仍成功 | 兩個 `is_error is not True` 的測試 |
| `.clarify/resolved/data/Step_timeout_s為0或負值時如何處理.md` | 答案 C：未傳、0、負值 → 120 | schema 的預設值 `timeout_s: float = 120` |
| `docs/design/showme.md` §7 | **約束：** server 名稱 `showme`；Qoder 全名 `mcp__showme__<tool>`；**只有**這四個工具 | `test_server_exposes_exactly_the_four_tools`；Step 5 的設定 JSON |
| `docs/design/showme.md` §7 | `MCPServer(name="showme", instructions=<SHOW protocol>)`；instructions 採 draft §7.5 意旨（教、不代做、一次一步、uid 來自最新 page），不是驗收字串 | `test_server_instructions_are_not_empty` 只驗**意旨關鍵字**，不整段比對 |
| `docs/design/showme.md` §13 | 只准用六個錯誤碼 | 契約測試只出現 `session_not_found` |
| `docs/design/showme.md` §14 | 測試層次第 3 層「MCP 契約（可後做）：stdio 列出四工具、無 `wait_for_user`、例外不會變成 `is_error`」 | 本篇整篇 |
| `docs/design/showme.md` §16 | 風險：Qoder 對長時間阻塞 tool 的 timeout → 活動前量、IDE 調高 Request Timeout；每個 tool 要人工確認 → allow list `mcp__showme__*` | Step 6、Step 7 |
| `docs/design/showme.md` §5 | **design：** 官方 `mcp` 的 `MCPServer` + `run(transport="stdio")`；ShowMe 內無 LLM | Step 4 手動 stdio 驗證 |
| `docs/design/showme.md` §3 Non-Goals | 不做第五個 tool、不做 pending 輪詢 | `test_there_is_no_wait_for_user_tool` + 「恰好四個」 |
