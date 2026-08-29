# A06｜瀏覽器層：JS 呼叫與假 overlay

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：`A05_注入overlay與emit橋.md` ｜ 下一篇：`A07_FakeBrowser與App骨架.md`
> 對應設計：`docs/design/showme.md` §10（Snapshot 與 uid）、§12（Overlay 邊界）、§15（S3 的 A 側前置） ｜ 對應切片：**S3 前置**
> 預估時間：55 分鐘

---

## 1. 這一篇要做什麼

兩件事：

1. 幫 `PlaywrightBrowser` 補上最後四個方法 —— `snapshot(n)`、`show(opts)`、`clear()`、`done(text)`。它們都只是 `page.evaluate(...)` 的薄包裝，把 `docs/handoff.md` 鎖死的四個 JS 呼叫包成 Python 方法。做完 `showme/browser.py` 就完成了。
2. 寫一份 **A 側的測試替身** `tests/fixtures/fake_overlay.js`，讓 A 現在就能驗證這四個包裝是對的，**不用等 B 把真的 overlay 寫完**。

> ### ⚠️ `tests/fixtures/fake_overlay.js` 不是產品 overlay
>
> 它**不是** B 的 `overlay/overlay.js`，也**不會**取代它、更不會被 demo 用到。
>
> 它只是一份「假貨」（test double）：只模仿 `docs/handoff.md` 鎖死的那四個函式的**介面與回傳形狀**，用最笨的方式實作（掃 `data-role` 屬性、把呼叫記進陣列、在 body 上加一個屬性）。這樣 A 就能驗證「我的 Python 包裝有沒有把參數傳對、有沒有把回傳值拿對」。
>
> 它**不做**的事：Driver.js 高亮、popover、a11y 角色白名單、完成觀察（listener），以及 —— 特別注意 —— **它不會自己 `emit`**。要模擬「人做完了」，測試自己用 `page.evaluate("window.__showme_emit({...})")` 手動打一發。
>
> 真正的高亮與完成判定是 B 的工作（`docs/design/showme.md` §15.1「人員 A 不要做：Driver.js 樣式、完成觀察 listener」）。A16 合流時會用 B 的真 overlay 再跑一次端到端。

---

## 2. 做完會看到什麼

### 2.1 四個包裝把 Python 呼叫送進頁面

```text
   Python（showme/browser.py）                頁面（overlay.js 或 fake_overlay.js）
   ────────────────────────────               ─────────────────────────────────────
   await b.snapshot(1)
     page.evaluate("(n) => window.__showme.snapshot(n)", 1)
                                    ─────────▶ window.__showme.snapshot(1)
                                    ◀───────── { elements: [...], truncated: false }
     回傳 dict ──────────────────────┘         （A03 的 build_page 之後才補 url/title）

   await b.show({uid, instruction, kind, index, total, expect})
     page.evaluate("(o) => window.__showme.show(o)", opts)
                                    ─────────▶ window.__showme.show(opts)
                                    ◀───────── undefined  → Python None

   await b.clear()   ──────────────────────▶ window.__showme.clear()
   await b.done(t)   ──────────────────────▶ window.__showme.done(t)
```

### 2.2 假 overlay 怎麼把 DOM 變成 elements

```text
  dashboard.html                        __showme.snapshot(1) 回傳
  ────────────────────────────          ─────────────────────────────────────────
  <h1>Dashboard</h1>          ← 跳過（沒有 data-role）
  <button data-role="button"            {
          data-testid="new-project">      uid:    "s1-1",
    New Project                           role:   "button",
  </button>                               name:   "New Project",
                                          testid: "new-project"
                                        },
  <a data-role="link"                   {
     href="#settings">                    uid:    "s1-2",
    Settings                              role:   "link",
  </a>                                    name:   "Settings",
                                          testid: ""       ← 沒有 data-testid 也有這個鍵
                                        }
                                        truncated: false

  ※ n 由 Python 傳進來（這裡是 1）。假 overlay 只負責組 "s" + n + "-" + (i+1)。
    Python 呼叫 snapshot(2) 就會拿到 s2-1、s2-2。世代由 A 決定，不是 B。
```

### 2.3 三份 overlay 的關係（別搞混）

