"""
End-to-End Test for Solomon Boss Battle System
Tests the complete battle flow including permadeath mechanics.
"""
import pytest
import json
import tempfile
import os
import random
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

# Import the boss battle system
import sys
sys.path.append('..')
from commands.boss_commands import BossCommands

class TestSolomonBossBattleE2E:
    """End-to-end test cases for Solomon boss battle system."""
    
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
    def mock_bot(self):
        """Mock bot for testing."""
        bot = MagicMock()
        bot.add_cog = AsyncMock()
        return bot
        
    @pytest.fixture
    def boss_commands(self, mock_bot):
        """Boss commands instance for testing."""
        return BossCommands(mock_bot)
        
    @pytest.fixture
    def mock_interaction(self):
        """Mock Discord interaction for testing."""
        interaction = AsyncMock()
        interaction.user.id = 123456789
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        return interaction
        
    def create_temp_character_file(self, character_data):
        """Create a temporary character file for testing."""
        temp_dir = tempfile.mkdtemp()
        character_file = os.path.join(temp_dir, "data", "characters", f"{character_data['id']}.json")
        os.makedirs(os.path.dirname(character_file), exist_ok=True)
        
        with open(character_file, 'w', encoding='utf-8') as f:
            json.dump(character_data, f, indent=4, ensure_ascii=False)
            
        return temp_dir, character_file
        
    @pytest.mark.asyncio
    async def test_solomon_info_command(self, boss_commands, mock_interaction):
        """Test the /solomon info command."""
        await boss_commands.show_solomon_info(mock_interaction)
        
        # Verify followup was sent
        mock_interaction.followup.send.assert_called_once()
        
        # Verify embed was created - check both positional and keyword arguments
        call_args = mock_interaction.followup.send.call_args
        if call_args[0]:  # Positional arguments
            embed = call_args[0][0]
        else:  # Keyword arguments
            embed = call_args[1]['embed']
            
        assert "SOLOMON - THE BURNING REVENANT" in embed.title
        assert "The Ultimate Being" in embed.description
        
        # Verify stats are included
        assert "**Level:** 70" in str(embed.fields)
        assert "**HP:** 1500/1500" in str(embed.fields)
        
    @pytest.mark.asyncio
    async def test_solomon_challenge_insufficient_level(self, boss_commands, mock_interaction):
        """Test challenging Solomon with insufficient level."""
        # Create character with low level
        low_level_character = {
            "id": "123456789",
            "name": "Weak Shinobi",
            "level": 30,  # Below required level 50
            "hp": 300,
            "max_hp": 300,
            "chakra": 200,
            "max_chakra": 200,
            "stamina": 150,
            "max_stamina": 150,
            "ninjutsu": 50,
            "jutsu": ["Katon: Gōka Messhitsu"],
            "achievements": ["Master of Elements", "Battle Hardened"],
            "titles": ["Genin"]
        }
        
        await boss_commands.start_solomon_battle(mock_interaction, low_level_character)
        
        # Verify error message
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        if call_args[0]:  # Positional arguments
            embed = call_args[0][0]
        else:  # Keyword arguments
            embed = call_args[1]['embed']
        assert "INSUFFICIENT POWER" in embed.title
        assert "level 50" in embed.description
        
    @pytest.mark.asyncio
    async def test_solomon_challenge_missing_achievements(self, boss_commands, mock_interaction):
        """Test challenging Solomon with missing achievements."""
        # Create character with missing achievements
        character_no_achievements = {
            "id": "123456789",
            "name": "Unworthy Shinobi",
            "level": 55,
            "hp": 500,
            "max_hp": 500,
            "chakra": 300,
            "max_chakra": 300,
            "stamina": 200,
            "max_stamina": 200,
            "ninjutsu": 80,
            "jutsu": ["Katon: Gōka Messhitsu"],
            "achievements": [],  # Missing required achievements
            "titles": ["Genin"]
        }
        
        await boss_commands.start_solomon_battle(mock_interaction, character_no_achievements)
        
        # Verify error message
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        if call_args[0]:  # Positional arguments
            embed = call_args[0][0]
        else:  # Keyword arguments
            embed = call_args[1]['embed']
        assert "INSUFFICIENT POWER" in embed.title
        assert "Master of Elements" in embed.description
        
    @pytest.mark.asyncio
    async def test_solomon_challenge_success(self, boss_commands, mock_interaction, sample_character_data):
        """Test successfully challenging Solomon."""
        await boss_commands.start_solomon_battle(mock_interaction, sample_character_data)
        
        # Verify battle was started
        mock_interaction.followup.send.assert_called_once()
        call_args = mock_interaction.followup.send.call_args
        if call_args[0]:  # Positional arguments
            embed = call_args[0][0]
        else:  # Keyword arguments
            embed = call_args[1]['embed']
        assert "SOLOMON - THE BURNING REVENANT" in embed.title
        assert "The Ultimate Being has appeared" in embed.description
        
        # Verify battle file was created
        battle_file = f"data/battles/solomon_{mock_interaction.user.id}.json"
        assert os.path.exists(battle_file)
        
        # Clean up
        if os.path.exists(battle_file):
            os.remove(battle_file)
            
    @pytest.mark.asyncio
    async def test_solomon_attack_success(self, boss_commands, mock_interaction, sample_character_data):
        """Test successful attack against Solomon."""
        # Create battle file
        battle_data = {
            "user_id": mock_interaction.user.id,
            "character": sample_character_data.copy(),
            "boss": {
                "id": "solomon",
                "name": "Solomon - The Burning Revenant",
                "hp": 1500,
                "max_hp": 1500,
                "level": 70
            },
            "turn": 1,
            "battle_log": []
        }
        
        battle_file = f"data/battles/solomon_{mock_interaction.user.id}.json"
        os.makedirs(os.path.dirname(battle_file), exist_ok=True)
        with open(battle_file, 'w', encoding='utf-8') as f:
            json.dump(battle_data, f, indent=4, ensure_ascii=False)
            
        try:
            await boss_commands.attack_solomon(mock_interaction, sample_character_data, "Katon: Gōka Messhitsu")
            
            # Verify attack was processed
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            if call_args[0]:  # Positional arguments
                embed = call_args[0][0]
            else:  # Keyword arguments
                embed = call_args[1]['embed']
            assert "BATTLE TURN" in embed.title
            
            # Verify battle file was updated
            with open(battle_file, 'r', encoding='utf-8') as f:
                updated_battle = json.load(f)
            assert updated_battle["turn"] > 1
            assert len(updated_battle["battle_log"]) > 0
            
        finally:
            # Clean up
            if os.path.exists(battle_file):
                os.remove(battle_file)
                
    @pytest.mark.asyncio
    async def test_solomon_attack_unknown_jutsu(self, boss_commands, mock_interaction, sample_character_data):
        """Test attacking with unknown jutsu."""
        # Create battle file first
        battle_data = {
            "user_id": mock_interaction.user.id,
            "character": sample_character_data.copy(),
            "boss": {
                "id": "solomon",
                "name": "Solomon - The Burning Revenant",
                "hp": 1200,
                "max_hp": 1500,
                "level": 70
            },
            "turn": 1,
            "battle_log": []
        }
        
        battle_file = f"data/battles/solomon_{mock_interaction.user.id}.json"
        os.makedirs(os.path.dirname(battle_file), exist_ok=True)
        with open(battle_file, 'w', encoding='utf-8') as f:
            json.dump(battle_data, f, indent=4, ensure_ascii=False)
            
        try:
            await boss_commands.attack_solomon(mock_interaction, sample_character_data, "Unknown Jutsu")

            # Verify error message
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            if call_args[0]:  # Positional arguments
                message = call_args[0][0]
            else:  # Keyword arguments
                message = call_args[1].get('content', '')
            assert "You don't know the jutsu" in message
            
        finally:
            # Clean up
            if os.path.exists(battle_file):
                os.remove(battle_file)
        
    @pytest.mark.asyncio
    async def test_solomon_attack_no_battle(self, boss_commands, mock_interaction, sample_character_data):
        """Test attacking when not in battle."""
        await boss_commands.attack_solomon(mock_interaction, sample_character_data, "Katon: Gōka Messhitsu")
        
        # Verify error message
        mock_interaction.followup.send.assert_called_once()
        assert "not in a battle" in mock_interaction.followup.send.call_args[0][0]
        
    @pytest.mark.asyncio
    async def test_solomon_status_no_battle(self, boss_commands, mock_interaction, sample_character_data):
        """Test status command when not in battle."""
        await boss_commands.show_battle_status(mock_interaction, sample_character_data)
        
        # Verify error message
        mock_interaction.followup.send.assert_called_once()
        assert "not in a battle" in mock_interaction.followup.send.call_args[0][0]
        
    @pytest.mark.asyncio
    async def test_solomon_status_in_battle(self, boss_commands, mock_interaction, sample_character_data):
        """Test status command when in battle."""
        # Create battle file
        battle_data = {
            "user_id": mock_interaction.user.id,
            "character": sample_character_data.copy(),
            "boss": {
                "id": "solomon",
                "name": "Solomon - The Burning Revenant",
                "hp": 1200,
                "max_hp": 1500,
                "level": 70
            },
            "turn": 3,
            "battle_log": ["Test log entry"]
        }
        
        battle_file = f"data/battles/solomon_{mock_interaction.user.id}.json"
        os.makedirs(os.path.dirname(battle_file), exist_ok=True)
        with open(battle_file, 'w', encoding='utf-8') as f:
            json.dump(battle_data, f, indent=4, ensure_ascii=False)
            
        try:
            await boss_commands.show_battle_status(mock_interaction, sample_character_data)
            
            # Verify status was shown
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            if call_args[0]:  # Positional arguments
                embed = call_args[0][0]
            else:  # Keyword arguments
                embed = call_args[1]['embed']
            assert "BATTLE TURN 3" in embed.title
            
        finally:
            # Clean up
            if os.path.exists(battle_file):
                os.remove(battle_file)
                
    @pytest.mark.asyncio
    async def test_solomon_flee_no_battle(self, boss_commands, mock_interaction, sample_character_data):
        """Test flee command when not in battle."""
        await boss_commands.flee_from_battle(mock_interaction, sample_character_data)
        
        # Verify error message
        mock_interaction.followup.send.assert_called_once()
        assert "not in a battle" in mock_interaction.followup.send.call_args[0][0]
        
    @pytest.mark.asyncio
    async def test_solomon_flee_in_battle(self, boss_commands, mock_interaction, sample_character_data):
        """Test flee command when in battle."""
        # Create battle file
        battle_data = {
            "user_id": mock_interaction.user.id,
            "character": sample_character_data.copy(),
            "boss": {
                "id": "solomon",
                "name": "Solomon - The Burning Revenant",
                "hp": 1200,
                "max_hp": 1500,
                "level": 70
            },
            "turn": 3,
            "battle_log": ["Test log entry"]
        }
        
        battle_file = f"data/battles/solomon_{mock_interaction.user.id}.json"
        os.makedirs(os.path.dirname(battle_file), exist_ok=True)
        with open(battle_file, 'w', encoding='utf-8') as f:
            json.dump(battle_data, f, indent=4, ensure_ascii=False)
            
        try:
            await boss_commands.flee_from_battle(mock_interaction, sample_character_data)
            
            # Verify flee message
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            if call_args[0]:  # Positional arguments
                embed = call_args[0][0]
            else:  # Keyword arguments
                embed = call_args[1]['embed']
            assert "FLED FROM BATTLE" in embed.title
            assert "Cowardice will not save you forever" in embed.description
            
            # Verify battle file was removed
            assert not os.path.exists(battle_file)
            
        finally:
            # Clean up
            if os.path.exists(battle_file):
                os.remove(battle_file)
                
    @pytest.mark.asyncio
    async def test_complete_battle_flow_victory(self, boss_commands, mock_interaction, sample_character_data):
        """Test complete battle flow ending in victory."""
        # Start battle
        await boss_commands.start_solomon_battle(mock_interaction, sample_character_data)
        
        # Verify battle started
        mock_interaction.followup.send.assert_called()
        call_args = mock_interaction.followup.send.call_args
        if call_args[0]:  # Positional arguments
            embed = call_args[0][0]
        else:  # Keyword arguments
            embed = call_args[1]['embed']
        assert "SOLOMON - THE BURNING REVENANT" in embed.title
        
        # Create battle file with boss at very low HP to ensure defeat
        battle_data = {
            "user_id": mock_interaction.user.id,
            "character": sample_character_data.copy(),
            "boss": {
                "id": "solomon",
                "name": "Solomon - The Burning Revenant",
                "hp": 1,  # Almost defeated - ensure one hit kills
                "max_hp": 1500,
                "level": 70
            },
            "turn": 10,
            "battle_log": ["Final attack!"]
        }
        
        battle_file = f"data/battles/solomon_{mock_interaction.user.id}.json"
        os.makedirs(os.path.dirname(battle_file), exist_ok=True)
        with open(battle_file, 'w', encoding='utf-8') as f:
            json.dump(battle_data, f, indent=4, ensure_ascii=False)
            
        try:
            # Attack to defeat boss
            mock_interaction.followup.send.reset_mock()
            await boss_commands.attack_solomon(mock_interaction, sample_character_data, "Katon: Gōka Messhitsu")
            
            # Verify victory message
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            if call_args[0]:  # Positional arguments
                embed = call_args[0][0]
            else:  # Keyword arguments
                embed = call_args[1]['embed']
            assert "VICTORY AGAINST SOLOMON" in embed.title
            assert "10000 EXP" in embed.description
            
        finally:
            # Clean up
            if os.path.exists(battle_file):
                os.remove(battle_file)
                
    @pytest.mark.asyncio
    async def test_complete_battle_flow_defeat(self, boss_commands, mock_interaction, sample_character_data):
        """Test complete battle flow ending in defeat (permadeath)."""
        # Start battle
        await boss_commands.start_solomon_battle(mock_interaction, sample_character_data)
        
        # Create battle file with character at low HP
        battle_data = {
            "user_id": mock_interaction.user.id,
            "character": {
                **sample_character_data,
                "hp": 10  # Almost dead
            },
            "boss": {
                "id": "solomon",
                "name": "Solomon - The Burning Revenant",
                "hp": 1000,
                "max_hp": 1500,
                "level": 70
            },
            "turn": 10,
            "battle_log": ["Solomon's final attack!"]
        }
        
        battle_file = f"data/battles/solomon_{mock_interaction.user.id}.json"
        os.makedirs(os.path.dirname(battle_file), exist_ok=True)
        with open(battle_file, 'w', encoding='utf-8') as f:
            json.dump(battle_data, f, indent=4, ensure_ascii=False)
            
        try:
            # Attack to trigger Solomon's response (which will kill character)
            mock_interaction.followup.send.reset_mock()
            await boss_commands.attack_solomon(mock_interaction, sample_character_data, "Katon: Gōka Messhitsu")
            
            # Verify defeat message (permadeath)
            mock_interaction.followup.send.assert_called_once()
            call_args = mock_interaction.followup.send.call_args
            if call_args[0]:  # Positional arguments
                embed = call_args[0][0]
            else:  # Keyword arguments
                embed = call_args[1]['embed']
            assert "DEFEATED BY SOLOMON" in embed.title
            assert "not yet ready to face the ultimate being" in embed.description
            
        finally:
            # Clean up
            if os.path.exists(battle_file):
                os.remove(battle_file)
                
    def test_battle_phase_progression(self, boss_commands):
        """Test battle phase progression based on HP."""
        # Test all phase thresholds
        phases = [
            {"hp_threshold": 1.0, "name": "Phase 1: The Crimson Shadow"},
            {"hp_threshold": 0.7, "name": "Phase 2: The Burning Revenant"},
            {"hp_threshold": 0.4, "name": "Phase 3: The Exiled Flame"},
            {"hp_threshold": 0.1, "name": "Phase 4: The Ultimate Being"}
        ]
        # Test phase transitions (match actual logic: >= threshold)
        assert boss_commands.get_current_phase(1.0)["name"] == "Phase 1: The Crimson Shadow"  # >= 1.0
        assert boss_commands.get_current_phase(0.8)["name"] == "Phase 2: The Burning Revenant"  # >= 0.7
        assert boss_commands.get_current_phase(0.6)["name"] == "Phase 3: The Exiled Flame"  # >= 0.4
        assert boss_commands.get_current_phase(0.3)["name"] == "Phase 4: The Ultimate Being"  # >= 0.1
        assert boss_commands.get_current_phase(0.05)["name"] == "Phase 4: The Ultimate Being"  # >= 0.1
        
    def test_damage_calculation(self, boss_commands):
        """Test damage calculation across phases."""
        jutsu = "Katon: Gōka Messhitsu"
        base_damage = 80
        
        # Test phase multipliers
        phase1 = {"name": "Phase 1: The Crimson Shadow"}
        damage1 = boss_commands.calculate_boss_damage(jutsu, phase1)
        assert damage1 == base_damage
        
        phase2 = {"name": "Phase 2: The Burning Revenant"}
        damage2 = boss_commands.calculate_boss_damage(jutsu, phase2)
        assert damage2 == int(base_damage * 1.3)
        
        phase3 = {"name": "Phase 3: The Exiled Flame"}
        damage3 = boss_commands.calculate_boss_damage(jutsu, phase3)
        assert damage3 == int(base_damage * 1.6)
        
        phase4 = {"name": "Phase 4: The Ultimate Being"}
        damage4 = boss_commands.calculate_boss_damage(jutsu, phase4)
        assert damage4 == int(base_damage * 2.0)
        
    @pytest.mark.asyncio
    async def test_battle_embed_creation(self, boss_commands, sample_character_data):
        """Test battle embed creation for different scenarios."""
        battle_data = {
            "character": sample_character_data,
            "boss": {
                "id": "solomon",
                "name": "Solomon - The Burning Revenant",
                "hp": 1200,
                "max_hp": 1500,
                "level": 70
            },
            "turn": 5,
            "battle_log": ["Test log entry 1", "Test log entry 2"]
        }
        
        # Test battle start embed
        embed = boss_commands.create_battle_embed(battle_data, "battle_start")
        assert "SOLOMON - THE BURNING REVENANT" in embed.title
        assert "The Ultimate Being has appeared" in embed.description
        
        # Test battle turn embed
        embed = boss_commands.create_battle_embed(battle_data, "battle_turn")
        assert "BATTLE TURN 5" in embed.title
        
        # Verify character stats are included
        char_field = None
        for field in embed.fields:
            if "Test Shinobi" in field.name:
                char_field = field
                break
        assert char_field is not None
        assert "500/500" in char_field.value
        
        # Verify boss stats are included
        boss_field = None
        for field in embed.fields:
            if "SOLOMON" in field.name:
                boss_field = field
                break
        assert boss_field is not None
        assert "1200/1500" in boss_field.value

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 