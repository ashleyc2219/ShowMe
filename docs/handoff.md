# ShowMe 接縫

A：`showme/` 四個 MCP tool。  
B：`overlay/overlay.js`（寫一次就好，AI 不即時產生 JS）。  
中間沒有 HTTP、沒有 import。

Tool 回給 AI 的是 **元素清單**（uid / role / name / testid），不是截圖。  
AI 看清單決定下一步要指哪個 uid。產品頁每個 project 不同；overlay 不變。

```text
Qoder
  │  MCP stdio
  ▼
MCP Server  showme/（A）
  start_tutorial · inspect_page · show_step · end_tutorial
  │  Playwright：evaluate / expose_function
  ▼
Chrome
  ├── 產品頁 :3000     人自己點／打字
  └── overlay.js（B）  __showme.snapshot / show / clear / done
                         │
                         └── emit ──▶ 叫醒卡住的 show_step ──▶ Qoder
```

| Tool | 這個 tool 要做到什麼 | 對應 JS | JS 要做到什麼 |
|---|---|---|---|
| `start_tutorial` | 開 Chrome、進 url、建立場次、回第一份元素清單 | `snapshot(n)` | 掃頁、貼 uid、回 `elements`（最多 150） |
| `inspect_page` | 再拍一次現在畫面，不畫箭頭 | `snapshot(n)` | 同上 |
| `show_step` | 對指定 uid 畫箭頭，卡住直到人做完／卡住／逾時，再回新清單 | `show(...)` → `__showme_emit` | 畫箭頭與說明；人做完或按 I'm stuck 時 emit 一次（不發 timeout） |
| `end_tutorial` | 清場、固定完成橫幅、刪場次 | `clear()` + `done(text)` | 拿掉箭頭；顯示 A 傳入的完成文案 |

細節：`docs/design/showme.md` §12。

---

## 鎖死的名字

A 呼叫：

```text
__showme.snapshot(n) → { elements, truncated }
__showme.show({ uid, instruction, kind, index, total, expect })
__showme.clear()
__showme.done(text)
```

B 呼叫（每步一次）：

```text
__showme_emit({ kind: "step_done" | "stuck", url, ts })
```

B 不發 `timeout`。`show.expect` = MCP 的 `expect_text`。  
`elements[]`：`uid` `role` `name` `testid`（沒有就 `""`）。  
uid 格式：A 給 `n`，B 組 `s{n}-{index}`。

---

## 目錄

A 改 `showme/`。B 改 `overlay/`。

## 過了再分頭

1. reload 後仍有 `window.__showme`
2. 頁面 `emit`，Python 收得到

下次再合：S7（人做完，`show_step` 才回來）。