```text
                       ┌──────────────────────────────────────────┐
                       │ window.__showme 的介面（docs/handoff.md） │
                       │  snapshot(n) / show(o) / clear() / done(t)│
                       └───────────┬──────────────────────────────┘
              實作 A              │              實作 B
      ┌───────────────────────────┴──────────────────────────┐
      ▼                                                      ▼
  overlay/overlay.js                        tests/fixtures/fake_overlay.js
  ── B 的產品檔 ──                          ── A 的測試替身 ──
  現在：stub，snapshot 回空陣列             掃 [data-role]、記錄呼叫、
  之後：Driver.js 高亮、popover、           在 body 加 data-showme-showing、
        完成觀察、每步 emit 一次            插入 #showme-banner
                                            不會自己 emit
      ▲                                                      ▲
      │ A05 的測試用它                                        │ A06、A15 的測試用它
      │ （只驗「注入成功」）                                   │ （驗四個包裝的參數與回傳）
      └───────── PlaywrightBrowser(overlay_path=...) ─────────┘
```

### 2.4 這一篇做完的檔案樹（★ = 本篇新增／修改）

```text
hackathonQoder/
├── showme/
│   └── browser.py                       ★ 修改（補最後四個方法，本篇之後完成）
└── tests/
    ├── test_browser_js.py               ★ 新增
    └── fixtures/
        ├── fake_overlay.js              ★ 新增（A 側測試替身）
        └── pages/
            ├── dashboard.html           A04 已有
            ├── new_project.html         ★ 新增
            └── many_buttons.html        ★ 新增（151 個按鈕，測 150 截斷）
```

---

## 3. 開始前先確認

- [ ] **A05 的驗收都打勾**：
  ```bash
  cd /Users/linjunting/hackathonQoder
  uv run pytest -m browser -q
  ```
  預期最後一行：`10 passed in 8.xxs`

- [ ] **`browser.py` 已經有 `_on_emit` 與 `set_emit_handler`，但還沒有那四個方法**：
  ```bash
  grep -n "    async def \|    def " showme/browser.py | sed -n '/PlaywrightBrowser/,$p'
  grep -c "async def snapshot" showme/browser.py
  ```
  第二個指令預期輸出 `1` —— 只有 `BrowserLike` 裡那一行宣告，`PlaywrightBrowser` 還沒有實作。

- [ ] **`static_server` 與 `dashboard.html` 可用**：
  ```bash
  ls tests/fixtures/pages/
  ```
  預期輸出：`dashboard.html`

- [ ] **A03 的 `rules.py` 在**（本篇不會 import 它，但要知道分工）：
  ```bash
  grep -n "^MAX_ELEMENTS\|^def build_page" showme/rules.py
  ```
  預期看到 `MAX_ELEMENTS = 150` 與 `def build_page(...)`。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| `page.evaluate(expr, arg)` | 「請頁面幫我跑這段 JS，把結果拿回來」。`expr` 是 JS 運算式或箭頭函式的字串；`arg` 是要傳進去的參數（會被序列化成 JSON 再送過去）。 |
| 序列化（serialize） | 把 Python 的 dict／list／字串轉成 JSON 送進瀏覽器，回來時再轉回 Python 物件。所以只能傳「純資料」，不能傳函式或 DOM 節點。 |
| test double（測試替身） | 為了測試而做的假貨。它只長得像真貨、行為夠用就好。`fake_overlay.js` 與 A07 的 `FakeBrowser` 都是。 |
| `data-role` | **這個專案測試自己約的標記**，寫在測試 HTML 上，讓假 overlay 知道哪些元素要收。產品 overlay 是看 a11y 角色，不看它。 |
| `data-showme-uid` | overlay 走訪時寫回 DOM 的屬性，讓 `show(opts)` 能靠 `uid` 找回真實節點。真 overlay 與假 overlay 都要寫（`docs/design/showme.md` §10）。 |
| `truncated` | 元素多過 150 個時的旗標。`true` 表示「還有更多，我只給你前 150 個」。 |
| a11y name | 無障礙名稱：螢幕閱讀器會唸出來的那個字（來自 `aria-label`、`<label>`、或元素文字）。沒有時規格要求填 `""`，元素仍要列出。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 修改 | `showme/browser.py` | 補 `snapshot`／`show`／`clear`／`done` 四個 `evaluate` 包裝；本篇之後這個檔完成 |
| 新增 | `tests/fixtures/fake_overlay.js` | **A 側測試替身**，模仿 `window.__showme` 的介面 |
| 新增 | `tests/fixtures/pages/new_project.html` | 測試頁：heading `New Project` + 一個 textbox + 一個 Create 按鈕 |
| 新增 | `tests/fixtures/pages/many_buttons.html` | 測試頁：151 個按鈕，驗 150 截斷與 `truncated=true` |
| 新增（測試） | `tests/test_browser_js.py` | 四個包裝的行為 |

