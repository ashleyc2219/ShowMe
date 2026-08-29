# A16｜與 B 合流與 Demo 演練

> **這只是黑客松開發專案，不要鑽牛角尖。**

> 前一篇：[A15_真瀏覽器端到端.md](A15_真瀏覽器端到端.md)　｜　下一篇：無；回到 [A00_導讀與總覽.md](A00_導讀與總覽.md) 檢查全部驗收
> 對應設計：`docs/design/showme.md` §6、§12、§15（S7/S8/S9）、§15.1（兩人分工與接縫）、§16（Demo 當日風險）、§17（open questions）｜ 對應切片：S7 / S8 / S9
> 預估時間：60–90 分鐘（不含示範站 `npm install` 的等待時間）

---

## 1. 這一篇要做什麼

**這一篇不寫程式。** 前面十五篇把 A 這一半做完了（四個 tool、Session 狀態機、阻塞等待、MCP 契約、真瀏覽器端到端），但 demo 要成立還差三件事：

1. 把 **B 的 `overlay/overlay.js`** 接上來，並逐項對照 `docs/handoff.md` 的鎖死名字確認接縫沒歪。
2. 把 **示範站 finefoods-antd** 跑起來，確認 Chrome 開得了、`start_tutorial` 拍得出元素清單。
3. 排練一次**手動 demo 劇本**：Qoder 對話一句 → 四個 tool 依序被呼叫 → 每一步畫面該長什麼樣 → 完成 banner。

最後把 A 側的設計決定整理成一張表（哪些是規格、哪些是「A 先決定、可改」），並把 A00–A16 從 `docs/plan/unfinish/` 搬到 `docs/plan/finish/`。

---

## 2. 做完會看到什麼

### 2.1 合流前 vs 合流後

```text
         合流前（A15 做完的狀態）                    合流後（本篇）
   ┌──────────────────────────────┐        ┌──────────────────────────────┐
   │ Qoder Agent                  │        │ Qoder Agent          （真的） │
   │   ↓ 手動打 JSON / pytest      │        │   ↓ MCP stdio                │
   │ ShowMe Python        （真的） │        │ ShowMe Python        （真的） │
   │   ↓ Playwright               │        │   ↓ Playwright               │
   │ headless Chromium    （真的） │        │ headed Chrome        （真的） │
   │   ↓                          │        │   ↓                          │
   │ fake_overlay.js      （假的） │  ===>  │ overlay/overlay.js   （B 的） │
   │   ↓                          │        │   ↓  Driver.js 箭頭 + popover │
   │ dashboard.html       （假的） │        │ finefoods-antd :3000 （真的） │
   │   ↓                          │        │   ↓                          │
   │ 測試手動 evaluate emit（假的） │        │ 人真的點下去         （真的） │
   └──────────────────────────────┘        └──────────────────────────────┘

   A 這邊要改的程式碼：0 行。
   要做的事：跑測試、對照接縫、排練。
```

### 2.2 Demo 現場的四個角色

```text
        ┌──────────────────────────────────────────────────────────────┐
        │  螢幕（建議左右並排，不要疊視窗）                                │
        │  ┌───────────────────────┐   ┌──────────────────────────────┐│
        │  │  Qoder                │   │  Chrome（headed）             ││
        │  │  ─────────────────    │   │  finefoods-antd :3000        ││
        │  │  你：教我怎麼…         │   │                              ││
        │  │  Agent：好的，我先看…  │   │      ┌──────────┐            ││
        │  │  [mcp__showme__       │   │      │ ← 箭頭    │            ││
        │  │    start_tutorial]    │   │      │ Products  │            ││
        │  │  [mcp__showme__       │   │      └──────────┘            ││
        │  │    show_step] ← 卡住中 │   │   ┌────────────────────────┐ ││
        │  │                       │   │   │ Step 1/4               │ ││
        │  │                       │   │   │ Click Products         │ ││
        │  │                       │   │   │ [Next] [I'm stuck]     │ ││
        │  │                       │   │   └────────────────────────┘ ││
        │  └───────────────────────┘   └──────────────────────────────┘│
        └──────────────────────────────────────────────────────────────┘
                    ↑                                  ↑
              觀眾看這邊：                        觀眾也看這邊：
              agent 在「等」                     人自己動手，不是 agent 代點
```

### 2.3 一次完整 demo 的時序

```text
 人          Qoder Agent           ShowMe(Python)        Chrome + overlay(B)
 │                │                      │                      │
 │─「教我怎麼新增  │                      │                      │
 │   一個 product」│                      │                      │
 │                │──start_tutorial────> │                      │
 │                │  (url, goal)         │──launch headed Chrome───────────>│
 │                │                      │──add_init_script(overlay.js)───>│
 │                │                      │──expose_function(__showme_emit)>│
 │                │                      │──goto :3000 ────────────────────>│
 │                │                      │──snapshot(1)────────────────────>│
 │                │<──page: s1-1 Products, s1-2 Orders, ... ────│  寫 data-showme-uid
 │                │                      │                      │
 │                │ (心裡排 4 步大綱)     │                      │
 │                │──show_step(s1-1,     │                      │
 │                │   "Click Products",  │──show({uid,...})───────────────>│
 │                │   click, 1, 4)       │                      │  Driver.js 高亮
 │  看見箭頭 <────────────────────────────────────────────────── │  popover: Step 1/4
 │                │                (卡住)│                      │
 │─點 Products──────────────────────────────────────────────────>│
 │                │                      │<──__showme_emit({kind:"step_done"})
 │                │<──{event:"step_done",│  醒來                 │
 │                │    page: s2-*}       │──snapshot(2)────────────────────>│
 │                │                      │                      │
 │                │──show_step(s2-7, "Click Create", click, 2, 4)──────────>│
 │  ...重複 2–4 步（uid 每次從最新 page 重挑）...                  │
 │                │                      │                      │
 │                │──end_tutorial────────>│──clear()───────────────────────>│
 │                │                      │──done("✅ Done — you created a project")>│
 │  看見完成橫幅 <──────────────────────────────────────────────── │
 │                │<──{ok: true}         │  Session 刪除          │
```

---

## 3. 開始前先確認

- [ ] A01–A15 全部完成，`uv run pytest -q` 全套全綠、0 skipped。
- [ ] `uv run pytest -m browser -q` 全綠（A04／A05／A06／A15）。
- [ ] A14 的 Qoder MCP 設定已經接好，Qoder 裡看得到 `showme` 這個 server 與四個 tool。
- [ ] A14 的 allow list 已加 `mcp__showme__*`。
- [ ] A14 量過的 Request Timeout 數字手邊有（等下要填進 checklist）。
- [ ] `scripts/dev_open.py` 存在（A04 建立），可以用 `uv run python scripts/dev_open.py <url>` headed 開一個網頁。
- [ ] **B 已經把 `overlay/overlay.js` 寫完並 push**（不再是那 10 行的 stub）。用這行確認：

```bash
cd /Users/linjunting/hackathonQoder
wc -l overlay/overlay.js && head -5 overlay/overlay.js
```

  stub 只有 10 行、`snapshot` 回空陣列。如果還是 stub，先做 §7 Step 2（示範站）與 Step 4（劇本紙上演練），等 B 好了再回來做 Step 1。

- [ ] Node 已裝（示範站需要，A 的 Python 不需要）：`node -v` 應該是 v20 以上。

---

## 4. 名詞小抄

