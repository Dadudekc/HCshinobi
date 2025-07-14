class ClanData:
    def __init__(self, data_dir: str = "data") -> None:
        self.data_dir = data_dir

    def create_default_clans(self):
        return {
            # Legendary Clans
            "Uchiha": {"name": "Uchiha", "rarity": "Legendary", "description": "Clan of the Sharingan, masters of fire and lightning techniques"},
            "Senju": {"name": "Senju", "rarity": "Legendary", "description": "Clan of the First Hokage, masters of wood release and healing"},
            "Uzumaki": {"name": "Uzumaki", "rarity": "Legendary", "description": "Clan of sealing techniques and chakra chains"},
            
            # Epic Clans
            "Hyuga": {"name": "Hyuga", "rarity": "Epic", "description": "Clan of the Byakugan, masters of gentle fist techniques"},
            "Aburame": {"name": "Aburame", "rarity": "Epic", "description": "Clan of insect users, masters of bug techniques"},
            "Inuzuka": {"name": "Inuzuka", "rarity": "Epic", "description": "Clan of beast companions, masters of tracking and fang techniques"},
            "Nara": {"name": "Nara", "rarity": "Epic", "description": "Clan of shadow techniques, masters of strategy and intelligence"},
            "Yamanaka": {"name": "Yamanaka", "rarity": "Epic", "description": "Clan of mind techniques, masters of telepathy and possession"},
            "Akimichi": {"name": "Akimichi", "rarity": "Epic", "description": "Clan of expansion techniques, masters of size manipulation"},
            
            # Rare Clans
            "Sarutobi": {"name": "Sarutobi", "rarity": "Rare", "description": "Clan of fire techniques, masters of the monkey summoning"},
            "Hatake": {"name": "Hatake", "rarity": "Rare", "description": "Clan of white chakra, masters of lightning techniques"},
            "Kaguya": {"name": "Kaguya", "rarity": "Rare", "description": "Clan of bone techniques, masters of Shikotsumyaku"},
            "Hozuki": {"name": "Hozuki", "rarity": "Rare", "description": "Clan of water techniques, masters of liquid transformation"},
            "Kaguya": {"name": "Kaguya", "rarity": "Rare", "description": "Clan of bone techniques, masters of Shikotsumyaku"},
            
            # Uncommon Clans
            "Kazekage": {"name": "Kazekage", "rarity": "Uncommon", "description": "Clan of wind techniques, masters of sand manipulation"},
            "Mizukage": {"name": "Mizukage", "rarity": "Uncommon", "description": "Clan of water techniques, masters of mist and ice"},
            "Raikage": {"name": "Raikage", "rarity": "Uncommon", "description": "Clan of lightning techniques, masters of speed and power"},
            "Tsuchikage": {"name": "Tsuchikage", "rarity": "Uncommon", "description": "Clan of earth techniques, masters of stone and dust"},
            "Hokage": {"name": "Hokage", "rarity": "Uncommon", "description": "Clan of fire techniques, masters of leadership and wisdom"},
            
            # Common Clans
            "Civilian": {"name": "Civilian", "rarity": "Common", "description": "No special bloodline, but potential for greatness through hard work"},
            "Merchant": {"name": "Merchant", "rarity": "Common", "description": "Clan of trade and commerce, masters of negotiation"},
            "Farmer": {"name": "Farmer", "rarity": "Common", "description": "Clan of agriculture, masters of earth and plant techniques"},
            "Blacksmith": {"name": "Blacksmith", "rarity": "Common", "description": "Clan of metalworking, masters of weapon crafting"},
            "Scholar": {"name": "Scholar", "rarity": "Common", "description": "Clan of knowledge, masters of research and learning"}
        }

    async def get_clan_by_name(self, name: str):
        return self.create_default_clans().get(name)

    async def get_all_clans(self):
        return list(self.create_default_clans().values())

    async def add_clan(self, clan: dict) -> None:
        pass