**不要動**：`overlay/overlay.js`（B 的）、`showme/rules.py`、`showme/session.py`、`showme/server.py`。

---

## 6. 介面約定

### 用到（來自 A04／A05）

```python
class PlaywrightBrowser:
    def __init__(self, overlay_path: Path = OVERLAY_PATH, headless: bool = False) -> None: ...
    async def launch(self) -> None: ...      # 已經會 add_init_script(path=self.overlay_path)
    self.page                                # playwright Page
```

`overlay_path` 是建構子參數，所以測試只要傳 `PlaywrightBrowser(overlay_path=FAKE_OVERLAY, headless=True)`，注入的就是假 overlay 而不是 B 的檔案。**這就是「不用等 B」的機制**。

### 提供（給後面幾篇）

```python
class PlaywrightBrowser:
    async def snapshot(self, n: int) -> dict:
        """回 window.__showme.snapshot(n) 的原始結果：{"elements": [...], "truncated": bool}。
        注意：這是 raw，還沒有 url／title。組成 Page 是 A03 的 build_page + A07 的 _take_snapshot。"""

    async def show(self, opts: dict) -> None:
        """opts 的六個鍵：uid、instruction、kind、index、total、expect。"""

    async def clear(self) -> None: ...
    async def done(self, text: str) -> None: ...
```

- A07 的 `ShowMeApp._take_snapshot` 會呼叫 `snapshot(n)`，再交給 `build_page(raw, url, title)`。
- A12 的 `ShowMeApp.show_step` 會呼叫 `show({...})` 與（timeout 時）`clear()`。
- A13 的 `ShowMeApp.end_tutorial` 會呼叫 `clear()` + `done(DONE_BANNER_TEXT)`。
- A15 的端到端測試會用 `PlaywrightBrowser(overlay_path=fake_overlay, headless=True)` 把整條路跑一遍。

### 鎖死的形狀（`docs/handoff.md`，不可改）

```text
window.__showme.snapshot(n)  → { elements: [{uid, role, name, testid}], truncated: bool }
window.__showme.show({ uid, instruction, kind, index, total, expect })
window.__showme.clear()
window.__showme.done(text)
```

`show.expect` 就是 MCP 的 `expect_text`；`show.index`／`show.total` 就是 `step_index`／`step_total`。名字在這條邊界上換過。

---

## 7. 步驟

### Step 1：寫假 overlay（10 分鐘）

```bash
mkdir -p tests/fixtures
```

新增 `tests/fixtures/fake_overlay.js`：

```javascript
// tests/fixtures/fake_overlay.js
//
// A 側測試替身（test double）—— 不是產品 overlay。
//
// 這個檔案只模仿 docs/handoff.md 鎖死的介面，讓 A 能在 B 的 overlay 寫好之前
// 驗證 showme/browser.py 的四個 evaluate 包裝。它刻意做得很笨：
//   - 掃 [data-role]（測試 HTML 自己標的），不做 a11y 角色推導
//   - 不用 Driver.js，只在 body 上加一個屬性當「有沒有在 show」的證據
//   - 沒有完成觀察 listener，也不會自己發出完成事件
//     （測試要模擬「人做完了」時，自己用 page.evaluate 手動打一發 emit）
//
// 產品 overlay 在 overlay/overlay.js，由 B 負責。

(function () {
  var MAX_ELEMENTS = 150;
  var calls = [];

  function collect(n) {
    var nodes = document.querySelectorAll("[data-role]");
    var elements = [];
    for (var i = 0; i < nodes.length && i < MAX_ELEMENTS; i += 1) {
      var node = nodes[i];
      var uid = "s" + n + "-" + (i + 1);
      node.setAttribute("data-showme-uid", uid);
      elements.push({
        uid: uid,
        role: node.getAttribute("data-role") || "",
        name: (node.textContent || "").trim(),
        testid: node.getAttribute("data-testid") || "",
      });
    }
    return { elements: elements, truncated: nodes.length > MAX_ELEMENTS };
  }

  window.__showme = {
    _calls: calls,

    snapshot: function (n) {
      calls.push(["snapshot", n]);
      return collect(n);
    },

    show: function (opts) {
      calls.push(["show", opts]);
      document.body.setAttribute("data-showme-showing", opts.uid);
    },

    clear: function () {
      calls.push(["clear"]);
      document.body.removeAttribute("data-showme-showing");
    },

    done: function (text) {
      calls.push(["done", text]);
      var banner = document.getElementById("showme-banner");
      if (!banner) {
        banner = document.createElement("div");
        banner.id = "showme-banner";
        document.body.appendChild(banner);
      }
      banner.textContent = text;
    },
  };
})();
```

