class CurrencySystem:
    def __init__(self) -> None:
        self.balances = {}

    async def get_player_balance(self, user_id: int) -> int:
        return self.balances.get(str(user_id), 0)

    async def add_balance(self, user_id: int, amount: int) -> None:
        self.balances[str(user_id)] = self.balances.get(str(user_id), 0) + amount