| 名詞 | 白話解釋 |
|---|---|
| 合流（merge / integration） | A 跟 B 各自寫的兩半第一次真的接在一起跑。接縫名字對不上就會靜靜地壞掉，所以要逐項對照。 |
| 接縫（seam） | 兩個人交界的那條線。ShowMe 的接縫就是 `window.__showme.*`（A 呼叫 B）與 `window.__showme_emit(...)`（B 呼叫 A），寫死在 `docs/handoff.md`。 |
| stub | 「假裝有這個東西」的空殼。`overlay/overlay.js` 一開始就是 stub：四個方法都在，但 `snapshot` 回空陣列、`show` 什麼都不做。 |
| Driver.js | B 用來畫高亮框與 popover 的第三方 JS 函式庫（MIT）。A 完全不碰它，但要知道它壞掉時的症狀。 |
| CSP（Content Security Policy） | 網站送給瀏覽器的一條規則：「只准從這些來源載入 script／樣式」。如果示範站設了嚴格 CSP，overlay 想從 CDN 載 Driver.js 就會被擋。 |
| finefoods-antd | 我們的示範產品頁：refine 官方的 Ant Design 外送平台後台 example。跑在 `:3000`。**它是外部 example，不進版控**。 |
| headed / headless | 有視窗 / 沒視窗。**demo 一定要 headed**——整個產品的價值就是人看得見箭頭。 |
| 彩排（dry run） | 用真的設備、真的流程走一次，但沒有觀眾。目的是把「只有現場才會出現」的問題先撞出來。 |
| `docs/plan/finish/` | 做完的計劃文件搬過去的地方。`unfinish/` 空了就代表 A 的計劃全部執行完。 |

---

## 5. 會動到的檔案

| 動作 | 路徑 | 這個檔負責什麼 |
|---|---|---|
| 執行（不改） | `overlay/overlay.js` | B 的產品 overlay。**A 一行都不改**，只是把它跑起來驗接縫 |
| 執行（不改） | `scripts/setup-sample-app.sh`、`docs/sample-app.md` | 建立示範站 |
| 執行（不改） | `scripts/dev_open.py` | headed 開一個網址確認 Chrome 能用 |
| 修改（本檔） | `docs/plan/unfinish/A16_與B合流與Demo演練.md` | 把 §7 Step 6 的 checklist 打勾、把實測數字填進去 |
| 搬移 | `docs/plan/unfinish/A00…A16` → `docs/plan/finish/` | §7 Step 8 |

**不會動到：** `showme/**`、`tests/**`（本篇不改任何程式碼；真的需要改代表前面某一篇的驗收沒過，回去補那一篇）。

---

## 6. 介面約定

本篇不新增介面，只**重述**要對照的那一組（來源 `docs/handoff.md`「鎖死的名字」，`docs/design/showme.md` §15.1「接縫」）：

```text
A 在頁面裡呼叫（Python 端是 browser.snapshot / show / clear / done）：

  window.__showme.snapshot(n)
      → { elements: [{ uid, role, name, testid }], truncated: bool }

  window.__showme.show({ uid, instruction, kind, index, total, expect })

  window.__showme.clear()

  window.__showme.done(text)


B 在頁面裡呼叫（每步恰好一次；A 用 context.expose_function 接）：

  window.__showme_emit({ kind: "step_done" | "stuck", url, ts })
```

不變條件（對照時逐條打勾）：

- `uid` 格式 `s{n}-{index}`；**n 由 A 決定並傳進 `snapshot(n)`**，B 只負責組字串。
- `elements[]` 每筆**四個鍵都在**：`uid`、`role`、`name`、`testid`（沒有就 `""`，不是 `null`、不是缺鍵）。
- `show.expect` = MCP 的 `expect_text`；`show.index` / `show.total` = `step_index` / `step_total`。
- **B 不發 `timeout`**。timeout 是 A 在 Python 用計時器決定的。
- **B 不發 `off_script`**（MVP Non-Goal）。
- 每步**恰好一次** emit。A 這邊會丟掉第二筆，但那是保險，不是讓 B 可以多發。
- overlay 走訪 DOM 時要把 `data-showme-uid` 寫到元素上，`show()` 才找得回那個節點。
- `clear()` 拆掉高亮與 listener，但**不拆 `window.__showme` 本身**。
- `done(text)` 顯示 A 傳進來的文字，B 不自己決定文案。

---

## 7. 步驟

### Step 1：與 B 合流檢查清單

B 的 `overlay/overlay.js` 進來之後，照這個順序做。

#### 1-1　先跑測試（3 分鐘）

```bash
cd /Users/linjunting/hackathonQoder
uv run pytest -m browser -q
```

其中 **`tests/test_browser_inject.py`（A05）用的就是 `overlay/overlay.js`**——也就是 B 的真檔案。它驗的正是 `docs/handoff.md` 說的「過了再分頭」兩個檢查點：

1. open 之後 `window.__showme` 是 object；**reload 之後仍在**（證明 `add_init_script` 生效）。
2. 頁面呼叫 `window.__showme_emit({kind:'step_done', url: location.href, ts: 1})`，**Python 的 handler 收得到那個 dict**。

預期輸出（測試數量依你前面寫了幾個而定）：

```text
........                                                            [100%]
8 passed in 6.71s
```

**2026-08-29 實測** ✅：

```text
......................                                              [100%]
22 passed, 147 deselected in 35.12s
```

全套 `uv run pytest -q` 也一起跑了：**169 passed in 29.88s**、0 skipped。
A05 用的是 B 的真 overlay，一樣綠 → 接縫的兩個檢查點（reload 後 `window.__showme` 還在、
頁面 emit Python 收得到）都成立，可以往下走 1-2。

`tests/test_browser_js.py`（A06）與 `tests/test_e2e_fake_overlay.py`（A15）用的是 `tests/fixtures/fake_overlay.js`，**不會**因為 B 的檔案改動而變色——這是刻意的：它們是 A 側的迴歸網，讓你在 B 的 overlay 壞掉時仍然知道「Python 這一半是好的」。

> 如果 A05 紅了、A06/A15 綠：問題在 B 的 overlay 或接縫，往下走 1-2。
> 如果 A05、A06、A15 都紅：問題在 A 這邊（或環境），回去看 A04/A05 的驗收。

#### 1-2　逐項對照鎖死的名字（10 分鐘）

開一個 headed 瀏覽器，親手在 console 敲一遍。先把示範站跑起來（Step 2），然後：

```bash
uv run python scripts/dev_open.py http://localhost:3000
```

視窗開起來之後（腳本會停 10 秒；不夠用就把它改成停久一點，或用下面的 REPL 版本）：

```bash
uv run python
```

```python
import asyncio
from showme.browser import PlaywrightBrowser

async def main():
    b = PlaywrightBrowser(headless=False)          # 預設 overlay_path 就是 overlay/overlay.js
    await b.launch()
    await b.open("http://localhost:3000")
    raw = await b.snapshot(1)
    print("truncated :", raw["truncated"])
    print("count     :", len(raw["elements"]))
    for el in raw["elements"][:5]:
        print(" ", el)
    print("keys      :", sorted(raw["elements"][0].keys()) if raw["elements"] else "(空)")
    input("看一下瀏覽器，然後按 Enter 繼續…")
    await b.show({"uid": raw["elements"][0]["uid"], "instruction": "Click this",
                  "kind": "click", "index": 1, "total": 4, "expect": ""})
    input("應該看到箭頭與 popover 了嗎？按 Enter 繼續…")
    await b.clear()
    await b.done("✅ Done — you created a project")
    input("箭頭消失、橫幅出現了嗎？按 Enter 結束…")
    await b.close()

asyncio.run(main())
```

對照表——每一項都要親眼確認：

