"""
Test suite for Solomon Boss Battle System
Tests the ultimate boss battle functionality.
"""
import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Import the boss battle system
import sys
sys.path.append('..')
from core.boss_battle_system import BossBattleSystem, BossBattleCommands

class TestSolomonBossBattle:
    """Test cases for Solomon boss battle system."""
    
    @pytest.fixture
    def sample_character_data(self):
        """Sample character data for testing."""
        return {
            "id": "123456789",
            "name": "Test Shinobi",
            "level": 55,
            "hp": 500,
            "max_hp": 500,
            "chakra": 300,
            "max_chakra": 300,
            "stamina": 200,
            "max_stamina": 200,
            "ninjutsu": 80,
            "jutsu": ["Katon: Gōka Messhitsu", "Rasengan", "Shadow Clone Jutsu"],
            "achievements": ["Master of Elements", "Battle Hardened"],
            "titles": ["Genin", "Fire Master"]
        }
        
    @pytest.fixture
    def sample_boss_data(self):
        """Sample Solomon boss data for testing."""
        return {
            "id": "solomon",
            "name": "Solomon - The Burning Revenant",
            "level": 70,
            "hp": 1500,
            "max_hp": 1500,
            "chakra": 1000,
            "max_chakra": 1000,
            "stamina": 500,
            "max_stamina": 500,
            "boss_phases": [
                {
                    "name": "Phase 1: The Crimson Shadow",
                    "hp_threshold": 1.0,
                    "description": "Solomon begins with Sharingan analysis and basic Katon techniques",
                    "jutsu_pool": ["Katon: Gōka Messhitsu", "Katon: Gōryūka no Jutsu", "Sharingan Genjutsu", "Adamantine Chakra-Forged Chains"],
                    "special_abilities": ["Sharingan Analysis", "Chakra Absorption"]
                },
                {
                    "name": "Phase 2: The Burning Revenant",
                    "hp_threshold": 0.7,
                    "description": "Solomon activates Mangekyō Sharingan and unleashes Amaterasu",
                    "jutsu_pool": ["Amaterasu", "Kamui Phase", "Yōton: Maguma Hōkai", "Yōton: Ryūsei no Jutsu"],
                    "special_abilities": ["Amaterasu Mastery", "Kamui Intangibility", "Lava Release"]
                }
            ],
            "boss_requirements": {
                "min_level": 50,
                "required_achievements": ["Master of Elements", "Battle Hardened"],
                "cooldown_hours": 168
            },
            "boss_rewards": {
                "exp": 10000,
                "ryo": 50000,
                "tokens": 100,
                "special_items": ["Solomon's Chain Fragment", "Burning Revenant's Cloak"],
                "achievements": ["Solomon Slayer", "The Ultimate Challenge"],
                "titles": ["Solomon's Equal", "The Unbreakable"]
            }
        }
        
    @pytest.fixture
    def mock_bot(self):
        """Mock bot for testing."""
        bot = MagicMock()
        bot.add_cog = AsyncMock()
        return bot
        
    @pytest.fixture
    def boss_system(self, mock_bot, sample_boss_data):
        """Boss battle system instance for testing."""
        with patch('core.boss_battle_system.BossBattleSystem.load_boss_data', return_value=sample_boss_data):
            return BossBattleSystem(mock_bot)
            
    def test_load_boss_data(self, mock_bot):
        """Test loading boss data from file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_data = {"test": "data"}
            json.dump(test_data, f)
            temp_file = f.name
            
        try:
            with patch('core.boss_battle_system.BossBattleSystem.boss_data_path', temp_file):
                system = BossBattleSystem(mock_bot)
                assert system.boss_data == test_data
        finally:
            os.unlink(temp_file)
            
    def test_get_current_phase(self, boss_system):
        """Test getting current boss phase based on HP percentage."""
        # Full HP should be Phase 1
        phase = boss_system.get_current_phase(1.0)
        assert phase["name"] == "Phase 1: The Crimson Shadow"
        
        # 80% HP should still be Phase 1
        phase = boss_system.get_current_phase(0.8)
        assert phase["name"] == "Phase 1: The Crimson Shadow"
        
        # 60% HP should be Phase 2
        phase = boss_system.get_current_phase(0.6)
        assert phase["name"] == "Phase 2: The Burning Revenant"
        
    def test_calculate_boss_damage(self, boss_system):
        """Test boss damage calculation."""
        phase = {"name": "Phase 1: The Crimson Shadow"}
        
        # Test basic damage
        damage = boss_system.calculate_boss_damage("Katon: Gōka Messhitsu", phase)
        assert damage == 80  # Base damage for Phase 1
        
        # Test phase multiplier
        phase = {"name": "Phase 2: The Burning Revenant"}
        damage = boss_system.calculate_boss_damage("Katon: Gōka Messhitsu", phase)
        assert damage == 104  # 80 * 1.3
        
        # Test unknown jutsu
        damage = boss_system.calculate_boss_damage("Unknown Jutsu", phase)
        assert damage == 130  # 100 * 1.3
        
    def test_get_boss_jutsu(self, boss_system):
        """Test getting random jutsu from phase pool."""
        phase = {
            "jutsu_pool": ["Jutsu 1", "Jutsu 2", "Jutsu 3"]
        }
        
        jutsu = boss_system.get_boss_jutsu(phase)
        assert jutsu in ["Jutsu 1", "Jutsu 2", "Jutsu 3"]
        
        # Test empty pool
        phase = {"jutsu_pool": []}
        jutsu = boss_system.get_boss_jutsu(phase)
        assert jutsu == "Basic Attack"
        
    def test_check_boss_requirements(self, boss_system, sample_character_data):
        """Test boss battle requirements checking."""
        # Test valid character
        can_battle, message = boss_system.check_boss_requirements(sample_character_data)
        assert can_battle == True
        assert "Requirements met" in message
        
        # Test insufficient level
        character_low_level = sample_character_data.copy()
        character_low_level["level"] = 30
        can_battle, message = boss_system.check_boss_requirements(character_low_level)
        assert can_battle == False
        assert "level 50" in message
        
        # Test missing achievements
        character_no_achievements = sample_character_data.copy()
        character_no_achievements["achievements"] = []
        can_battle, message = boss_system.check_boss_requirements(character_no_achievements)
        assert can_battle == False
        assert "Master of Elements" in message
        
    @pytest.mark.asyncio
    async def test_start_boss_battle(self, boss_system, sample_character_data):
        """Test starting a boss battle."""
        mock_interaction = AsyncMock()
        mock_interaction.followup.send = AsyncMock()
        
        # Test successful battle start
        result = await boss_system.start_boss_battle(mock_interaction, sample_character_data)
        assert result == True
        
        # Verify battle was initialized
        user_id = str(sample_character_data["id"])
        assert user_id in boss_system.active_boss_battles
        
        battle_data = boss_system.active_boss_battles[user_id]
        assert battle_data["character"]["name"] == "Test Shinobi"
        assert battle_data["boss"]["name"] == "Solomon - The Burning Revenant"
        assert battle_data["turn"] == 1
        
        # Test already in battle
        result = await boss_system.start_boss_battle(mock_interaction, sample_character_data)
        assert result == False
        mock_interaction.followup.send.assert_called_with("❌ You are already in a battle with Solomon!")
        
    def test_create_battle_embed(self, boss_system, sample_character_data):
        """Test battle embed creation."""
        battle_data = {
            "character": sample_character_data,
            "boss": boss_system.boss_data,
            "turn": 1,
            "battle_log": ["Test log entry"]
        }
        
        # Test battle start embed
        embed = boss_system.create_battle_embed(battle_data, "battle_start")
        assert "SOLOMON - THE BURNING REVENANT" in embed.title
        assert "The Ultimate Being has appeared" in embed.description
        
        # Test battle turn embed
        embed = boss_system.create_battle_embed(battle_data, "battle_turn")
        assert "BATTLE TURN 1" in embed.title
        
        # Verify character stats are included
        char_field = None
        for field in embed.fields:
            if "Test Shinobi" in field.name:
                char_field = field
                break
        assert char_field is not None
        assert "500/500" in char_field.value
        
    @pytest.mark.asyncio
    async def test_process_boss_turn(self, boss_system):
        """Test processing boss turn."""
        battle_data = {
            "character": {"hp": 500, "max_hp": 500},
            "boss": {"hp": 1500, "max_hp": 1500},
            "turn": 1,
            "battle_log": []
        }
        
        # Test boss turn processing
        updated_battle = await boss_system.process_boss_turn(battle_data)
        
        # Verify turn increased
        assert updated_battle["turn"] == 2
        
        # Verify battle log has entries
        assert len(updated_battle["battle_log"]) > 0
        
        # Verify boss regeneration
        assert updated_battle["boss"]["hp"] > 1500  # Should have regenerated
        
    @pytest.mark.asyncio
    async def test_process_player_attack(self, boss_system, sample_character_data):
        """Test processing player attack."""
        mock_interaction = AsyncMock()
        mock_interaction.followup.send = AsyncMock()
        
        # Initialize battle
        user_id = str(sample_character_data["id"])
        battle_data = {
            "user_id": user_id,
            "character": sample_character_data.copy(),
            "boss": boss_system.boss_data.copy(),
            "turn": 1,
            "battle_log": []
        }
        boss_system.active_boss_battles[user_id] = battle_data
        
        # Test successful attack
        result = await boss_system.process_player_attack(mock_interaction, "Katon: Gōka Messhitsu")
        assert result == True
        
        # Verify boss took damage
        updated_battle = boss_system.active_boss_battles[user_id]
        assert updated_battle["boss"]["hp"] < 1500
        
        # Test unknown jutsu
        result = await boss_system.process_player_attack(mock_interaction, "Unknown Jutsu")
        assert result == False
        mock_interaction.followup.send.assert_called_with("❌ You don't know the jutsu **Unknown Jutsu**!")
        
    @pytest.mark.asyncio
    async def test_end_boss_battle_victory(self, boss_system, sample_character_data):
        """Test ending battle with victory."""
        mock_interaction = AsyncMock()
        mock_interaction.followup.send = AsyncMock()
        
        battle_data = {
            "user_id": str(sample_character_data["id"]),
            "character": sample_character_data.copy(),
            "boss": {"hp": 0, "max_hp": 1500},  # Boss defeated
            "turn": 5,
            "battle_log": ["Final attack!"]
        }
        
        await boss_system.end_boss_battle(mock_interaction, battle_data, "victory")
        
        # Verify victory message
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args[0][0]
        assert "VICTORY AGAINST SOLOMON" in call_args.title
        assert "10000 EXP" in call_args.description
        
    @pytest.mark.asyncio
    async def test_end_boss_battle_defeat(self, boss_system, sample_character_data):
        """Test ending battle with defeat."""
        mock_interaction = AsyncMock()
        mock_interaction.followup.send = AsyncMock()
        
        battle_data = {
            "user_id": str(sample_character_data["id"]),
            "character": {"hp": 0, "max_hp": 500},  # Player defeated
            "boss": {"hp": 1000, "max_hp": 1500},
            "turn": 5,
            "battle_log": ["Final attack!"]
        }
        
        await boss_system.end_boss_battle(mock_interaction, battle_data, "defeat")
        
        # Verify defeat message
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args[0][0]
        assert "DEFEATED BY SOLOMON" in call_args.title
        
    @pytest.mark.asyncio
    async def test_boss_commands_setup(self, mock_bot):
        """Test boss commands cog setup."""
        await BossBattleCommands.setup(mock_bot)
        mock_bot.add_cog.assert_called_once()
        
    def test_boss_phases_progression(self, boss_system):
        """Test boss phase progression based on HP."""
        # Test all phase thresholds
        phases = boss_system.boss_data["boss_phases"]
        
        # 100% HP - Phase 1
        phase = boss_system.get_current_phase(1.0)
        assert phase == phases[0]
        
        # 75% HP - Phase 1
        phase = boss_system.get_current_phase(0.75)
        assert phase == phases[0]
        
        # 65% HP - Phase 2
        phase = boss_system.get_current_phase(0.65)
        assert phase == phases[1]
        
    def test_boss_damage_scaling(self, boss_system):
        """Test boss damage scaling across phases."""
        jutsu = "Katon: Gōka Messhitsu"
        base_damage = 80
        
        # Phase 1: 1.0x multiplier
        phase1 = {"name": "Phase 1: The Crimson Shadow"}
        damage1 = boss_system.calculate_boss_damage(jutsu, phase1)
        assert damage1 == base_damage
        
        # Phase 2: 1.3x multiplier
        phase2 = {"name": "Phase 2: The Burning Revenant"}
        damage2 = boss_system.calculate_boss_damage(jutsu, phase2)
        assert damage2 == int(base_damage * 1.3)
        
        # Phase 3: 1.6x multiplier
        phase3 = {"name": "Phase 3: The Exiled Flame"}
        damage3 = boss_system.calculate_boss_damage(jutsu, phase3)
        assert damage3 == int(base_damage * 1.6)
        
        # Phase 4: 2.0x multiplier
        phase4 = {"name": "Phase 4: The Ultimate Being"}
        damage4 = boss_system.calculate_boss_damage(jutsu, phase4)
        assert damage4 == int(base_damage * 2.0)
        
    def test_boss_requirements_validation(self, boss_system):
        """Test comprehensive boss requirements validation."""
        # Valid character
        valid_char = {
            "id": "123",
            "level": 60,
            "achievements": ["Master of Elements", "Battle Hardened"]
        }
        can_battle, message = boss_system.check_boss_requirements(valid_char)
        assert can_battle == True
        
        # Invalid level
        invalid_level = valid_char.copy()
        invalid_level["level"] = 30
        can_battle, message = boss_system.check_boss_requirements(invalid_level)
        assert can_battle == False
        assert "level 50" in message
        
        # Missing achievements
        missing_achievements = valid_char.copy()
        missing_achievements["achievements"] = ["Master of Elements"]  # Missing "Battle Hardened"
        can_battle, message = boss_system.check_boss_requirements(missing_achievements)
        assert can_battle == False
        assert "Battle Hardened" in message
        
        # No achievements
        no_achievements = valid_char.copy()
        no_achievements["achievements"] = []
        can_battle, message = boss_system.check_boss_requirements(no_achievements)
        assert can_battle == False
        assert "Master of Elements" in message

if __name__ == "__main__":
    pytest.main([__file__]) 