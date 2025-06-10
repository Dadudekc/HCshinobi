import inspect

class CharacterCommands:
    async def profile(self, user_id):
        # Fetch currency and tokens, supporting both async and sync methods
        ryo = 0
        tokens = 0
        currency_system = getattr(self.bot.services, 'currency_system', None)
        token_system = getattr(self.bot.services, 'token_system', None)
        if currency_system:
            raw_ryo = currency_system.get_player_balance(user_id)
            ryo = await raw_ryo if inspect.isawaitable(raw_ryo) else raw_ryo
        if token_system:
            raw_tokens = token_system.get_player_tokens(user_id)
            tokens = await raw_tokens if inspect.isawaitable(raw_tokens) else raw_tokens

        # Fetch other profile information
        # ... existing code ...

        # ... rest of the method ...