幾個要看懂的點：

- `document.querySelectorAll("[data-role]")` 回傳的順序**就是 DOM 順序**，符合 clarify「硬上限 150，依 DOM 走訪順序取前 150，不分 viewport」。
- 迴圈條件 `i < nodes.length && i < MAX_ELEMENTS`：最多收 150 筆。
- `truncated: nodes.length > MAX_ELEMENTS`：剛好 150 時是 `false`，151 個才是 `true`。這正是 clarify 定的邊界。
- `node.setAttribute("data-showme-uid", uid)`：把 uid 寫回 DOM，跟真 overlay 一樣（`docs/design/showme.md` §10）。這樣 `show(opts)` 才有辦法用 uid 找回節點 —— 假 overlay 這裡偷懶沒有真的去找，但屬性照寫，A16 合流時比較好對照。
- `testid: node.getAttribute("data-testid") || ""`：**沒有 `data-testid` 時給空字串，不是省略鍵**。這是 clarify 明訂的（`PageElement_元素沒有data-testid時testid欄位如何表示.md`，回答 B）。
- `name: (node.textContent || "").trim()`：假 overlay 用文字內容當 name。`<input>` 的 `textContent` 是空字串，所以 textbox 的 `name` 會是 `""` —— 剛好可以拿來驗「沒有 a11y name 的互動元素仍列出且 name 為空字串」。
- `window.__showme._calls`：把每次呼叫記下來，測試想確認參數細節時可以讀。這個欄位**只有假 overlay 有**，產品 overlay 沒有，所以正式程式碼裡永遠不要用它 —— 只有測試可以。

### Step 2：寫兩份測試頁（8 分鐘）

`tests/fixtures/pages/new_project.html`：

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>New Project</title>
  </head>
  <body>
    <h1 data-role="heading">New Project</h1>
    <input data-role="textbox" data-testid="project-name" aria-label="Project name" />
    <button data-role="button" data-testid="create">Create</button>
  </body>
</html>
```

三個 `data-role` 元素，掃出來會是 `s1-1`（heading）、`s1-2`（textbox）、`s1-3`（button）。

textbox 的 `name` 會是 `""` —— 因為假 overlay 是用 `textContent` 當 name，而 `<input>` 沒有文字內容。這一點測試會斷言，剛好對上 `開始教學.feature` 的 Rule「沒有 a11y name 的互動元素仍列出且 name 為空字串」。

> `aria-label="Project name"` 是刻意留著的：**真的** overlay（B 寫的）會從 `aria-label` 推出 a11y name `"Project name"`，所以 A07 的 `fake_browser` fixture 裡那個假頁面才會寫 `{"role": "textbox", "name": "Project name", ...}`。兩者不一樣不是矛盾 —— 一個是「假 overlay 在真瀏覽器裡掃出來的」，一個是「假瀏覽器直接餵的資料」，各自測各自那一層。

`tests/fixtures/pages/many_buttons.html`：

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Many Buttons</title>
  </head>
  <body>
    <h1>Many Buttons</h1>
    <div id="list"></div>
    <script>
      var list = document.getElementById("list");
      for (var i = 1; i <= 151; i += 1) {
        var button = document.createElement("button");
        button.setAttribute("data-role", "button");
        button.setAttribute("data-testid", "btn-" + i);
        button.textContent = "Button " + i;
        list.appendChild(button);
      }
    </script>
  </body>
</html>
```

**為什麼用 `<script>` 生成，而不是把 151 個 `<button>` 寫出來？**

- 151 行幾乎一樣的 HTML 沒有人讀得出「到底是 150 還是 151」；一個 `i <= 151` 的迴圈一眼就能檢查。改成 150 或 200 來試邊界也只要改一個數字。
- 生成失敗不會靜悄悄過去：如果 script 沒跑，`data-role` 元素會是 0 個，測試會以 `assert len(...) == 150` 失敗，訊息很清楚。
- **時序上沒有風險**：`add_init_script` 在 document 建立後、頁面自己的 `<script>` **之前**執行，所以 `window.__showme` 先存在；接著頁面的迴圈跑完；`page.goto()` 等到 `load` 才回來；Python 再 `evaluate` 呼叫 `snapshot(1)`。呼叫時 151 個按鈕早就都在 DOM 裡了。