| # | 要確認的 | 怎麼看 | 不對的話 |
|---|---|---|---|
| 1 | `snapshot(n)` 回的是 `{"elements": [...], "truncated": bool}` | 上面的 `raw["truncated"]` 印得出 `False`／`True` | B 的回傳鍵名錯了；對 `docs/handoff.md` |
| 2 | `elements[]` 每筆**四個鍵都在** | `keys : ['name', 'role', 'testid', 'uid']` | 缺 `testid` 是最常見的：規格明訂鍵永遠在、值可為 `""` |
| 3 | 沒有 `data-testid` 的元素，`testid` 是 `""` 不是 `None`／`undefined` | 找一個側邊選單連結看它的 `testid` | B 要寫 `el.dataset.testid \|\| ""` |
| 4 | 沒有 a11y name 的元素仍列出，`name` 是 `""` | 找 icon-only 的按鈕 | 規格明訂「沒有 name 的互動元素仍列出」 |
| 5 | `uid` 格式是 `s1-1`、`s1-2`…（因為我們傳 `n=1`） | 印出來的第一筆 | B 不可以自己決定 `n`；`snapshot(2)` 就要變 `s2-*` |
| 6 | 元素上真的寫了 `data-showme-uid` | 在 Chrome DevTools 的 Elements 面板搜尋 `data-showme-uid` | 沒寫的話 `show()` 找不回節點，箭頭會畫不出來 |
| 7 | 超過 150 個時只回前 150 且 `truncated` 是 `true` | finefoods-antd 的列表頁元素多，看 `count` 是不是 150 | 若 `count > 150`，B 的截斷沒做；A 這邊 `rules.build_page` 也會兜底截到 150，但 `truncated` 旗標會不準 |
| 8 | `show(opts)` 用的是 `uid / instruction / kind / index / total / expect` 六個鍵 | 上面 REPL 傳的就是這六個，箭頭有出來就對 | 鍵名對不上時 popover 會缺字（例如沒有 Step k/N） |
| 9 | popover 有：說明、`Step k / N`、`Next`、`I'm stuck` 四樣 | 肉眼看 | 少 `I'm stuck` 的話 `event: "stuck"` 這條路走不通 |
| 10 | 點 `Next` → emit 一次 `{kind:"step_done"}`；點 `I'm stuck` → emit 一次 `{kind:"stuck"}` | 用 Step 5 的完整彩排驗，或在 console 監看 | — |
| 11 | **每步只 emit 一次**：連點兩下 Next 不會送兩筆 | 彩排時故意連點 | A 這邊會丟掉第二筆（`_on_emit` 檢查 `pending.done()`），所以看起來沒事——但下一步就可能被上一步殘留的 listener 提早結束 |
| 12 | B **不發** `timeout`、**不發** `off_script` | `grep -n "timeout\|off_script" overlay/overlay.js` | 有的話請 B 拿掉；timeout 是 Python 的責任 |
| 13 | `clear()` 拆高亮與 listener，但 `window.__showme` 還在 | `clear()` 之後在 console 敲 `typeof window.__showme` 應該是 `"object"` | 拆掉的話下一次 `show()` 就爆 |
| 14 | `done(text)` 顯示的是**傳進去的字**，不是 B 寫死的字 | REPL 裡故意傳 `"XYZ"` 看是不是顯示 XYZ | 文案由 Python 決定（`DONE_BANNER_TEXT`） |

```bash
grep -n "timeout\|off_script\|__showme_emit" overlay/overlay.js
```

預期：只在「發 emit」的地方看到 `__showme_emit`，而且**看不到** `timeout` 或 `off_script` 被當成 emit 的 kind。

##### 2026-08-29 實測（真 overlay + finefoods-antd :3000）

驗證方式：scratchpad 的 async 腳本用 `PlaywrightBrowser()` 打 `http://localhost:3000`，
headless 與 headed 各跑一次（結果相同），`page.on("console", ...)` 全程收訊息。
第 12 項用 `grep`。**14 項全過（14/14 ✅），沒有一項要退回給 B。**

| # | 結果 | 證據 |
|---|---|---|
| 1 | ✅ | `snapshot(1)` 回的 keys = `['elements', 'truncated']`，`truncated=False` |
| 2 | ✅ | 67 筆元素，每筆 keys 都是 `['name', 'role', 'testid', 'uid']`，異常 0 筆 |
| 3 | ✅ | 67/67 筆 `testid == ""`（finefoods 整站沒用 `data-testid`），型別全是 `str`，沒有 `None`／缺鍵。例：`{'uid': 's1-1', 'role': 'link', 'name': '', 'testid': ''}` |
| 4 | ✅ | 有 8 筆 `name == ""` 仍被列出（側邊欄 logo 連結 `s1-1`、header 的 icon-only 按鈕 `s1-17` 等） |
| 5 | ✅ | `snapshot(1)` 前三筆 = `s1-1 / s1-2 / s1-3`；`snapshot(2)` 全部變 `s2-*`（前三筆 `s2-1 / s2-2 / s2-3`）。n 由 Python 傳、B 只組字串 |
| 6 | ✅ | `document.querySelectorAll("[data-showme-uid]").length` = 67，與 `elements` 筆數一致 |
| 7 | ✅ | finefoods 每頁都不到 150（`/` 67、`/products` 58、`/orders` 53、`/customers` 53），`truncated` 都是 `False`——與頁面白名單候選數完全相等。為了真的踩到上限，另外在頁面臨時注入 200 顆 `<button>` 再拍：**`count=150`、`truncated=True`、最後一筆 uid `s2-150`**（注入的 probe 節點事後移除，沒有動 `sample-app/`） |
| 8 | ✅ | `show({uid, instruction, kind, index, total, expect})` 六鍵傳進去，`.driver-popover` 出現，標題是 `Step 1 / 4` |
| 9 | ✅ | popover 的 `innerText` = `"Step 1 / 4\nClick Products in the sidebar\nNext\nI'm stuck"`——說明、`Step k / N`、`Next`、`I'm stuck` 四樣齊 |
| 10 | ✅ | 用 `set_emit_handler` 收：點 Next → 恰好一筆 `{'kind': 'step_done', 'url': ..., 'ts': ..., 'signal': 'next_button', 'uid': 's2-9'}`；點 I'm stuck → 恰好一筆 `{'kind': 'stuck', ..., 'signal': 'stuck_button', 'uid': 's3-5'}` |
| 11 | ✅ | 用 `evaluate` 對同一顆 Next 按鈕同步 `click()` 兩次 → **只收到 1 筆** emit（overlay 自己的 `current.emitted` guard 擋掉第二筆，不是靠 A 的 `pending.done()` 兜底） |
| 12 | ✅ | `grep -n "timeout\|off_script" overlay/overlay.js` **完全沒有輸出**（連字串都沒出現）。timeout 是 Python 的責任、`off_script` 是 Non-Goal，B 都沒碰 |
| 13 | ✅ | `clear()` 之後 `typeof window.__showme === "object"`，且 `.driver-popover` 確實消失 |
| 14 | ✅ | `done("XYZ-test")` 之後 `document.body.innerText` 含 `XYZ-test`——文案來自 Python，B 沒寫死 |

實測順帶發現的兩件事（不是接縫錯，是 demo 要知道的）：

1. **`start_tutorial` 剛回來時 `page.elements` 可能是 0 筆。** finefoods-antd 是 SPA，
   `page.goto` 的 load 事件比 React render 早。彩排時第一次 `start_tutorial` 回的就是
   `元素數 = 0`，等 2 秒再 `inspect_page` 就變成 44–67 筆。
   → demo 時 agent 的第一個動作最好是 `inspect_page` 再挑 uid（§9 排錯表本來就有這一列）。
   → **彩排後已修（2026-08-29）**：`showme/app.py` 的 `_take_snapshot` 拍到空清單會等 0.5 秒重拍、最多 3 次、
   snapshot# 不重複加（`SNAPSHOT_RETRIES` / `SNAPSHOT_RETRY_DELAY_S`），測試在 `tests/test_tool_start.py` 末尾兩條。
   所以現在 `start_tutorial` 通常直接就有元素；agent 先 `inspect_page` 仍然無害。
2. **finefoods-antd 整站沒有 `role == "textbox"`。** header 的搜尋框雖然是 `<input type="search">`，
   但 antd 的 AutoComplete 在上面掛了 `role="combobox"`，overlay 的 `roleOf()` 顯性 role 優先，
   所以它被歸成 combobox。`kind="input"` 的完成判定看的是元素本身的 `blur`／`change` + `value` 非空，
   跟 role 無關，所以**照樣可用**（彩排第 2 步就是拿它做的，成功回 `step_done`）。
   → demo 要示範 `kind="input"` 時，uid 從 `role == "combobox"` 且 name 含 `Search` 的那筆挑。

