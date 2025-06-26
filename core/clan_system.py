"""Simple clan data loader and membership management."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional, List


class ClanSystem:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = Path(data_dir) / "clans"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._clans: Dict[str, Dict] = {}
        self._load_clans()

    def _load_clans(self) -> None:
        file = self.data_dir / "clans.json"
        if file.exists():
            with open(file, "r", encoding="utf-8") as f:
                for clan in json.load(f):
                    self._clans[clan["name"]] = clan

    def get_clan(self, name: str) -> Optional[Dict]:
        return self._clans.get(name)

    def list_clans(self) -> List[Dict]:
        return list(self._clans.values())
