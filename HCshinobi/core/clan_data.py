class ClanData:
    """Placeholder clan data access."""

    def __init__(self, data_dir: str = "") -> None:
        self.data_dir = data_dir

    def get_all_clans(self):
        return []

    async def get_clan_by_name(self, name: str):
        return None

    def create_default_clans(self):
        return {}