#### 1-3　Driver.js 被 CSP 擋的症狀（A 要認得，但修是 B 的事）

**A 這邊看到的症狀：** `show_step` 一切正常——它乖乖卡住等待、沒有丟例外、`error` 是 `""`——**但是畫面上什麼都沒有**。人不知道要點哪裡，於是一路等到 timeout。

**怎麼確認是不是 CSP：** 在 Chrome 按 `Cmd+Option+J` 打開 console，找這種紅字：

```text
Refused to load the script 'https://cdn.jsdelivr.net/npm/driver.js@…' because it
violates the following Content Security Policy directive: "script-src 'self' …".
```

**為什麼會這樣：** `add_init_script` 是 Playwright 直接注入到 execution context 的，**不受**網站 CSP 對外部 script 的限制——所以 `window.__showme` 一定進得去。但如果 overlay 在執行期又去 `document.createElement('script')` 從 CDN 拉 Driver.js，那一次載入就是網站自己的請求，會被 CSP 擋下。設計 §12 已經寫了處理方式：**改成本地 vendor 檔**（把 Driver.js 的單檔放進 `overlay/`，跟 overlay.js 一起注入）。

**A 要做的事：** 只有「認出症狀、告訴 B」。不要自己去改 `overlay/**`。

##### 2026-08-29 實測：**沒有 CSP 問題** ✅

三次跑（seam 腳本 headless／headed、完整彩排 headed）都用 `page.on("console", ...)` 全程收訊息，
**沒有任何一則含 `Refused to load` 或 `Content Security Policy`**。原因很明確：
`overlay/overlay.js` 是 `overlay/build.sh` 把 `overlay.src.js` + `vendor/driver.iife.js` +
`vendor/driver.css`（內嵌成 `__SHOWME_DRIVER_CSS__` 字串）串成的**單一 517 行 bundle**，
執行期完全不去 CDN 拉東西——也就是設計 §12 說的「改成本地 vendor 檔」那條路，B 一開始就走了。

console 裡確實有紅字，但**全部是示範站自己的**，跟 ShowMe 無關，不用理：

```text
Warning: [antd: Menu] `children` is deprecated. Please use `items` instead.
Warning: [antd: Dropdown] `overlay` is deprecated. Please use `menu` instead.
Google Maps JavaScript API error: BillingNotEnabledMapError
Warning: Instance created by `useForm` is not connected to any Form element.
Maximum update depth exceeded.（在搜尋框打字後 refine 自己刷出來的）
```

#### 1-4　合流完成的判準

- [x] `uv run pytest -q` 全套全綠（包含用 B 的 overlay 的 A05）。→ 2026-08-29 實測 **169 passed in 29.88s**、0 skipped；`uv run pytest -m browser -q` 為 **22 passed, 147 deselected in 35.12s**。
- [x] 1-2 的 14 項全部確認過。→ **14/14 ✅**（表在上面）。
- [x] 在示範站上手動跑一次 REPL，箭頭出得來、popover 四樣齊、clear 與 done 都對。→ 改用 scratchpad 腳本跑（headless + headed 各一次），箭頭、`Step 1 / 4`、`Next`、`I'm stuck`、`clear()`、`done("XYZ-test")` 全部正確。

---

### Step 2：把示範站跑起來

完整說明在 `docs/sample-app.md`，這裡只寫「要打哪幾行、看到什麼算成功」。

```bash
cd /Users/linjunting/hackathonQoder
./scripts/setup-sample-app.sh
```

腳本會做 scaffold（`npm create refine-app@latest -- --example finefoods-antd`）、修 `package.json` 裡鎖死的 peer dependency、`npm install --legacy-peer-deps`。第一次跑要好幾分鐘。成功時最後會印：

```text
==> 完成。啟動方式：

    cd sample-app/finefoods-antd
    npm run dev

然後打開 http://localhost:3000
```

`npm run dev` 是長駐的 server，腳本刻意不幫你跑。**另開一個終端機分頁**：

```bash
cd /Users/linjunting/hackathonQoder/sample-app/finefoods-antd
npm run dev
```

看到 vite 印出網址就對了。**如果它說 3000 被佔用而改用別的 port，記下那個 port**——後面所有 url 都要跟著換。

`docs/sample-app.md` 的「疑難排解」有 peer dependency、資料夾名稱、port 被佔用三種情況的處理，遇到就去看，這裡不重抄。

---

### Step 3：用 headed 確認 Chrome 開得了示範站

在 Qoder 接上去之前，先用 A04 建的小腳本確認「Playwright 真的能開 headed Chrome 並載入示範站」。這一步失敗的話，後面全部都不用試。

```bash
cd /Users/linjunting/hackathonQoder
uv run python scripts/dev_open.py http://localhost:3000
```

預期：**一個 Chrome 視窗彈出來**，顯示 finefoods-antd 的畫面（左邊側邊欄有 Dashboard / Orders / Products / Customers 之類的項目），停 10 秒後自己關掉，終端機沒有 traceback。

三個常見結果：

| 看到什麼 | 意思 | 怎麼辦 |
|---|---|---|
| 視窗彈出、頁面正常 | ✅ 過了 | 往下走 |
| 視窗彈出但頁面空白／`ERR_CONNECTION_REFUSED` | 示範站沒在跑，或 port 不對 | 回 Step 2 確認 `npm run dev` 還活著、port 對不對 |
| 沒有視窗，終端機丟 `Executable doesn't exist` | Chromium 沒裝、Chrome channel 也找不到 | `uv run playwright install chromium` |

#### 2026-08-29 實測（Step 2 + Step 3）

示範站已經在跑（不重跑 `setup-sample-app.sh`、不重 `npm install`）：

```text
$ curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
200

$ uv run python scripts/dev_open.py http://localhost:3000
opened : http://localhost:3000/
title  : Finefoods Ant Design Admin Panel - refine
視窗會停留 10 秒，請用眼睛確認畫面。
（exit code 0，沒有 traceback）
```

✅ headed Chrome 彈得出來、載得到示範站、`channel="chrome"` 走的是本機 Google Chrome。

---

### Step 4：手動 demo 劇本

#### 4-1　開場那一句話

在 Qoder 的對話框輸入（**只輸入這一句，不要幫 agent 想步驟**）：

```text
用 ShowMe 教我怎麼在 http://localhost:3000 新增一個 product。
不要幫我操作，我要自己點。
```

第二句是給觀眾聽的，也是給 agent 的保險（`instructions` 裡已經寫了「you never act for them」，但講出來 demo 效果更好）。

#### 4-2　四個 tool 的呼叫順序與每一步的預期畫面

