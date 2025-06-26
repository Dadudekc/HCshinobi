class TokenSystem:
    def __init__(self, data_file: str | None = None) -> None:
        self.data_file = data_file or "tokens.json"
        self.tokens: dict[str, int] = {}

    def get_player_tokens(self, user_id: int | str) -> int:
        return self.tokens.get(str(user_id), 0)

    def set_player_tokens(self, user_id: int | str, amount: int) -> None:
        self.tokens[str(user_id)] = amount

    def add_tokens_and_save(self, user_id: int | str, amount: int) -> int:
        new_amount = self.get_player_tokens(user_id) + amount
        self.tokens[str(user_id)] = new_amount
        return new_amount

    def save_token_data(self) -> None:
        pass
