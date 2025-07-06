"""Dummy personality modifiers for clan assignment."""
class PersonalityModifiers:
    async def get_modifier_for_user(self, user_id: int | str) -> float:
        return 1.0