| # | Agent 呼叫 | Qoder 畫面上會看到 | Chrome 畫面上會看到 | 這一步的重點 |
|---|---|---|---|---|
| 1 | `mcp__showme__start_tutorial(url="http://localhost:3000", goal="create a product")` | 一個 tool call，馬上回來（1–3 秒）。回傳裡有 `session_id`（形如 `s_8f2a`）、`page.elements`（一串 `s1-*`）、`next_action` | **Chrome 視窗彈出來**，載入 finefoods-antd | 快、而且**元素清單是文字不是截圖**——這是 ShowMe 的核心：agent 靠 uid 指人，不靠視覺 |
| 2 | `mcp__showme__show_step(session_id=…, uid="s1-N", instruction="Click Products", kind="click", step_index=1, step_total=4)` | tool call **卡住不回來** | 側邊欄的 Products 被高亮，旁邊 popover 寫著說明、`Step 1 / 4`、`Next`、`I'm stuck` | **這就是整個 demo 的關鍵畫面**：agent 在等人。停在這裡多講兩句 |
| 3 | （人自己點 Products） | 幾秒後 tool call 回來：`event: "step_done"`、`elapsed_s`、一份新的 `page`（uid 變 `s2-*`） | 頁面換到商品列表，箭頭消失 | 完成判定在 overlay（URL 變了），不是 agent 猜的、也不是等 HTTP |
| 4 | `mcp__showme__show_step(session_id=…, uid="s2-M", instruction="Click Create", kind="click", step_index=2, step_total=4)` | 又卡住 | Create 按鈕被高亮，popover 寫 `Step 2 / 4` | **uid 是從第 3 步回來的那份 page 重挑的**，不是一開始就排好的 |
| 5 | （人自己點 Create） | 回 `step_done` + `s3-*` 的新 page | 出現新增商品的表單／抽屜 | — |
| 6 | `mcp__showme__show_step(uid="s3-K", instruction="Type a product name", kind="input", step_index=3, step_total=4)` | 卡住 | 名稱欄位被高亮 | `kind="input"`：完成條件是「有字 + blur/change」或按 Next |
| 7 | （人自己打字然後點別的地方） | 回 `step_done` + `s4-*` | — | — |
| 8 | `mcp__showme__show_step(uid="s4-J", instruction="Click Save", kind="click", step_index=4, step_total=4)` | 卡住 | Save 按鈕被高亮 | — |
| 9 | （人自己點 Save） | 回 `step_done` + `s5-*` | 商品建立成功 | — |
| 10 | `mcp__showme__end_tutorial(session_id=…, summary="create a product")` | 回 `{"ok": true, "error": ""}` | 箭頭全部消失，出現橫幅 **`✅ Done — you created a project`** | 收攤 |

> **關於 banner 文案：** 規格（`.clarify/resolved/features/結束教學_完成banner文案與summary參數的關係為何.md`，答案 B）明訂 banner 是**固定字串** `✅ Done — you created a project`，**忽略 summary**。所以就算這次 demo 教的是「新增 product」，橫幅仍然寫 project。這是規格的既定結果，**不要為了 demo 好看去改**——要改是改規格，不是改實作。真的在意的話，demo 的 goal 就直接用 `create a project`，或在講稿裡一句話帶過：「這個橫幅的文案目前是規格寫死的常數」。

> **關於按鈕的實際文字：** 上表的 `Products` / `Create` / `Save` 是示意。ShowMe 的設計就是**不預先知道畫面長怎樣**——agent 每一步都從最新的 `page.elements` 現挑 uid、用畫面上看得到的字寫 instruction。所以你不需要事先背下 finefoods-antd 的 UI，Step 5 彩排時看實際回傳的清單就好。

#### 4-3　講稿的三個停頓點

1. **第 2 步 tool 卡住時**：「注意看，這個 tool call 現在沒有回來。它在等我。這不是超時、不是壞掉——ShowMe 的 `show_step` 是阻塞的，人做完它才回。」
2. **第 3 步回來、uid 從 `s1-*` 變 `s2-*` 時**：「畫面換了，所以元素清單重拍了一份，uid 世代加一。agent 不能拿舊清單的 uid，那會被擋成 `uid_not_in_snapshot`。」
3. **第 10 步 banner 出現時**：「Session 到這裡就被刪掉了。再呼叫任何 tool 都是 `session_not_found`。」

#### 4-4　萬一卡住的救場動作

| 現場狀況 | 救場 | 別做什麼 |
|---|---|---|
| 人點了但箭頭沒消、tool 沒回來 | 按 popover 上的 **Next**（任何 kind 按 Next 都算 `step_done`） | 不要去 Qoder 裡按取消 |
| 人根本看不懂要點哪 | 按 **I'm stuck**，agent 會用同一個元素、更白話的說明再畫一次 | 不要自己幫他點 |
| 箭頭指錯地方 | 讓 agent 呼叫 `inspect_page` 重拍，再挑一次 | 不要手動改 uid |
| 整個 tool 逾時了 | 沒關係，`event: "timeout"` 也會回一份新 page，agent 可以接著走 | 不要重開 Qoder |

---

### Step 5：完整彩排一次

把 Step 2 → Step 3 → Step 4 從頭到尾**不看筆記**跑一遍，計時。

彩排時要做到的：

- [ ] 從「打開終端機」到「Chrome 出現 finefoods-antd」不超過 2 分鐘（示範站已經 `npm run dev` 在背景跑的前提下）。
- [ ] 四個 tool 都真的被呼叫到，順序是 `start_tutorial` → `show_step` ×N → `end_tutorial`。
- [ ] 至少有一步是 `kind="input"`（證明不是只會 click）。
- [ ] 故意按一次 **I'm stuck**，看 `event: "stuck"` 回來、agent 用同一個元素重畫（`steps_shown` 會 +1）。
- [ ] 故意讓一步 **timeout**（用 `timeout_s=10` 然後什麼都不做），確認箭頭被清掉、`event: "timeout"`、`error` 是 `""`，而且 agent 還能接著走。
- [ ] 最後 banner 真的出現。
- [ ] 再讓 agent 呼叫一次 `end_tutorial`，看到 `session_not_found`。
- [ ] 全程 **agent 沒有替人點過任何東西**。

彩排時把實際看到的東西記下來（下一步要用）：

```text
示範站實際 port           : 3000
start_tutorial 回的元素數  : 0（剛回來時）→ 等 2 秒 inspect_page 後 67   truncated: false
Products 那一項的 uid      : s2-9（第二份 snapshot 的第 9 筆；每場次都要現挑，別背這個數字）
一次 show_step 從呼叫到畫出箭頭的秒數 : 0.02–0.04 秒
Qoder Request Timeout 實測 : 預設 ____ 秒 / 已調高到 ____ 秒   ← 待使用者在 Qoder IDE 量測
demo 時要用的 timeout_s    : ____   ← 待使用者決定（要小於上面那個數字）
```

#### 2026-08-29 程式化彩排實測

彩排方式：不經過 Qoder，直接用 `ShowMeApp()`（**預設 factory**，也就是產品路徑：
真 overlay + `channel="chrome"` 的 **headed** Chrome）在 scratchpad 腳本裡依序呼叫四個 tool，
`show_step` 放進 `asyncio.create_task` 讓它真的阻塞，然後用 `page.click` / `page.fill`
模擬「人」的動作。走的就是 Qoder 會走的那條路，只是把「人」換成腳本。

> ⚠ **全程沒有按任何 Save／Create／Submit／Delete。** finefoods-antd 的資料後端是外部公開 API，
> 彩排只做：側邊欄導航、搜尋框打字後 blur、按 popover 的 Next／I'm stuck、什麼都不做等 timeout。
> 所以 §7 Step 4-2 劇本裡的第 8–9 步（Click Save）**沒有**在彩排裡跑，demo 現場也建議跳過或換成 Cancel。

| # | 動作 | 回傳 event | `elapsed_s` | 其他數字 |
|---|---|---|---|---|
| 1 | `start_tutorial("http://localhost:3000", "create a product")` | — | 呼叫到回來 **1.9 秒**（另一次 3.2 秒） | `session_id='s_17d4'`、`error=''`、`page.elements` **0 筆**、`truncated=false` |
| 1b | 等 2 秒 → `inspect_page` | — | — | **67 筆**、`truncated=false`、uid 世代 `s2-*`；Products = `s2-9` |
| 2 | `show_step(s2-9, "Click Products in the sidebar", "click", 1, 4, timeout_s=30)` | （卡住） | — | 呼叫 → `.driver-popover` 出現 **0.02 秒**；popover 文字 `"Step 1 / 4\nClick Products in the sidebar\nNext\nI'm stuck"`；`task.done() == False` |
| 3 | `page.click('[data-showme-uid="s2-9"]')`（模擬人） | **`step_done`** | 0.1 | `error=''`、新 page **67 筆**、uid 變 `s3-*`、`url=http://localhost:3000/products` |
| 4 | `show_step(s4-18, "Type something in the search box", **"input"**, 2, 4, timeout_s=30)` | （卡住） | — | 畫出箭頭 0.02 秒。⚠ 這個 uid 的 `role` 是 `combobox` 不是 `textbox`（見 §7 1-2 實測發現 2），`tagName === "INPUT"` |
| 5 | `page.fill(...)` 打 `chicken` 再 `blur()` | **`step_done`** | 0.0 | `error=''`。**沒有送出表單** |
| 6 | `show_step(s6-5 Orders, "click", 3, 4, timeout_s=30)` → 按 **I'm stuck** | **`stuck`** | 0.1 | `steps_shown` 2 → **3** |
| 7 | 同一個元素、從新 page 重挑 uid（`s7-5`）再 `show_step` | （卡住後按 Next → `step_done`） | — | `steps_shown` 3 → **4**（證實「stuck 後重畫也算一步」） |
| 8 | `show_step(Customers, "click", 4, 4, timeout_s=5)`，**什麼都不做** | **`timeout`** | **5.0** | `error=''`（timeout 是 event 不是 error）、`.driver-popover` 已消失（A-3 的 `clear()` 有跑） |
| 9 | `end_tutorial(session_id, "create a product")` | — | — | `ok=True`、`error=''`、`document.body.innerText` 含 **`✅ Done — you created a project`** |
| 10 | 再 `end_tutorial(同一個 session_id)` | — | — | `ok=False`、`error='session_not_found'` |
| 11 | `await app.shutdown()` | — | — | 正常關閉，沒有 traceback |

