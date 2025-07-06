class TokenSystem:
    def __init__(self) -> None:
        self.tokens = {}

    async def get_player_tokens(self, user_id: int) -> int:
        return self.tokens.get(str(user_id), 0)

    async def add_tokens(self, user_id: int, amount: int) -> None:
        self.tokens[str(user_id)] = self.tokens.get(str(user_id), 0) + amount
