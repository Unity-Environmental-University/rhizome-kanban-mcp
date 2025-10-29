# MCP Tool Contracts

Each request follows JSON-RPC 2.0. Example envelope:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "kanban.add_card", "arguments": {"title": "Write docs"}}}
```

## kanban.list_board
- **Description:** Return all columns and cards.
- **Arguments:** none.
- **Result:** `{ "board": {"columns": {...}}, "summary": {"Backlog": 3, ...} }`

## kanban.add_card
- **Arguments:**
  - `title` (string, required)
  - `column` (string, optional; default `Backlog`)
  - `description` (string, optional)
  - `tags` (array of strings, optional)
  - `links` (array of strings, optional)
  - `metadata` (object, optional)
- **Result:** `{ "card": { ... } }`

## kanban.move_card
- **Arguments:**
  - `card_id` (string, required)
  - `column` (string, required)
- **Result:** `{ "card": { ... } }`

## kanban.complete_card
- **Arguments:**
  - `card_id` (string, required)
- **Result:** `{ "card": { ... } }`

## kanban.prune_done
- **Arguments:**
  - `older_than_days` (integer, optional, default 14)
- **Result:** `{ "pruned": 3 }`

## kanban.import_flight
- **Description:** Pull pending steps from the active Rhizome flight plan.
- **Arguments:** none.
- **Result:** `{ "created": 2 }`

## kanban.sync_git
- **Description:** Summarise `git status --porcelain` and add/update a backlog card.
- **Arguments:** none.
- **Result:** `{ "card": { ... } }` or `{ "message": "Workspace clean" }`

## Hooks
If `.rhizome/kanban/hooks.d/` exists in the calling repository, every executable
file in that directory is invoked after mutations (`add_card`, `move_card`,
`complete_card`, `prune_done`, `import_flight`, `sync_git`). The tool passes a
JSON payload on stdin:

```json
{
  "event": "add_card",
  "card": { ... },
  "board_path": "/abs/path/.rhizome/kanban/board.json"
}
```

Use this to trigger notifications, update external trackers, etc.