彩排結論：**四個 tool 全部走過、含一次 input、一次 stuck、一次 timeout，全程 Python 沒有替人按任何送出類按鈕。**

彩排時的 checklist 對照：

- [x] 四個 tool 都真的被呼叫到，順序是 `start_tutorial` → `show_step` ×5 → `end_tutorial`。
- [x] 至少有一步是 `kind="input"`（第 4–5 步）。
- [x] 故意按一次 **I'm stuck**，`event: "stuck"` 回來、同元素重畫時 `steps_shown` +1。
- [x] 故意讓一步 timeout（用 `timeout_s=5`），`event: "timeout"`、`error` 是 `""`、箭頭被清掉、後面還能接著走。
- [x] 最後 banner 真的出現。
- [x] 再 `end_tutorial` 得到 `session_not_found`。
- [x] 全程沒有替人點過任何東西（`page.click` 是「扮演人」，不是 agent 代點；agent 側只呼叫四個 tool）。
- [ ] 從「打開終端機」到「Chrome 出現 finefoods-antd」不超過 2 分鐘 → **待使用者**（程式化彩排量不到「人開終端機」這段；`start_tutorial` 本身是 1.9–3.2 秒）。

---

### Step 6：Demo 前一天 checklist

前一天做完，當天只需要「開機、啟動、講」。

> 2026-08-29 已由 agent 驗過的項目直接打勾並附數字；**需要 Qoder IDE 或現場環境的一律標「待使用者」，沒有打勾。**

**環境**

- [x] `uv run pytest -q` 全套全綠、0 skipped。→ **169 passed in 29.88s**
- [x] `git status` 乾淨（沒有沒 commit 的改動）。→ `showme/`、`tests/`、`overlay/` 一行都沒動；工作區只剩使用者自己既有的未追蹤／已修改檔（`CLAUDE.md`、`docs/plan/dev-prompts/phase0829*.md`、`docs/sample-app.md`、`scripts/setup-sample-app.sh`、A16 的 TODO），加上本篇要 commit 的 A16 文件與 REP。
- [x] `sample-app/finefoods-antd/` 已經 `npm install` 好（當天不要現場裝）。→ 本次全程沒重跑 `setup-sample-app.sh`、沒 `npm install`
- [x] `npm run dev` 起得來，`http://localhost:3000` 打得開。→ `curl` 回 **200**，title `Finefoods Ant Design Admin Panel - refine`
- [x] `uv run python scripts/dev_open.py http://localhost:3000` 能彈出 headed Chrome。→ exit 0、視窗有出來
- [x] `uv run showme` 能啟動（`Ctrl-C` 結束）。→ `uv run showme < /dev/null` 乾淨啟動並在 stdin EOF 時 **exit 0**

**Qoder**（全部**待使用者**，agent 碰不到 IDE）

- [ ] MCP 設定裡 `showme` 在、四個 tool 列得出來。　**待使用者**
- [ ] allow list 有 `mcp__showme__*`，實測不會每次跳確認。　**待使用者**
- [ ] Request Timeout 已調高：實測 ______ 秒。　**待使用者**
- [ ] demo 用的 `timeout_s` 決定好：______ 秒（要小於上面那個數字）。　**待使用者**

**Overlay（B 的部分，A 只確認）**

- [x] `overlay/overlay.js` 不是 stub。→ **517 行 / 46 KB**，開頭寫著 `GENERATED FILE — 由 overlay/build.sh 產生`，Driver.js 與 driver.css 都已 vendor 進 bundle
- [x] `uv run pytest -m browser -q` 全綠。→ **22 passed, 147 deselected in 35.12s**
- [x] Step 1-2 的 14 項都確認過。→ **14/14 ✅**
- [x] Driver.js 沒有被 CSP 擋（console 沒紅字）。→ 三次跑都 **0 則** `Refused to load`／CSP 訊息（bundle 不走 CDN）

**現場**（全部**待使用者**）

- [ ] 螢幕解析度／縮放調好，Qoder 與 Chrome 左右並排都看得清楚。　**待使用者**
- [ ] Chrome 沒有登入其他帳號、沒有一堆分頁、沒有擋畫面的擴充功能。　**待使用者**
- [ ] 通知全關（Chrome、系統、Slack）。　**待使用者**
- [ ] 螢幕不會自動休眠。　**待使用者**
- [ ] 網路：示範站是 localhost，**不需要網路**；但 Qoder 的模型需要，確認連得上。　**待使用者**
- [ ] 電源接著。　**待使用者**

**備案**（**待使用者**）

- [ ] 彩排的錄影或截圖存好（現場真的爆掉就放這個）。　**待使用者**
- [ ] 知道 §9 故障排除表在哪一頁。　**待使用者**

---

### Step 7：A 側設計決定總表

這張表要在 demo 的 Q&A 講得出來：**哪些是規格說的、哪些是 A 先決定的**。

規格已定案、**不可改**的（`.clarify/resolved/` + `erm.dbml` + `.feature`）：六個錯誤碼、`max_steps=12`、預設 `timeout_s=120`、`elapsed_s >= timeout_s` 算 timeout、同 ts 後至丟棄、`steps_shown` 在畫出時 +1（含 stuck 重畫）、banner 固定文案且忽略 summary、`end_tutorial` 後刪除 Session、150 硬上限、`testid` 鍵永遠在、非法 kind 視為 observe、不檢查 host。

下面這七項是**A 的設計決定（可改）**——規格沒寫死，A 先選一個實作，不是規格：