```text
  document 建立 ─▶ fake_overlay.js（定義 __showme）
                 ─▶ 頁面 <script>（append 151 個 button）
                 ─▶ load 事件 ─▶ goto() 回到 Python
                 ─▶ await browser.snapshot(1)   ← 這時才掃 DOM
```

### Step 3：先寫測試，看它紅（10 分鐘）

新增 `tests/test_browser_js.py`：

```python
"""A06：snapshot / show / clear / done 四個 evaluate 包裝。

注入的是 tests/fixtures/fake_overlay.js（A 側測試替身），不是 B 的產品 overlay。
所以這個檔在 B 完成之前就能全綠。

    uv run pytest -m browser tests/test_browser_js.py -q
"""

from __future__ import annotations

from pathlib import Path

import pytest

from showme.browser import PlaywrightBrowser

pytestmark = [pytest.mark.anyio, pytest.mark.browser]

FAKE_OVERLAY = Path(__file__).parent / "fixtures" / "fake_overlay.js"
DONE_TEXT = "✅ Done — you created a project"


@pytest.fixture
async def browser():
    b = PlaywrightBrowser(overlay_path=FAKE_OVERLAY, headless=True)
    await b.launch()
    try:
        yield b
    finally:
        await b.close()


async def test_snapshot_returns_elements_with_all_four_keys(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    raw = await browser.snapshot(1)

    assert raw["truncated"] is False
    assert raw["elements"] == [
        {"uid": "s1-1", "role": "button", "name": "New Project", "testid": "new-project"},
        {"uid": "s1-2", "role": "link", "name": "Settings", "testid": ""},
    ]


async def test_snapshot_number_flows_into_uid(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    raw = await browser.snapshot(2)

    assert [element["uid"] for element in raw["elements"]] == ["s2-1", "s2-2"]


async def test_snapshot_writes_uid_back_to_dom(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")
    await browser.snapshot(1)

    attribute = await browser.page.evaluate(
        "document.querySelector('button').getAttribute('data-showme-uid')"
    )

    assert attribute == "s1-1"


async def test_element_without_a11y_name_still_listed(browser, static_server):
    await browser.open(f"{static_server}/new_project.html")

    raw = await browser.snapshot(1)

    assert [element["role"] for element in raw["elements"]] == ["heading", "textbox", "button"]
    assert raw["elements"][1] == {
        "uid": "s1-2",
        "role": "textbox",
        "name": "",
        "testid": "project-name",
    }


async def test_snapshot_truncates_at_150(browser, static_server):
    await browser.open(f"{static_server}/many_buttons.html")

    raw = await browser.snapshot(1)

    assert len(raw["elements"]) == 150
    assert raw["truncated"] is True
    assert raw["elements"][0]["name"] == "Button 1"
    assert raw["elements"][-1]["uid"] == "s1-150"
    assert raw["elements"][-1]["name"] == "Button 150"


async def test_show_marks_the_page_and_clear_removes_it(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")
    await browser.snapshot(1)

    await browser.show(
        {
            "uid": "s1-1",
            "instruction": "Click New Project",
            "kind": "click",
            "index": 1,
            "total": 4,
            "expect": "",
        }
    )
    showing = await browser.page.evaluate(
        "document.body.getAttribute('data-showme-showing')"
    )

    await browser.clear()
    cleared = await browser.page.evaluate(
        "document.body.getAttribute('data-showme-showing')"
    )

    assert showing == "s1-1"
    assert cleared is None


async def test_show_receives_all_six_keys(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")
    opts = {
        "uid": "s1-2",
        "instruction": "Read the heading",
        "kind": "observe",
        "index": 3,
        "total": 5,
        "expect": "Settings",
    }

    await browser.show(opts)

    recorded = await browser.page.evaluate(
        "window.__showme._calls.filter((c) => c[0] === 'show').map((c) => c[1])"
    )
    assert recorded == [opts]


async def test_done_inserts_the_banner(browser, static_server):
    await browser.open(f"{static_server}/dashboard.html")

    await browser.done(DONE_TEXT)

    text = await browser.page.evaluate(
        "document.getElementById('showme-banner').textContent"
    )
    assert text == DONE_TEXT
```

說明幾個測試的用意：

