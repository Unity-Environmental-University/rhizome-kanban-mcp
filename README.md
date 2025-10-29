# rhizome-kanban-mcp

Minimal MCP (Model Context Protocol) server that keeps a human-facing Kanban
board alongside a Rhizome repository. Personas and human operators can
add/move/complete cards via `rhizome mcp` commands or any MCP-compatible client.
State is stored as JSON under `.rhizome/kanban/` and hooks allow further
automation (e.g. notifications, syncing to other systems).

## Features

- Opinionated default columns: **Backlog → In Progress → Review → Done**
- JSON-backed board (`.rhizome/kanban/board.json`) — no external database.
- Tools:
  - `kanban.list_board` — peek at columns & cards.
  - `kanban.add_card` — create work items with tags/links/metadata.
  - `kanban.move_card` — move across columns.
  - `kanban.complete_card` — mark complete (moves to `Done`).
  - `kanban.prune_done` — drop stale completed cards.
  - `kanban.import_flight` — seed cards from Rhizome flight-plan steps.
  - `kanban.sync_git` — summarize `git status` into a backlog card.
- Hook support: executables in `.rhizome/kanban/hooks.d` are invoked on
  mutations with a JSON payload (`event`, `card`, etc.).
- Installable via `rhizome mcp plugin install https://github.com/unity-edu/rhizome-kanban-mcp.git`.

## Quick Start

```bash
# clone this repo somewhere reachable
cd /path/to/rhizome-kanban-mcp

# list tools (stdio one-shot)
printf '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | ./bin/kanban-mcp

# integrate with rhizome (from your target repo)
rhizome mcp plugin install https://github.com/unity-edu/rhizome-kanban-mcp.git
rhizome mcp call kanban.add_card --arg title="Draft release notes"
```

## Directory layout

```
rhizome-kanban-mcp/
├── README.md
├── LICENSE
├── rhizome-mcp.json        # tells Rhizome how to launch the server
├── bin/kanban-mcp          # thin launcher (stdio JSON-RPC)
├── kanban_mcp/             # Python package with server + helpers
└── docs/
    └── API.md              # tool contracts & payload examples
```

The MCP server is stateless.  It reads / writes `.rhizome/kanban/board.json`
in the calling repository.  Hook executables (if present) live under `.rhizome/kanban/hooks.d/`.

## Requirements

- Python 3.9+
- No third-party dependencies; only standard library modules are used.

## Development

```bash
python -m compileall kanban_mcp bin/kanban-mcp
pytest            # (optional) if you add tests
```

Run the lint/test suite before submitting PRs.  The project uses MIT license.
