class CurrencySystem:
    def __init__(self, data_file: str | None = None) -> None:
        self.data_file = data_file or "currency.json"
        self.balances: dict[str, int] = {}

    def get_player_balance(self, user_id: int | str) -> int:
        return self.balances.get(str(user_id), 0)

    def set_player_balance(self, user_id: int | str, amount: int) -> None:
        self.balances[str(user_id)] = amount

    def add_balance_and_save(self, user_id: int | str, amount: int) -> int:
        new_balance = self.get_player_balance(user_id) + amount
        self.balances[str(user_id)] = new_balance
        return new_balance

    def save_currency_data(self) -> None:
        pass