- `test_snapshot_returns_elements_with_all_four_keys` 一次驗三件事：uid 格式 `s{n}-{index}`、四個鍵都在、`Settings` 的 `testid` 是 `""` 而不是缺鍵。這對得上 `開始教學.feature` 的 Example（`s1-4 button New Project new-project` / `s1-7 link Settings （空）`）—— 序號不同是因為我們的測試頁只有兩個元素，規格例子那頁有更多；**格式與鍵才是重點**。
- `test_snapshot_number_flows_into_uid` 驗「世代由 A 決定」：Python 傳 2，頁面就組 `s2-*`。這是 `docs/handoff.md`「A 給 `n`，B 組 `s{n}-{index}`」的直接驗證。
- `test_element_without_a11y_name_still_listed` 對應 `開始教學.feature` 的 Rule「沒有 a11y name 的互動元素仍列出且 name 為空字串」。
- `test_snapshot_truncates_at_150` 對應 Rule「硬上限 150⋯超過 150 個時只留前 150 且 truncated 為 true」。**注意 `browser.py` 這一層不做截斷**，截斷發生在頁面裡（真 overlay 由 B 做），而 A03 的 `build_page` 會再保險一次。兩層都做是刻意的：B 若漏了，Python 這層仍然守得住。
- `cleared is None`：`getAttribute` 找不到屬性時回 JS 的 `null`，到 Python 變成 `None`。
- `test_show_receives_all_six_keys` 讀假 overlay 的 `_calls`，確認六個鍵一字不差地送到了。這個測試**只在假 overlay 下有意義**，A16 換成真 overlay 後它會失敗 —— 所以 A16 的合流清單會把它標成「假 overlay 專用」。

跑一次看紅：

```bash
uv run pytest -m browser tests/test_browser_js.py -q
```

預期輸出：

```text
FFFFFFFF                                                            [100%]
=================================== FAILURES ===================================
E       AttributeError: 'PlaywrightBrowser' object has no attribute 'snapshot'
...
8 failed in 6.02s
```

### Step 4：補上四個包裝（5 分鐘）

在 `showme/browser.py` 的 `title()` 之後、`set_emit_handler()` 之前，插入：

```python
    async def snapshot(self, n: int) -> dict:
        return await self.page.evaluate("(n) => window.__showme.snapshot(n)", n)

    async def show(self, opts: dict) -> None:
        await self.page.evaluate("(o) => window.__showme.show(o)", opts)

    async def clear(self) -> None:
        await self.page.evaluate("() => window.__showme.clear()")

    async def done(self, text: str) -> None:
        await self.page.evaluate("(t) => window.__showme.done(t)", text)
```

**為什麼寫成箭頭函式 `"(n) => ..."` 而不是直接字串內插？**

因為要**傳參數**。`page.evaluate(expr, arg)` 只在 `expr` 長得像函式時才會把 `arg` 餵進去（官方文件的用法：`page.evaluate('num => num', 42)`，見 https://playwright.dev/python/docs/evaluating ）。

千萬不要寫成 `page.evaluate(f"window.__showme.snapshot({n})")` 這種字串拼接：`opts` 裡的 `instruction` 是模型寫的自由文字，可能有引號、反斜線、換行 —— 拼進 JS 字串就會炸，或更糟，把後面的程式碼截斷。用參數傳遞時 Playwright 會走 JSON 序列化，不會有這個問題。

`clear()` 沒有參數，所以寫成 `"() => ..."`（也可以只寫 `"window.__showme.clear()"`，但四個保持同一種寫法比較不會漏改）。

回傳值：`snapshot` 拿到的是 JS 物件轉成的 Python dict；另外三個 JS 都回 `undefined`，所以 Python 拿到 `None`，我們直接丟掉（方法宣告成 `-> None`）。

### Step 5：跑測試看它綠（3 分鐘）

```bash
uv run pytest -m browser tests/test_browser_js.py -q
```

預期輸出：

```text
........                                                            [100%]
8 passed in 6.44s
```

全部瀏覽器測試：

```bash
uv run pytest -m browser -q
```

預期輸出：

```text
..................                                                  [100%]
18 passed in 12.31s
```

（A04 四個 + A05 六個 + 本篇八個 = 18。）

不開瀏覽器那組：

```bash
uv run pytest -m "not browser" -q
```

預期最後一行類似：`28 passed, 18 deselected in 0.44s`

### Step 6：確認 `browser.py` 已經完成（3 分鐘）

**這一篇改完後 `showme/browser.py` 的完整內容**（之後 A07–A16 都不再改這個檔）：

```python
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
```

快速自檢：`PlaywrightBrowser` 的方法應該剛好 13 個（含 `__init__`），順序是
`__init__ → launch → _on_emit → is_alive → open → current_url → title → snapshot → show → clear → done → set_emit_handler → close`。