| # | 問題 | A 的決定 | 為什麼這樣選 | 改的話會影響 |
|---|---|---|---|---|
| **OQ1** | SHOWING 時 `inspect_page` / `end_tutorial` 該回哪個 `error`？（設計 §17 open Q1；已定案的六個碼裡沒有 `not_ready`） | 回 `show_step_in_progress` | 不新增第七個錯誤碼；語意也接近（「正在畫，等它」） | `tests/test_tool_inspect.py`、`tests/test_tool_end.py`；agent 的 instructions 不用改 |
| **OQ2** | SHOWING 時 `start_tutorial` 覆蓋，卡住的那次 `show_step` 怎麼收尾？（設計 §17 open Q2） | `start_tutorial` 把 pending future 以 `{"kind": "cancelled"}` 解掉；那次 `show_step` 回 `event="timeout"`、`page=None`、`error=""`，**不**再碰瀏覽器／Session | 已經有 `timeout` 這個 event，不必新增 error；而且不會兩邊搶著改 Session | `showme/app.py` 的 `start_tutorial` 與 `show_step`；`tests/test_tool_start.py` 的 OQ2 測試 |
| **A-1** | `start_tutorial` 導航失敗時 Session 怎麼辦？ | **不建立／刪除** Session（只有成功的 start 才有 Session）；回 `session_id=""`、`error="navigation_failed"` | 避免留下一個「有 id 但沒有頁面」的半殘場次 | `tests/test_tool_start.py` |
| **A-2** | `end_tutorial` 之後關不關瀏覽器？ | **不關**。瀏覽器在 process 結束（`shutdown()`）時才關；下次 `start_tutorial` 重用同一個瀏覽器，若已被人手動關掉則重新 launch | 人要看到完成 banner；關掉等於把成果收走 | `showme/app.py` 的 `end_tutorial`；`tests/test_tool_end.py` |
| **A-3** | timeout 之後要不要清 overlay？ | 要：Python 呼叫 `browser.clear()`。`step_done` / `stuck` 之後**不**清（overlay 自己處理；下一次 `show()` 本來就會先 clear） | 設計 §11 明寫 timeout 後「`clear()` 觀察器、拍 page、state=READY」 | `showme/app.py` 的 `show_step`；`tests/test_tool_show_step_wait.py` |
| **A-4** | `elapsed_s` 的精度？ | `round(elapsed, 1)` | 對齊規格 Example 的 `4.2` | `showme/app.py` 的 `show_step` |
| **A-5** | `expose_function` 掛在 page 還是 context？ | `context.expose_function`（跨 page／導航都在） | 教學過程一定會換頁，掛在 page 上會掉 | `showme/browser.py` 的 `launch()` |

另外一項是 **B 的**設計決定，A 只要知道：設計 §17 open Q3「什麼算隱藏」——B 採用 §11 的最小集合（不在 document、`display:none`、`visibility:hidden`、`aria-hidden="true"`），不做 IntersectionObserver。若 demo 的元素用 `opacity:0` 消失，overlay 可能漏判，人按 Next 就好。

---

### Step 8：把 A00–A16 搬到 `docs/plan/finish/`

慣例：**一篇做完就搬一篇**，這樣 `docs/plan/unfinish/` 裡剩下的就是還沒做的。

```bash
cd /Users/linjunting/hackathonQoder
git mv docs/plan/unfinish/A16_與B合流與Demo演練.md docs/plan/finish/
git commit -m "docs: A16 done — merged with B and rehearsed the demo"
```

（前面每一篇也是同樣兩行，把檔名換掉就好。）

A16 是最後一篇，所以搬完之後 `unfinish/` 應該是空的：

```bash
ls docs/plan/unfinish/
ls docs/plan/finish/
```

預期：

```text
（unfinish 沒有輸出）

A00_導讀與總覽.md
A01_環境建置與骨架確認.md
A02_Session資料模型.md
A03_純函數規則.md
A04_瀏覽器層_開啟頁面.md
A05_注入overlay與emit橋.md
A06_瀏覽器層_JS呼叫與假overlay.md
A07_FakeBrowser與App骨架.md
A08_start_tutorial.md
A09_start_tutorial覆蓋場次.md
A10_inspect_page.md
A11_show_step前置檢查.md
A12_show_step阻塞等待.md
A13_end_tutorial.md
A14_MCP契約測試與stdio.md
A15_真瀏覽器端到端.md
A16_與B合流與Demo演練.md
```

如果你是一次做完全部才搬，一行就好：

```bash
git mv docs/plan/unfinish/A*.md docs/plan/finish/ && git commit -m "docs: move the finished A plan into docs/plan/finish"
```

搬完之後回 `docs/plan/finish/A00_導讀與總覽.md`，照它最後那份總驗收清單再對一次。

---

## 8. 驗收清單

**合流**

- [x] `overlay/overlay.js` 是 B 的真檔案（不是 10 行 stub）。→ 517 行 bundle
- [x] `uv run pytest -q` 全套全綠、0 skipped，其中 A05 的 `test_browser_inject.py` 用的是 B 的 overlay。→ **169 passed**
- [x] §7 Step 1-2 的 14 項接縫全部親眼確認過。→ **14/14 ✅**（headless + headed 各跑一次）
- [x] Driver.js 沒被 CSP 擋（Chrome console 沒有 `Refused to load the script` 紅字）；有的話已告知 B。→ **0 則**，不需要告知 B

**示範站**

- [x] `sample-app/finefoods-antd/` 建好、`npm run dev` 跑得起來。→ `curl` 回 200（本次沒重裝、沒重跑腳本）
- [x] `uv run python scripts/dev_open.py http://localhost:3000` 能彈出 headed Chrome 並看到示範站。→ exit 0

**Demo**

- [x] 彩排完整跑過一次：`start_tutorial` → `show_step` ×N（含一次 input、一次 stuck、一次 timeout）→ `end_tutorial` → 再 `end_tutorial` 得 `session_not_found`。→ 程式化彩排（`ShowMeApp()` 預設 factory、headed Chrome）跑完 11 步，見 §7 Step 5 實測表
- [x] 全程 agent 沒有替人操作。→ Python 只呼叫四個 tool；`page.click` / `page.fill` 是腳本「扮演人」，且沒碰任何送出類按鈕
- [x] 完成 banner 真的出現，文字是 `✅ Done — you created a project`。
- [x] §7 Step 5 的六個實測數字都填了。→ 四個填實測值；**Qoder Request Timeout 與 demo 用的 `timeout_s` 兩格待使用者在 Qoder IDE 量測**
- [ ] §7 Step 6 的 checklist 全部打勾。→ 環境與 Overlay 兩段**全勾**；**Qoder／現場／備案三段待使用者**

**收尾**

- [ ] §7 Step 7 的七項 A 側設計決定，你講得出「這是我們決定的，不是規格」。　**待使用者**（表本身不用改）
- [ ] A00–A16 都搬到 `docs/plan/finish/`，`docs/plan/unfinish/` 是空的。→ Step 8 由主控執行
- [x] `showme/**`、`tests/**`、`overlay/**` 在本篇一行都沒改。→ `git status` 確認三個目錄乾淨

---

## 9. 常見問題與排錯

