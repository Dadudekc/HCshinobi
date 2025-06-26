"""Manage player currency using a JSON file."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class CurrencySystem:
    def __init__(self, data_dir: str = "data") -> None:
        self.file = Path(data_dir) / "currency" / "currency.json"
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.balances: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if self.file.exists():
            with open(self.file, "r", encoding="utf-8") as f:
                self.balances = json.load(f)

    def save(self) -> None:
        with open(self.file, "w", encoding="utf-8") as f:
            json.dump(self.balances, f, indent=2)

    def get_player_balance(self, user_id: int | str) -> int:
        return int(self.balances.get(str(user_id), 0))

    def set_player_balance(self, user_id: int | str, amount: int) -> None:
        self.balances[str(user_id)] = amount
        self.save()

    def add_balance_and_save(self, user_id: int | str, amount: int) -> None:
        self.balances[str(user_id)] = self.get_player_balance(user_id) + amount
        self.save()
