"""In-memory helpers for the Kanban board stored as JSON."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_COLUMNS = ["Backlog", "In Progress", "Review", "Done"]
TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%SZ"


def utcnow() -> datetime:
    return datetime.utcnow()


def timestamp() -> str:
    return utcnow().strftime(TIMESTAMP_FMT)


@dataclass
class Card:
    id: str
    title: str
    column: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=timestamp)
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "column": self.column,
            "tags": self.tags,
            "links": self.links,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }


@dataclass
class Board:
    path: Path
    columns: Dict[str, List[Card]]
    metadata: Dict[str, object]

    @classmethod
    def load(cls, path: Path) -> "Board":
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            columns = {
                name: [Card(**card) for card in cards]
                for name, cards in data.get("columns", {}).items()
            }
            metadata = data.get("metadata", {})
        else:
            columns = {name: [] for name in DEFAULT_COLUMNS}
            metadata = {"created_at": timestamp()}
        board = cls(path=path, columns=columns, metadata=metadata)
        board.ensure_columns(DEFAULT_COLUMNS)
        return board

    def save(self) -> None:
        payload = {
            "columns": {name: [card.to_dict() for card in cards] for name, cards in self.columns.items()},
            "metadata": self.metadata,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def ensure_columns(self, names: List[str]) -> None:
        for name in names:
            self.columns.setdefault(name, [])

    def add_card(self, card: Card) -> Card:
        self.ensure_columns([card.column])
        self.columns[card.column].append(card)
        self.save()
        return card

    def find_card(self, card_id: str) -> Optional[Card]:
        for cards in self.columns.values():
            for card in cards:
                if card.id == card_id:
                    return card
        return None

    def move_card(self, card_id: str, column: str) -> Card:
        card = self.find_card(card_id)
        if not card:
            raise ValueError(f"Card '{card_id}' not found")
        self.ensure_columns([column])
        for cards in self.columns.values():
            if card in cards:
                cards.remove(card)
                break
        card.column = column
        card.updated_at = timestamp()
        self.columns[column].append(card)
        self.save()
        return card

    def complete_card(self, card_id: str) -> Card:
        card = self.move_card(card_id, "Done")
        card.completed_at = timestamp()
        self.save()
        return card

    def prune_done(self, older_than_days: int) -> int:
        cutoff = utcnow() - timedelta(days=older_than_days)
        done_cards = self.columns.get("Done", [])
        kept: List[Card] = []
        removed = 0
        for card in done_cards:
            if not card.completed_at:
                kept.append(card)
                continue
            completed_at = datetime.strptime(card.completed_at, TIMESTAMP_FMT)
            if completed_at < cutoff:
                removed += 1
            else:
                kept.append(card)
        self.columns["Done"] = kept
        if removed:
            self.save()
        return removed

    def summary(self) -> Dict[str, int]:
        return {name: len(cards) for name, cards in self.columns.items()}
