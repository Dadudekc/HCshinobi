class CurrencySystem:
    """Simple in-memory currency manager."""

    def __init__(self, data_path: str = "") -> None:
        self.balances = {}

    async def get_player_balance(self, user_id: str) -> int:
        return self.balances.get(user_id, 0)

    async def set_player_balance(self, user_id: str, amount: int) -> None:
        self.balances[user_id] = amount

    def add_balance_and_save(self, user_id: str, amount: int) -> None:
        self.balances[user_id] = self.balances.get(user_id, 0) + amount
