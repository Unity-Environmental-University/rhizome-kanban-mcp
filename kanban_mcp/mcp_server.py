"""Kanban MCP stdio server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from .board import Board, Card, DEFAULT_COLUMNS
from .hooks import run_hooks

JSON = Dict[str, Any]


def repo_root() -> Path:
    return Path(os.environ.get("RHIZOME_REPO_ROOT") or os.getcwd())


def board_path() -> Path:
    return repo_root() / ".rhizome" / "kanban" / "board.json"


def load_board() -> Board:
    return Board.load(board_path())


def list_board(_: JSON) -> JSON:
    board = load_board()
    return {
        "board": {
            "columns": {name: [card.to_dict() for card in cards] for name, cards in board.columns.items()},
            "metadata": board.metadata,
        },
        "summary": board.summary(),
    }


def add_card(params: JSON) -> JSON:
    title = params.get("title")
    if not title:
        raise ValueError("Missing required parameter: title")
    column = params.get("column") or DEFAULT_COLUMNS[0]
    card = Card(
        id=str(uuid.uuid4()),
        title=title,
        column=column,
        description=params.get("description", ""),
        tags=params.get("tags", []),
        links=params.get("links", []),
        metadata=params.get("metadata", {}),
    )
    board = load_board()
    board.ensure_columns([column])
    board.add_card(card)
    run_hooks(repo_root(), "add_card", {"card": card.to_dict(), "board_path": str(board.path)})
    return {"card": card.to_dict()}


def move_card(params: JSON) -> JSON:
    card_id = params.get("card_id")
    column = params.get("column")
    if not card_id or not column:
        raise ValueError("Parameters card_id and column are required")
    board = load_board()
    card = board.move_card(card_id, column)
    run_hooks(repo_root(), "move_card", {"card": card.to_dict(), "board_path": str(board.path)})
    return {"card": card.to_dict()}


def complete_card(params: JSON) -> JSON:
    card_id = params.get("card_id")
    if not card_id:
        raise ValueError("Parameter card_id is required")
    board = load_board()
    card = board.complete_card(card_id)
    run_hooks(repo_root(), "complete_card", {"card": card.to_dict(), "board_path": str(board.path)})
    return {"card": card.to_dict()}


def prune_done(params: JSON) -> JSON:
    older_than = int(params.get("older_than_days", 14))
    board = load_board()
    pruned = board.prune_done(older_than)
    if pruned:
        run_hooks(repo_root(), "prune_done", {"pruned": pruned, "board_path": str(board.path)})
    return {"pruned": pruned}


def import_flight(_: JSON) -> JSON:
    root = repo_root()
    active_path = root / ".rhizome" / "flight_plans" / "active.json"
    if not active_path.is_file():
        return {"message": "No active flight plan"}
    active = json.loads(active_path.read_text(encoding="utf-8"))
    fp_id = active.get("id")
    if not fp_id:
        return {"message": "Active flight plan missing id"}
    plan_path = active_path.parent / f"{fp_id}.json"
    if not plan_path.is_file():
        return {"message": "Flight plan file not found"}
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    pending = [step for step in plan.get("steps", []) if step.get("status") not in {"done", "completed"}]
    board = load_board()
    existing = {
        card.metadata.get("flight_step")
        for cards in board.columns.values()
        for card in cards
        if card.metadata.get("flight_step")
    }
    created = 0
    for step in pending:
        step_id = step.get("id")
        if step_id in existing:
            continue
        card = Card(
            id=str(uuid.uuid4()),
            title=step.get("title", f"Step {step_id}"),
            column=DEFAULT_COLUMNS[0],
            description=step.get("note", ""),
            metadata={"flight_step": step_id, "flight_id": plan.get("id")},
        )
        board.add_card(card)
        created += 1
    if created:
        run_hooks(root, "import_flight", {"created": created, "board_path": str(board.path)})
    return {"created": created}


def sync_git(_: JSON) -> JSON:
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        raise RuntimeError(f"git status failed: {exc}") from exc
    output = status.stdout.strip()
    board = load_board()
    metadata = {"git_status": True}
    backlog = board.columns.setdefault(DEFAULT_COLUMNS[0], [])
    backlog[:] = [card for card in backlog if card.metadata != metadata]
    if not output:
        board.save()
        run_hooks(repo_root(), "sync_git", {"message": "clean", "board_path": str(board.path)})
        return {"message": "Workspace clean"}
    card = Card(
        id=str(uuid.uuid4()),
        title="Workspace dirty",
        column=DEFAULT_COLUMNS[0],
        description=output,
        metadata=metadata,
        tags=["git"],
    )
    board.add_card(card)
    run_hooks(repo_root(), "sync_git", {"card": card.to_dict(), "board_path": str(board.path)})
    return {"card": card.to_dict()}


TOOLS = {
    "kanban.list_board": {
        "fn": list_board,
        "description": "Return the Kanban board and summary counts",
        "parameters": {"type": "object", "properties": {}},
    },
    "kanban.add_card": {
        "fn": add_card,
        "description": "Add a card to the board",
        "parameters": {
            "type": "object",
            "required": ["title"],
            "properties": {
                "title": {"type": "string"},
                "column": {"type": "string"},
                "description": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "links": {"type": "array", "items": {"type": "string"}},
                "metadata": {"type": "object"},
            },
        },
    },
    "kanban.move_card": {
        "fn": move_card,
        "description": "Move a card to a different column",
        "parameters": {
            "type": "object",
            "required": ["card_id", "column"],
            "properties": {
                "card_id": {"type": "string"},
                "column": {"type": "string"},
            },
        },
    },
    "kanban.complete_card": {
        "fn": complete_card,
        "description": "Move a card to Done and stamp completed_at",
        "parameters": {
            "type": "object",
            "required": ["card_id"],
            "properties": {"card_id": {"type": "string"}},
        },
    },
    "kanban.prune_done": {
        "fn": prune_done,
        "description": "Remove completed cards older than N days",
        "parameters": {
            "type": "object",
            "properties": {"older_than_days": {"type": "integer", "minimum": 1}},
        },
    },
    "kanban.import_flight": {
        "fn": import_flight,
        "description": "Seed cards from active flight plan pending steps",
        "parameters": {"type": "object", "properties": {}},
    },
    "kanban.sync_git": {
        "fn": sync_git,
        "description": "Summarise git status into a backlog card",
        "parameters": {"type": "object", "properties": {}},
    },
}


def tools_list() -> JSON:
    return {name: {"description": meta["description"], "parameters": meta["parameters"]} for name, meta in TOOLS.items()}


def tools_call(name: str, arguments: Optional[JSON]) -> JSON:
    tool = TOOLS.get(name)
    if not tool:
        raise ValueError(f"Tool '{name}' not found")
    fn = tool["fn"]
    return fn(arguments or {})


def handle_request(request: JSON) -> JSON:
    jsonrpc = request.get("jsonrpc")
    method = request.get("method")
    req_id = request.get("id")
    if jsonrpc != "2.0":
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32600, "message": "Invalid Request"}}
    try:
        if method == "initialize":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"serverInfo": {"name": "kanban-mcp", "version": "0.1.0"}}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": tools_list()}
        if method == "tools/call":
            params = request.get("params") or {}
            name = params.get("name")
            arguments = params.get("arguments")
            result = tools_call(name, arguments)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
    except ValueError as exc:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": str(exc)}}
    except Exception as exc:  # pylint: disable=broad-except
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": str(exc)}}


def main() -> None:
    raw = sys.stdin.read() if not sys.stdin.isatty() else (sys.argv[1] if len(sys.argv) > 1 else "")
    if not raw:
        sys.stderr.write("No JSON-RPC payload provided\n")
        sys.exit(1)
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as exc:
        response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc}"}}
    else:
        response = handle_request(request)
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
