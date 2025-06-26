class TokenSystem:
    """Simple token tracking system."""

    def __init__(self, data_path: str = "") -> None:
        self.tokens = {}

    async def get_player_tokens(self, user_id: str) -> int:
        return self.tokens.get(user_id, 0)

    async def add_tokens(self, user_id: str, amount: int) -> None:
        self.tokens[user_id] = self.tokens.get(user_id, 0) + amount
