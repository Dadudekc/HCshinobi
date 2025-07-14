class CurrencySystem:
    def __init__(self) -> None:
        self.balances = {}

    async def get_player_balance(self, user_id: int) -> int:
        return self.balances.get(str(user_id), 0)

    async def add_balance(self, user_id: int, amount: int) -> None:
        self.balances[str(user_id)] = self.balances.get(str(user_id), 0) + amount

    def add_balance_and_save(self, user_id: int, amount: int) -> int:
        """Add balance and return the new balance. This is a sync method for compatibility."""
        self.balances[str(user_id)] = self.balances.get(str(user_id), 0) + amount
        return self.balances[str(user_id)]
