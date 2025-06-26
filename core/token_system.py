"""Simple token tracking system."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class TokenSystem:
    def __init__(self, data_dir: str = "data") -> None:
        self.file = Path(data_dir) / "tokens" / "tokens.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.tokens: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if self.file.exists():
            with open(self.file, "r", encoding="utf-8") as f:
                self.tokens = json.load(f)

    def save(self) -> None:
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.tokens, f, indent=2)

    def get_player_tokens(self, user_id: int | str) -> int:
        return int(self.tokens.get(str(user_id), 0))

    def add_tokens(self, user_id: int | str, amount: int) -> None:
        self.tokens[str(user_id)] = self.get_player_tokens(user_id) + amount
        self.save()
