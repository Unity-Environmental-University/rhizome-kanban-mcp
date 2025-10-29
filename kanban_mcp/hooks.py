"""Hook dispatching for Kanban events."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


def hooks_dir(repo_root: Path) -> Path:
    return repo_root / ".rhizome" / "kanban" / "hooks.d"


def run_hooks(repo_root: Path, event: str, payload: Dict[str, Any]) -> None:
    directory = hooks_dir(repo_root)
    if not directory.is_dir():
        return
    for hook in sorted(directory.iterdir()):
        if not hook.is_file() or not os.access(hook, os.X_OK):
            continue
        try:
            subprocess.run(
                [str(hook)],
                input=json.dumps({"event": event, **payload}, ensure_ascii=False),
                text=True,
                check=False,
            )
        except Exception:
            # Hooks should not break the MCP call; swallow errors.
            continue