| 症狀 | 可能原因 | 怎麼處理 |
|---|---|---|
| **Chrome 沒開**：`start_tutorial` 丟 `Executable doesn't exist at …` | Chromium 沒裝，而且 `channel="chrome"` 也失敗 | `uv run playwright install chromium`。macOS 上 `/Applications/Google Chrome.app` 在的話 `channel="chrome"` 會先成功，這時不需要另外裝 |
| **Chrome 沒開**：完全沒視窗，也沒錯誤 | 用了 `headless=True` | demo 一律 headed。`PlaywrightBrowser` 的預設就是 `headless=False`；檢查有沒有人在哪裡傳了 `headless=True` |
| **Chrome 開了但是在別的桌面／被擋住** | macOS 的多桌面 | demo 前先把 Chrome 拉到主桌面，或關掉「自動重新排列 Spaces」 |
| `error: "navigation_failed"` | 示範站沒在跑、port 不對、url 打錯 | 瀏覽器直接輸入那個 url 試試。注意 `npm run dev` 被佔 port 時會自己換號 |
| `error: "navigation_failed"` 但瀏覽器打得開 | url 少了 scheme（寫成 `localhost:3000` 而不是 `http://localhost:3000`） | 補上 `http://` |
| **一直 `uid_not_in_snapshot`** | agent 拿舊 snapshot 的 uid。每次 `show_step` 回來都附一份**新**的 page（uid 世代 +1），舊的就作廢了 | 這是**設計就會這樣**。`show_step` 失敗時本來就會附一份新鮮 page，讓 agent 直接從那份重挑。連續發生的話檢查 `instructions` 有沒有被改掉（裡面明寫 "Never reuse a uid from an older snapshot"） |
| 一直 `uid_not_in_snapshot`，而且回傳的 page 幾乎沒有元素 | 頁面還在載入（SPA 還沒 render 完）就拍了 snapshot | 讓 agent 先 `inspect_page` 再挑；或 demo 前先手動把示範站點過一輪讓它 warm 起來 |
| **IDE Request Timeout**：`show_step` 還沒到 `timeout_s` 就被 IDE 中斷 | IDE 等待上限比 `timeout_s` 短 | 照 A14 Step 7 調高 Request Timeout；調不了就每一步都明確傳一個比它小的 `timeout_s`。**不要**為此加第五個 tool 或做 `wait_for_user`（設計 §16 明寫） |
| `error: "show_step_in_progress"` | 上一個 `show_step` 還卡著（人還沒做完），agent 就送了第二個 | 讓人把上一步做完，或按 Next／I'm stuck。agent 的 `instructions` 已寫 "One show_step at a time"；一直發生代表 agent 沒遵守，在對話裡提醒它一句 |
| `error: "show_step_in_progress"` 但畫面上沒有箭頭 | 上一次 `show_step` 因為 IDE 中斷而「client 端放棄了、server 端還在等」 | 這是最麻煩的一種。等它自己 timeout（最多 `timeout_s` 秒）就會回 READY；或呼叫一次 `start_tutorial` 覆蓋（OQ2 的路徑，會把卡住的那次以 `event="timeout"` 收掉） |
| `error: "max_steps_exceeded"` | `steps_shown` 已經到 12。注意 **stuck 後重畫也算一步** | 呼叫 `start_tutorial` 重開一場（同 `session_id`、`steps_shown` 歸零）。demo 的流程要控制在 4–6 步，不要規劃 10 步以上 |
| **誤用 headless**：測試都綠、demo 卻看不到東西 | 有人把 demo 也跑成 headless | 只有 `tests/` 裡才會傳 `headless=True`；產品路徑（`get_app()` → `ShowMeApp()` → `PlaywrightBrowser()`）用預設的 `headless=False` |
| 箭頭沒出來但 `show_step` 正常卡住 | Driver.js 被 CSP 擋，或元素上沒有 `data-showme-uid` | 看 §7 Step 1-3；這是 B 的修 |
| 箭頭指到看不見的地方（頁面沒捲過去） | overlay 的 `scrollIntoView` 沒做 | B 的事（設計 §12 明列 `show` 要 `scrollIntoView`） |
| 人點了 Next 兩次，下一步立刻就結束了 | overlay 的 listener 沒在 `clear()` 時拆乾淨，殘留到下一步 | B 的事（接縫第 11 項）；A 這邊的 `pending.done()` 只擋得住同一步的第二筆 |
| banner 寫的是 project，但我們教的是 product | **規格如此**：banner 是固定字串、忽略 summary | 不要改實作。要嘛 demo 的 goal 就用 `create a project`，要嘛在講稿裡說明這是規格寫死的常數 |
| `end_tutorial` 之後 Chrome 就關掉了，觀眾沒看到 banner | 有人加了 `browser.close()` | 拿掉。A-2 的設計決定就是不關 |
| demo 中途想重來 | 直接再呼叫一次 `start_tutorial`（同 url、同 goal） | 它會覆蓋：同 `session_id`、`steps_shown` 歸零、snapshot# 回到 1、state=READY。**不需要**重開 Qoder 或重開 server |
| Qoder 每個 tool 都跳確認視窗 | allow list 沒設好 | 加 `mcp__showme__*`；`show_step` 卡住時跳確認視窗會讓現場很混亂 |
| server 起不來：`command not found: uv` | IDE 的 PATH 跟終端機不一樣 | `which uv` 拿完整路徑填進 MCP 設定的 `"command"` |

---

## 10. 對照規格

| 規格來源 | 條目 | 本篇怎麼滿足 |
|---|---|---|
| `docs/handoff.md`「鎖死的名字」 | `__showme.snapshot(n) → {elements, truncated}`、`show({uid, instruction, kind, index, total, expect})`、`clear()`、`done(text)`、`__showme_emit({kind, url, ts})`；B 不發 timeout；`elements[]` 四鍵必在；uid 由 A 給 n、B 組字串 | §6 重述 + §7 Step 1-2 的 14 項逐條驗 |
| `docs/handoff.md`「過了再分頭」 | ① reload 後仍有 `window.__showme` ② 頁面 emit，Python 收得到 | §7 Step 1-1：A05 的 `tests/test_browser_inject.py` 就是這兩條 |
| `docs/sample-app.md` | 示範站 finefoods-antd 的建置與啟動、疑難排解 | §7 Step 2 引用，不重抄 |
| `scripts/setup-sample-app.sh` | 一鍵 scaffold + 修 peer dependency + `npm install` | §7 Step 2 |
| `features/顯示步驟.feature` | Rule：畫出 overlay 後阻塞直到使用者做完或逾時 | §7 Step 4-2 第 2、3 步（demo 的關鍵畫面） |
| `features/顯示步驟.feature` | Rule：任何 kind 按 Next → step_done；按 I'm stuck → stuck | §7 Step 1-2 第 10 項、Step 5 的彩排項目 |
| `features/顯示步驟.feature` | Rule：uid 通過驗證並畫出後 steps_shown 加 1，含 stuck 後重畫 | §9 的 `max_steps_exceeded` 那一列明寫「stuck 後重畫也算一步」 |
| `features/顯示步驟.feature` | Rule：steps_shown ≥ 12 → max_steps_exceeded | §9 排錯表 |
| `features/開始教學.feature` | Rule：同一時間只允許一個教學場次，再次開始時場次識別不變並覆蓋目標與網址 | §9「demo 中途想重來」 |
| `features/開始教學.feature` | Rule：目標 url 無法開啟時 navigation_failed | §9 兩列 |
| `features/開始教學.feature` | Rule：page.elements 硬上限 150、testid 鍵永遠存在、沒有 a11y name 仍列出 | §7 Step 1-2 第 2、3、4、7 項 |
| `features/結束教學.feature` | Rule：完成 banner 文案固定且忽略 summary | §7 Step 4-2 的 callout、§9 「banner 寫的是 project」 |
| `features/結束教學.feature` | Rule：成功結束後刪除 Session（再 end → session_not_found） | §7 Step 5 彩排項目 |
| `.clarify/resolved/features/結束教學_完成banner文案與summary參數的關係為何.md` | 答案 B：固定字串，忽略 summary | 同上；明確寫「不要為了 demo 好看去改」 |
| `.clarify/resolved/data/Session_各狀態允許呼叫哪些MCP工具.md` | 答案 A：嚴格依狀態機 | §7 Step 7 的 OQ1 |
| `docs/design/showme.md` §12 | overlay 五個方法的職責；Driver.js 放 `overlay/` 或 CDN；若 CSP 擋 CDN 改本地檔；init script 由 Playwright 注入不經 app CSP | §7 Step 1-3 完整說明症狀與成因 |
| `docs/design/showme.md` §15 | S7（show_step 阻塞）、S8（end_tutorial banner + 刪 Session）、S9（端到端：Qoder「教我 create a project」走到 banner） | §7 Step 4、Step 5 |
| `docs/design/showme.md` §15.1 | A/B 分工與「不要搶的檔」：A 改 `showme/**`、B 改 `overlay/**` | §5「不會動到」、§7 Step 1-3「不要自己去改 `overlay/**`」 |
| `docs/design/showme.md` §16 | Demo 當日風險五項：長時間阻塞的 IDE timeout、每個 tool 要人工確認、Chrome vs Chromium、IDE vs CLI、headed 視窗被擋 | §7 Step 6 的 checklist + §9 排錯表五列 |
| `docs/design/showme.md` §17 | open questions 1–3；1、2 歸 A 先用傾向實作，3 歸 B | §7 Step 7 全表，且明確標「A 的設計決定（可改）」而非規格 |
| `docs/design/showme.md` §3 Non-Goals | 不加第五個 tool、不做 `wait_for_user`、不做 `off_script` | §9「IDE Request Timeout」那一列明寫不要為此加 tool；§7 Step 1-2 第 12 項確認 B 沒發 `off_script` |
