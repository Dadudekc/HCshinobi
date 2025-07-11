"""
E2E Test for NPC Battle Mechanics System
Tests all special abilities, phases, and unique mechanics for each NPC boss.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from typing import Dict, Any

# Import the battle system
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.boss_battle_system import BossBattleSystem
from commands.boss_commands import BossCommands


class TestNPCBattleMechanics:
    """Test NPC battle mechanics and special abilities."""
    
    @pytest.fixture
    def battle_system(self):
        """Create a battle system instance for testing."""
        mock_bot = MagicMock()
        return BossBattleSystem(mock_bot)
    
    @pytest.fixture
    def mock_interaction(self):
        """Create a mock Discord interaction."""
        interaction = AsyncMock(spec=discord.Interaction)
        interaction.user.id = 123456789
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()
        return interaction
    
    @pytest.fixture
    def test_character(self):
        """Create a test character with various jutsu."""
        return {
            "name": "Test Ninja",
            "level": 60,
            "hp": 1000,
            "max_hp": 1000,
            "chakra": 500,
            "max_chakra": 500,
            "exp": 5000,
            "ryo": 1000,
            "jutsu": [
                "Rasengan",
                "Shadow Clone Jutsu", 
                "Fireball Jutsu",
                "Lightning Blade",
                "Earth Wall Jutsu"
            ],
            "stats": {
                "strength": 80,
                "speed": 75,
                "intelligence": 70,
                "chakra_control": 85
            }
        }
    
    @pytest.mark.asyncio
    async def test_victor_lightning_mechanics(self, battle_system, mock_interaction, test_character):
        """Test Victor's lightning storm mechanics."""
        # Mock NPC data loading
        with patch.object(battle_system, 'load_npc_data') as mock_load_npc:
            # Mock Victor's data
            mock_load_npc.return_value = {
                "name": "Victor",
                "level": 60,
                "hp": 800,
                "max_hp": 800,
                "jutsu": ["Raiton: Chidori", "Raiton: Lightning Blade"],
                "boss_requirements": {"min_level": 50}
            }
            
            # Start battle
            success = await battle_system.start_npc_battle(mock_interaction, test_character, "Victor")
            assert success is True
            
            # Check battle data
            battle_data = battle_system.active_boss_battles[str(mock_interaction.user.id)]
            assert battle_data["npc_name"] == "Victor"
            assert "special_mechanics" in battle_data
            
            # Test speed boost mechanics
            battle_data["turn"] = 3
            battle_data = battle_system.apply_npc_mechanics(battle_data, {})
            
            # Check that speed boost was applied
            log_entries = [entry for entry in battle_data["battle_log"] if "speed increases" in entry.lower()]
            assert len(log_entries) > 0
            
            # Test phase progression
            boss = battle_data["boss"]
            boss["hp"] = int(boss["max_hp"] * 0.6)  # 60% HP - should be Phase 3
            
            phase = battle_system.get_npc_current_phase(boss["hp"] / boss["max_hp"], battle_data["special_mechanics"])
            assert "Thunder God" in phase.get("name", "")  # Phase 3
            
            # Test damage calculation
            damage = battle_system.calculate_npc_damage("Raiton: Lightning Storm", phase, boss)
            assert damage > 0
            
            # Cleanup
            del battle_system.active_boss_battles[str(mock_interaction.user.id)]
    
    @pytest.mark.asyncio
    async def test_trunka_barrier_mechanics(self, battle_system, mock_interaction, test_character):
        """Test Trunka's barrier mastery mechanics."""
        with patch.object(battle_system, 'load_npc_data') as mock_load_npc:
            mock_load_npc.return_value = {
                "name": "Trunka",
                "level": 65,
                "hp": 1000,
                "max_hp": 1000,
                "jutsu": ["Protection Barrier Jutsu"],
                "boss_requirements": {"min_level": 55}
            }
            
            # Start battle
            success = await battle_system.start_npc_battle(mock_interaction, test_character, "Trunka")
            assert success is True
            
            battle_data = battle_system.active_boss_battles[str(mock_interaction.user.id)]
            
            # Test barrier mechanics
            battle_data = battle_system.apply_npc_mechanics(battle_data, {})
            
            # Check barrier HP was set
            assert "barrier_hp" in battle_data
            assert battle_data["barrier_hp"] == 200
            
            # Check barrier log entry
            log_entries = [entry for entry in battle_data["battle_log"] if "barrier" in entry.lower()]
            assert len(log_entries) > 0
            
            # Test phase progression
            boss = battle_data["boss"]
            boss["hp"] = int(boss["max_hp"] * 0.2)  # 20% HP - should be Phase 3
            
            phase = battle_system.get_npc_current_phase(boss["hp"] / boss["max_hp"], battle_data["special_mechanics"])
            assert "Absolute Defense" in phase.get("name", "")
            
            # Cleanup
            del battle_system.active_boss_battles[str(mock_interaction.user.id)]
    
    @pytest.mark.asyncio
    async def test_chen_shadow_mechanics(self, battle_system, mock_interaction, test_character):
        """Test Chen's shadow tactics mechanics."""
        with patch.object(battle_system, 'load_npc_data') as mock_load_npc:
            mock_load_npc.return_value = {
                "name": "Chen",
                "level": 55,
                "hp": 700,
                "max_hp": 700,
                "jutsu": ["Shadow Possession Jutsu"],
                "boss_requirements": {"min_level": 45}
            }
            
            # Start battle
            success = await battle_system.start_npc_battle(mock_interaction, test_character, "Chen")
            assert success is True
            
            battle_data = battle_system.active_boss_battles[str(mock_interaction.user.id)]
            
            # Test shadow restriction mechanics
            battle_data = battle_system.apply_npc_mechanics(battle_data, {})
            
            # Check restricted jutsu was set
            assert "restricted_jutsu" in battle_data
            assert battle_data["restricted_jutsu"] in test_character["jutsu"]
            
            # Check restriction log entry
            log_entries = [entry for entry in battle_data["battle_log"] if "restricts" in entry.lower()]
            assert len(log_entries) > 0
            
            # Test phase progression
            boss = battle_data["boss"]
            boss["hp"] = int(boss["max_hp"] * 0.1)  # 10% HP - should be Phase 3
            
            phase = battle_system.get_npc_current_phase(boss["hp"] / boss["max_hp"], battle_data["special_mechanics"])
            assert "Shadow Mastery" in phase.get("name", "")
            
            # Cleanup
            del battle_system.active_boss_battles[str(mock_interaction.user.id)]
    
    @pytest.mark.asyncio
    async def test_cap_byakugan_mechanics(self, battle_system, mock_interaction, test_character):
        """Test Cap's Byakugan precision mechanics."""
        with patch.object(battle_system, 'load_npc_data') as mock_load_npc:
            mock_load_npc.return_value = {
                "name": "Cap",
                "level": 50,
                "hp": 600,
                "max_hp": 600,
                "jutsu": ["Gentle Fist: Eight Trigrams Sixty-Four Palms"],
                "boss_requirements": {"min_level": 40}
            }
            
            # Start battle
            success = await battle_system.start_npc_battle(mock_interaction, test_character, "Cap")
            assert success is True
            
            battle_data = battle_system.active_boss_battles[str(mock_interaction.user.id)]
            
            # Test chakra point targeting (30% chance)
            # We'll test multiple times to ensure it triggers
            disabled_found = False
            for _ in range(10):
                test_battle_data = battle_data.copy()
                test_battle_data["battle_log"] = []
                test_battle_data = battle_system.apply_npc_mechanics(test_battle_data, {})
                
                if "disabled_jutsu" in test_battle_data:
                    disabled_found = True
                    assert test_battle_data["disabled_jutsu"] in test_character["jutsu"]
                    break
            
            # Test phase progression
            boss = battle_data["boss"]
            boss["hp"] = int(boss["max_hp"] * 0.5)  # 50% HP - should be Phase 3
            
            phase = battle_system.get_npc_current_phase(boss["hp"] / boss["max_hp"], battle_data["special_mechanics"])
            assert "Ultimate Defense" in phase.get("name", "")  # Phase 3
            
            # Cleanup
            del battle_system.active_boss_battles[str(mock_interaction.user.id)]
    
    @pytest.mark.asyncio
    async def test_chris_sealing_mechanics(self, battle_system, mock_interaction, test_character):
        """Test Chris's sealing mastery mechanics."""
        with patch.object(battle_system, 'load_npc_data') as mock_load_npc:
            mock_load_npc.return_value = {
                "name": "Chris",
                "level": 45,
                "hp": 500,
                "max_hp": 500,
                "jutsu": ["Four Symbols Seal"],
                "boss_requirements": {"min_level": 35}
            }
            
            # Start battle
            success = await battle_system.start_npc_battle(mock_interaction, test_character, "Chris")
            assert success is True
            
            battle_data = battle_system.active_boss_battles[str(mock_interaction.user.id)]
            
            # Test sealing mechanics (25% chance)
            sealed_found = False
            for _ in range(10):
                test_battle_data = battle_data.copy()
                test_battle_data["battle_log"] = []
                test_battle_data = battle_system.apply_npc_mechanics(test_battle_data, {})
                
                if "sealed_ability" in test_battle_data:
                    sealed_found = True
                    assert test_battle_data["sealed_ability"] in ["chakra", "jutsu", "movement"]
                    break
            
            # Test phase progression
            boss = battle_data["boss"]
            boss["hp"] = int(boss["max_hp"] * 0.1)  # 10% HP - should be Phase 3
            
            phase = battle_system.get_npc_current_phase(boss["hp"] / boss["max_hp"], battle_data["special_mechanics"])
            assert "Ultimate Sealing" in phase.get("name", "")
            
            # Cleanup
            del battle_system.active_boss_battles[str(mock_interaction.user.id)]
    
    @pytest.mark.asyncio
    async def test_npc_damage_calculation(self, battle_system):
        """Test NPC damage calculation with different phases."""
        # Test Victor's jutsu damage
        phase1 = {"name": "Phase 1: Thunder Initiation"}
        phase2 = {"name": "Phase 2: Lightning Fury"}
        phase3 = {"name": "Phase 3: Thunder God"}
        
        boss = {"level": 60, "hp": 800, "max_hp": 800}
        
        # Test damage scaling with phases
        damage1 = battle_system.calculate_npc_damage("Raiton: Chidori", phase1, boss)
        damage2 = battle_system.calculate_npc_damage("Raiton: Lightning Storm", phase2, boss)
        damage3 = battle_system.calculate_npc_damage("Raiton: Lightning Burst", phase3, boss)
        
        assert damage1 > 0
        assert damage2 > damage1  # Phase 2 should do more damage
        assert damage3 > damage2  # Phase 3 should do the most damage
    
    @pytest.mark.asyncio
    async def test_npc_jutsu_selection(self, battle_system):
        """Test NPC jutsu selection from phase pools."""
        phase = {
            "jutsu_pool": ["Jutsu A", "Jutsu B", "Jutsu C"]
        }
        
        # Test multiple selections to ensure randomness
        jutsu_selections = []
        for _ in range(10):
            jutsu = battle_system.get_npc_jutsu(phase)
            jutsu_selections.append(jutsu)
            assert jutsu in phase["jutsu_pool"]
        
        # Should have some variety (not always the same jutsu)
        assert len(set(jutsu_selections)) > 1
    
    @pytest.mark.asyncio
    async def test_npc_battle_embed_creation(self, battle_system, test_character):
        """Test NPC battle embed creation."""
        boss = {
            "name": "Victor",
            "level": 60,
            "hp": 800,
            "max_hp": 800
        }
        
        battle_data = {
            "character": test_character,
            "boss": boss,
            "turn": 1,
            "battle_log": ["Test log entry"],
            "special_mechanics": {
                "name": "Lightning Storm",
                "description": "Victor's speed increases with each turn"
            }
        }
        
        # Test battle start embed
        embed = battle_system.create_npc_battle_embed(battle_data, "battle_start")
        assert embed.title == "⚔️ BATTLE STARTED: VICTOR"
        assert "Victor's speed increases with each turn" in embed.description
        
        # Test battle turn embed
        embed = battle_system.create_npc_battle_embed(battle_data, "battle_turn")
        assert "BATTLE TURN 1" in embed.title
    
    @pytest.mark.asyncio
    async def test_npc_phase_transitions(self, battle_system):
        """Test NPC phase transitions based on HP percentage."""
        mechanics = {
            "phases": [
                {"name": "Phase 1", "hp_threshold": 1.0},
                {"name": "Phase 2", "hp_threshold": 0.7},
                {"name": "Phase 3", "hp_threshold": 0.3}
            ]
        }
        
        # Test different HP percentages
        assert battle_system.get_npc_current_phase(1.0, mechanics)["name"] == "Phase 1"
        assert battle_system.get_npc_current_phase(0.8, mechanics)["name"] == "Phase 2"  # 0.8 is Phase 2
        assert battle_system.get_npc_current_phase(0.7, mechanics)["name"] == "Phase 2"
        assert battle_system.get_npc_current_phase(0.5, mechanics)["name"] == "Phase 3"  # 0.5 is Phase 3
        assert battle_system.get_npc_current_phase(0.3, mechanics)["name"] == "Phase 3"
        assert battle_system.get_npc_current_phase(0.1, mechanics)["name"] == "Phase 3"
    
    @pytest.mark.asyncio
    async def test_npc_battle_commands_integration(self, battle_system, mock_interaction, test_character):
        """Test integration with boss battle commands."""
        commands = BossCommands(None)  # Pass None as bot parameter
        commands.battle_system = battle_system
        commands.active_boss_battles = battle_system.active_boss_battles  # Fix: share state
        # Patch start_npc_battle to use the battle_system's method
        commands.start_npc_battle = battle_system.start_npc_battle
        
        # Mock character loading on the command class
        with patch.object(commands, 'load_character_data', return_value=test_character):
            with patch.object(battle_system, 'load_npc_data') as mock_load_npc:
                mock_load_npc.return_value = {
                    "name": "Victor",
                    "level": 60,
                    "hp": 800,
                    "max_hp": 800,
                    "jutsu": ["Raiton: Chidori"],
                    "boss_requirements": {"min_level": 50}
                }
                
                # Test battle_npc command (call .callback)
                await commands.battle_npc.callback(commands, mock_interaction, "Victor")
                
                # Check that battle was started
                assert str(mock_interaction.user.id) in battle_system.active_boss_battles
                
                # Test npc_list command (call .callback)
                await commands.npc_list.callback(commands, mock_interaction)
                
                # Verify embed was sent
                mock_interaction.followup.send.assert_called()
                
                # Cleanup
                del battle_system.active_boss_battles[str(mock_interaction.user.id)]


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"]) 