class ClanData:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir

    def create_default_clans(self):
        return {
            "Uchiha": {"name": "Uchiha", "rarity": "Legendary"},
            "Hyuga": {"name": "Hyuga", "rarity": "Rare"}
        }

    async def get_clan_by_name(self, name: str):
        return self.create_default_clans().get(name)

    async def get_all_clans(self):
        return list(self.create_default_clans().values())

    async def add_clan(self, clan: dict) -> None:
        pass
