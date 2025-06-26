"""Simple token tracking system."""
from typing import Dict


class TokenSystem:
    def __init__(self) -> None:
        self._tokens: Dict[int, int] = {}

    async def get_player_tokens(self, user_id: int) -> int:
        return self._tokens.get(user_id, 0)

    async def set_player_tokens(self, user_id: int, amount: int) -> None:
        self._tokens[user_id] = amount
