"""Basic in-memory currency management."""
from typing import Dict


class CurrencySystem:
    def __init__(self) -> None:
        self._balances: Dict[int, int] = {}

    async def get_player_balance(self, user_id: int) -> int:
        return self._balances.get(user_id, 0)

    async def set_player_balance(self, user_id: int, amount: int) -> None:
        self._balances[user_id] = amount