```bash
grep -n "    def \|    async def " showme/browser.py | tail -13
```

### Step 7：commit（2 分鐘）

```bash
git add showme/browser.py tests/test_browser_js.py tests/fixtures/fake_overlay.js \
        tests/fixtures/pages/new_project.html tests/fixtures/pages/many_buttons.html
git commit -m "feat(browser): wrap __showme snapshot/show/clear/done with a fake overlay for tests"
```

預期輸出：

```text
[main xxxxxxx] feat(browser): wrap __showme snapshot/show/clear/done with a fake overlay for tests
 5 files changed, 2xx insertions(+)
```

---

## 8. 驗收清單

- [ ] `showme/browser.py` 有 13 個 `PlaywrightBrowser` 成員，順序如 Step 6。
- [ ] `tests/fixtures/fake_overlay.js` 存在，檔頭註解明講「不是產品 overlay」，而且**沒有**任何 `__showme_emit` 呼叫。
  ```bash
  grep -c "__showme_emit" tests/fixtures/fake_overlay.js
  ```
  預期輸出：`0`
- [ ] `tests/fixtures/pages/` 有三個檔：`dashboard.html`、`new_project.html`、`many_buttons.html`。
- [ ] `uv run pytest -m browser tests/test_browser_js.py -q` → `8 passed`。
- [ ] `uv run pytest -m browser -q` → `18 passed`。
- [ ] `uv run pytest -m "not browser" -q` → 全綠，`18 deselected`。
- [ ] `overlay/overlay.js` 沒有被改（`git status` 看不到它）。
- [ ] commit 已建立，只含上面五個檔。

---

## 9. 常見問題與排錯

