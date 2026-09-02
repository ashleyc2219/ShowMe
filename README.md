# ShowMe

**Ask any web app how to do something. It shows you where to click.**

ShowMe is a **stdio [MCP](https://modelcontextprotocol.io) server** that lets AI coding agents (Qoder, Claude Code, ...) *teach* users how to use a web app. The agent calls ShowMe's tools, ShowMe opens a real headed Chrome with [Playwright](https://playwright.dev/python/), injects an overlay into the target page, and draws arrows and highlights — **the user does every click and keystroke themselves. ShowMe teaches, never acts.**

Built as a 5-hour hackathon project. No LLM inside — just tools, a browser, and an overlay.

## How it works

```text
AI Agent (Qoder / Claude Code)
    │  MCP stdio — 4 tools
    ▼
showme/ (Python)          at most one session in memory
    │  Playwright: launch / goto / add_init_script / expose_function
    ▼
Chrome (headed)
    ├── your web app (e.g. localhost:3000)   ← the user operates it
    └── overlay.js (Driver.js)               ← highlights + "done" detection
```

The agent plans the steps; `show_step` blocks until the human finishes the highlighted action (or presses "I'm stuck", or times out), then returns a fresh page snapshot so the agent can pick the next step.

## Tools

| Tool | What it does |
|---|---|
| `start_tutorial(url, goal)` | Open the app in a headed browser, inject the overlay, start the session, return the first page snapshot (uids `s1-*`) |
| `inspect_page(session_id)` | Re-snapshot the current page without drawing anything |
| `show_step(session_id, uid, instruction, ...)` | Highlight one element and **block** until the user finishes (`step_done`), gets `stuck`, or `timeout` — returns a fresh snapshot |
| `end_tutorial(session_id, summary)` | Clear the overlay, show the done banner, delete the session |

`kind` is one of `click` / `input` / `select` / `observe`. Completion detection lives in the overlay: target removed/hidden, URL changed, or the user presses Next.

## Quick start

Requirements: **Python 3.12**, **uv**, **Google Chrome**.

```bash
git clone https://github.com/ashleyc2219/ShowMe.git
cd ShowMe
uv sync                        # install dependencies
uv run playwright install chromium   # only needed for headless tests
```

Register the server in your MCP client (Qoder / Claude Code):

```json
{
  "mcpServers": {
    "showme": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ShowMe", "run", "showme"]
    }
  }
}
```

> ⚠️ `show_step` blocks for up to 120 seconds — raise your client's MCP request timeout accordingly.

Then just ask your agent, e.g. *"Teach me how to create an order in this app at http://localhost:3000"*.

### Demo: a real sample app

We use the [refine](https://refine.dev) **finefoods-antd** example (a food-delivery admin panel) as the target app:

```bash
./scripts/setup-sample-app.sh        # scaffolds into sample-app/ (not in git)
cd sample-app/finefoods-antd && npm run dev   # → http://localhost:3000
```

Details in [docs/sample-app.md](docs/sample-app.md).

## Development

```bash
uv run pytest                      # full suite
uv run pytest -m "not browser"     # fast: skips tests that launch Chromium
uv run pytest -m browser           # only headless-browser tests
uv run showme                      # run the MCP server manually (stdio)
```

Testing is TDD throughout: in-memory MCP client contract tests, `FakeBrowser`/fake-overlay test doubles, and headless end-to-end tests.

## Project layout

| Path | Role |
|---|---|
| `showme/server.py` | Thin MCP shell — 4 tools forward to the app |
| `showme/app.py` | Tool logic |
| `showme/session.py` | Session / state machine (READY → SHOWING) |
| `showme/rules.py` | Pure validation rules (no dependencies) |
| `showme/browser.py` | Playwright wrapper behind a `BrowserLike` protocol |
| `overlay/` | Injected JS: DOM snapshots, Driver.js highlights, done detection |
| `tests/` | pytest suite incl. e2e with a real browser |

Architecture notes: [docs/handoff.md](docs/handoff.md) · design: [docs/design/showme.md](docs/design/showme.md)

## Credits

- [Model Context Protocol](https://modelcontextprotocol.io) — the agent↔tool protocol
- [Playwright for Python](https://playwright.dev/python/) — browser automation
- [Driver.js](https://driverjs.com/) — element highlighting inside the overlay
- [refine finefoods-antd](https://refine.dev/docs/examples/finefoods/) — demo target app
