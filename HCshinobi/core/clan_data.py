"""Minimal clan data loader."""
from typing import Dict


class ClanData:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir
        self._clans: Dict[str, dict] = {}

    def create_default_clans(self) -> Dict[str, dict]:
        self._clans = {"Uchiha": {"name": "Uchiha"}}
        return self._clans

    def get_clan(self, name: str) -> dict:
        return self._clans.get(name, {"name": name})