| 症狀 | 原因 | 怎麼處理 |
|---|---|---|
| `TypeError: window.__showme.snapshot is not a function` | 注入的還是 B 的 stub，或 `FAKE_OVERLAY` 路徑錯 | 在測試裡印 `print(FAKE_OVERLAY, FAKE_OVERLAY.exists())`；確認 fixture 有傳 `overlay_path=FAKE_OVERLAY`。 |
| `raw["elements"] == []`（空的） | 注入的是 B 的 stub（它就是回空陣列） | 同上。**這也是一個好徵兆**：代表 A05 的注入機制正常，只是換錯檔。 |
| uid 是 `s1-1` 但你以為該是 `s1-4` | 規格 Example 的頁面元素比較多，我們的測試頁只有兩個 | 這是預期的。要驗的是**格式**（`s{n}-{index}`，1-based）與四個鍵，不是序號本身。 |
| `len(raw["elements"])` 是 151 | 假 overlay 的迴圈條件寫錯 | 檢查 `i < nodes.length && i < MAX_ELEMENTS`，以及 `MAX_ELEMENTS = 150`。 |
| `truncated` 在剛好 150 個時是 `True` | 用了 `>=` 而不是 `>` | `nodes.length > MAX_ELEMENTS`，clarify 明訂「≤150 則 truncated=false」。 |
| `many_buttons.html` 掃出 0 個元素 | 頁面 `<script>` 出錯（例如少了分號、瀏覽器不支援語法） | 在 DevTools Console 看紅字；或暫時把 `browser.page.on("console", print)` 加進 fixture。用的是 `var` 與字串相加，任何瀏覽器都吃。 |
| `assert cleared is None` 失敗、拿到 `''` | `removeAttribute` 寫成 `setAttribute(..., "")` | 一定要用 `removeAttribute`；空字串屬性仍然「存在」。 |
| `show` 的 `opts` 少一個鍵，測試卻過了 | 假 overlay 不檢查鍵 | 這是刻意的（假貨不做驗證）。真正保證六個鍵齊全的是 A12 `app.show_step` 組 dict 的那段程式，以及 `test_show_receives_all_six_keys`。 |
| `done` 之後找不到 `#showme-banner` | 頁面 body 還沒建立（例如在 `about:blank` 上呼叫） | 先 `await browser.open(...)` 再 `done(...)`。 |
| A16 換上 B 的真 overlay 後 `test_show_receives_all_six_keys` 紅了 | 真 overlay 沒有 `_calls` | 預期的。那個測試是假 overlay 專用；A16 的合流清單會處理。其他測試（uid 格式、四個鍵、150 截斷）換真 overlay 後**應該仍然綠**，若不綠就是 B 的 walker 沒照 handoff 做，把差異貼給 B。 |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/spec/features/開始教學.feature` | Rule：`page.elements` 硬上限 150，依 DOM 走訪順序取前 150，不分 viewport（兩個 Example：≤150 → `truncated=false`；151 → 150 筆且 `true`） | `test_snapshot_truncates_at_150`（151 個按鈕 → 150 筆 + `truncated=True`）與 `test_snapshot_returns_elements_with_all_four_keys`（2 個元素 → `truncated=False`）。 |
| `docs/spec/features/開始教學.feature` | Rule：`page.elements` 的 `testid` 鍵永遠存在，沒有 `data-testid` 時為空字串（Example：Settings 沒有 testid） | `dashboard.html` 的 Settings 連結沒有 `data-testid`；測試斷言 `"testid": ""`。 |
| `docs/spec/features/開始教學.feature` | Rule：沒有 a11y name 的互動元素仍列出且 name 為空字串（`#TODO`） | `new_project.html` 的 `<input>` 沒有文字內容 → `name: ""` 但仍在清單裡（`test_element_without_a11y_name_still_listed`）。 |
| `docs/spec/features/開始教學.feature` | Rule：成功開始後回傳第一份濃縮 page，uid 的 snapshot# 為 1 | 本篇提供管道：`snapshot(1)` → uid `s1-*`。真正在 `start_tutorial` 成功時把 n 設成 1，是 A07 的 `_take_snapshot` + A08。 |
| `docs/spec/features/檢查頁面.feature` | Rule：成功時 uid snapshot# 比上一份加一（Example：`s1-4` → `s2-4`） | `test_snapshot_number_flows_into_uid` 驗證 n 由 Python 傳、uid 跟著變（`s1-*` → `s2-*`）。「+1」的計數在 A07 的 `_take_snapshot`。 |
| `docs/spec/.clarify/resolved/data/Page_elements超過上限時如何截斷並標記truncated.md` | 回答 B：硬上限 150、DOM 順序、不分 viewport、≤150 → `false` | 假 overlay 用 `querySelectorAll` 的 DOM 順序、`i < 150`、`nodes.length > 150`。沒有任何 viewport／幾何判斷。 |
| `docs/spec/.clarify/resolved/data/PageElement_元素沒有data-testid時testid欄位如何表示.md` | 回答 B：鍵永遠存在，沒有時為空字串 | `testid: node.getAttribute("data-testid") \|\| ""`。 |
| `docs/spec/.clarify/resolved/data/PageElement_uid的snapshot編號何時遞增.md` | 回答 A：每次產生 snapshot 都加一；陳舊 snapshot# 的 uid 必然不在最新 elements | 本篇證明 uid 真的帶世代（`s1-*` vs `s2-*`），所以陳舊 uid 一定對不上。比對邏輯在 A03 的 `uid_in_page` + A11。 |
| `docs/spec/erm.dbml` | `PageElement.uid` 格式 `s{snapshot#}-{index}`；`Page.truncated` | 假 overlay 組 `"s" + n + "-" + (i + 1)`（1-based，對齊規格例子 `s1-4`）。 |
| `docs/spec/features/結束教學.feature` | Rule：成功結束後清掉 overlay；完成 banner 文案固定 | 本篇提供 `clear()` 與 `done(text)` 兩個管道並各有測試；`end_tutorial` 的呼叫順序與固定文案在 A13。 |
| `docs/design/showme.md` §10 | Walker 在 overlay：`__showme.snapshot(n)` 寫 `data-showme-uid` 並回傳 elements；Python 組 `url`／`title` | `test_snapshot_writes_uid_back_to_dom`；`browser.snapshot()` 只回 raw，`url`／`title` 由 `current_url()`／`title()` 另外取（A07 的 `_take_snapshot` 合起來）。 |
| `docs/design/showme.md` §12 | `window.__showme` 的四個方法職責 | 四個 `evaluate` 包裝一一對應，沒有多開第五個。 |
| `docs/design/showme.md` §14 | 測試策略：「overlay 在 Playwright 測頁的 fixture」 | `tests/fixtures/pages/*.html` + `fake_overlay.js`。 |
| `docs/design/showme.md` §15.1 | 人員 A **不要做**：Driver.js 樣式、完成觀察 listener | 假 overlay 兩者都沒有，而且不自己 emit；產品 overlay 仍歸 B。 |
| `docs/handoff.md` | `snapshot(n) → { elements, truncated }`、`show({uid, instruction, kind, index, total, expect})`、`clear()`、`done(text)`；A 給 `n`，B 組 uid | 四個包裝的簽名與 `test_show_receives_all_six_keys` 逐項對齊。 |
