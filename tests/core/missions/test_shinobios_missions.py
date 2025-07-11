"""
Tests for ShinobiOS Mission System
Comprehensive testing of battle simulation and mission mechanics
"""

import pytest
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from HCshinobi.core.missions.shinobios_engine import (
    ShinobiOSEngine, ShinobiStats, Jutsu, BattleAction, EnvironmentEffect
)
from HCshinobi.core.missions.shinobios_mission import (
    ShinobiOSMission, BattleParticipant, BattleState, BattleMissionType
)
from HCshinobi.core.missions.mission import MissionDifficulty

class TestShinobiOSEngine:
    """Test the core ShinobiOS battle engine"""
    
    def setup_method(self):
        self.engine = ShinobiOSEngine()
    
    def test_engine_initialization(self):
        """Test engine initializes with all components"""
        assert self.engine.environments
        assert self.engine.jutsu_database
        assert self.engine.narration_templates
        
        # Check environments loaded
        assert "forest" in self.engine.environments
        assert "desert" in self.engine.environments
        assert "mountain" in self.engine.environments
        
        # Check jutsu loaded
        assert "fireball" in self.engine.jutsu_database
        assert "shadow_clone" in self.engine.jutsu_database
        assert "rasengan" in self.engine.jutsu_database
    
    def test_create_shinobi(self):
        """Test shinobi creation with stats"""
        shinobi = self.engine.create_shinobi("Test Shinobi", level=10)
        assert hasattr(shinobi, "name")
        assert shinobi.name == "Test Shinobi"
        assert shinobi.level == 10
        assert shinobi.max_chakra == 190  # 100 + (10-1) * 10
        assert shinobi.max_health == 235  # 100 + (10-1) * 15
        assert shinobi.chakra == shinobi.max_chakra
        assert shinobi.health == shinobi.max_health
    
    def test_shinobi_stats_operations(self):
        """Test shinobi stat operations"""
        shinobi = self.engine.create_shinobi("Test", level=1)
        
        # Test chakra usage
        assert shinobi.use_chakra(50)
        assert shinobi.chakra == 50
        assert not shinobi.use_chakra(100)  # Insufficient chakra
        assert shinobi.chakra == 50
        
        # Test damage
        damage_dealt = shinobi.take_damage(30)
        assert damage_dealt > 0
        assert shinobi.health < shinobi.max_health
        
        # Test healing
        original_health = shinobi.health
        shinobi.heal(20)
        assert shinobi.health > original_health
        
        # Test chakra regeneration
        shinobi.regenerate_chakra(25)
        assert shinobi.chakra > 50
    
    def test_jutsu_execution(self):
        """Test jutsu execution mechanics"""
        attacker = self.engine.create_shinobi("Attacker", level=10)
        target = self.engine.create_shinobi("Target", level=10)
        environment = self.engine.environments["forest"]
        jutsu = self.engine.jutsu_database["fireball"]
        
        action = self.engine.execute_action(attacker, target, jutsu, environment)
        
        assert isinstance(action, BattleAction)
        assert action.actor == "Attacker"
        assert action.target == "Target"
        assert action.jutsu == jutsu
        assert action.chakra_used == jutsu.chakra_cost
        assert attacker.chakra < attacker.max_chakra
    
    def test_environment_effects(self):
        """Test environment effects on battle"""
        attacker = self.engine.create_shinobi("Attacker", level=10)
        target = self.engine.create_shinobi("Target", level=10)
        jutsu = self.engine.jutsu_database["fireball"]
        
        # Test forest environment
        forest_env = self.engine.environments["forest"]
        forest_action = self.engine.execute_action(attacker, target, jutsu, forest_env)
        
        # Test volcanic environment (should do more damage)
        volcanic_env = self.engine.environments["volcanic"]
        volcanic_action = self.engine.execute_action(attacker, target, jutsu, volcanic_env)
        
        # Volcanic should generally do more damage due to damage modifier
        assert volcanic_action.damage >= forest_action.damage
        
        # Test chakra regeneration effect: reduce chakra, then regen
        attacker.chakra = max(0, attacker.chakra - 10)
        before = attacker.chakra
        self.engine.regenerate_stats(attacker, forest_env)
        assert attacker.chakra > before
    
    def test_available_jutsu_by_level(self):
        """Test jutsu availability based on level"""
        level_1_shinobi = self.engine.create_shinobi("Level 1", level=1)
        level_20_shinobi = self.engine.create_shinobi("Level 20", level=20)
        
        level_1_jutsu = self.engine.get_available_jutsu(level_1_shinobi)
        level_20_jutsu = self.engine.get_available_jutsu(level_20_shinobi)
        
        # Higher level should have more jutsu
        assert len(level_20_jutsu) > len(level_1_jutsu)
        
        # Level 20 should have rasengan
        rasengan_names = [j.name for j in level_20_jutsu if "rasengan" in j.name.lower()]
        assert len(rasengan_names) > 0
        
        # Level 1 should not have rasengan
        rasengan_names = [j.name for j in level_1_jutsu if "rasengan" in j.name.lower()]
        assert len(rasengan_names) == 0
    
    def test_mission_scenario_creation(self):
        """Test mission scenario creation"""
        # Test D-rank scenario
        d_scenario = self.engine.create_mission_scenario("D", "forest")
        assert len(d_scenario["enemies"]) == 1
        assert d_scenario["enemies"][0].level == 5
        
        # Test S-rank scenario
        s_scenario = self.engine.create_mission_scenario("S", "volcanic")
        assert len(s_scenario["enemies"]) == 3
        assert s_scenario["enemies"][0].level == 40
        
        # Check objectives
        assert len(d_scenario["objectives"]) > 0
        assert len(s_scenario["objectives"]) > 0

class TestShinobiOSMission:
    """Test ShinobiOS mission functionality"""
    
    def setup_method(self):
        self.engine = ShinobiOSEngine()
        self.mission = ShinobiOSMission(
            engine=self.engine,
            id="test_mission",
            title="Test Mission",
            description="A test mission",
            difficulty=MissionDifficulty.C_RANK,
            village="Konoha",
            reward={"experience": 100, "currency": 50},
            duration=timedelta(hours=1)
        )
    
    def test_mission_initialization(self):
        """Test mission initialization"""
        assert self.mission.engine == self.engine
        assert self.mission.battle_id
        assert self.mission.mission_type == BattleMissionType.ELIMINATION
        assert self.mission.battle_state is None
    
    def test_battle_initialization(self):
        """Test battle initialization"""
        players = [{
            "user_id": "123",
            "name": "Test Player",
            "level": 10,
            "stats": {"ninjutsu": 60}
        }]
        
        self.mission.initialize_battle(players, "forest")
        
        assert self.mission.battle_state is not None
        assert len(self.mission.battle_state.get_players()) == 1
        assert len(self.mission.battle_state.get_enemies()) > 0
        assert self.mission.battle_state.environment is not None
        assert len(self.mission.battle_state.objectives) > 0
    
    @pytest.mark.asyncio
    async def test_player_action_execution(self):
        """Test player action execution"""
        # Initialize battle
        players = [{
            "user_id": "123",
            "name": "Test Player",
            "level": 10
        }]
        self.mission.initialize_battle(players, "forest")
        
        # Get enemy target
        enemies = self.mission.battle_state.get_enemies()
        target_id = enemies[0].user_id
        
        # Execute action
        result = await self.mission.execute_player_action("123", "Fireball Jutsu", target_id)
        
        assert result["success"]
        assert "action" in result
        assert "battle_state" in result
        assert "completion_status" in result
        
        # Check battle log was updated
        assert len(self.mission.battle_state.battle_log) > 0
    
    @pytest.mark.asyncio
    async def test_enemy_turn_execution(self):
        """Test enemy turn execution"""
        # Initialize battle
        players = [{
            "user_id": "123",
            "name": "Test Player",
            "level": 10
        }]
        self.mission.initialize_battle(players, "forest")
        
        # Execute enemy turn
        actions = await self.mission.execute_enemy_turn()
        
        assert isinstance(actions, list)
        # Should have actions if enemies are alive
        if self.mission.battle_state.get_enemies():
            assert len(actions) > 0
    
    def test_mission_completion_check(self):
        """Test mission completion checking"""
        # Initialize battle
        players = [{
            "user_id": "123",
            "name": "Test Player",
            "level": 10
        }]
        self.mission.initialize_battle(players, "forest")
        
        # Check initial status
        completion = self.mission._check_mission_completion()
        assert not completion["completed"]
        assert completion["status"] == "in_progress"
        
        # Simulate all enemies defeated
        for enemy in self.mission.battle_state.get_enemies():
            enemy.status = "defeated"
        
        completion = self.mission._check_mission_completion()
        assert completion["completed"]
        assert completion["status"] == "success"
        
        # Simulate all players defeated
        for player in self.mission.battle_state.get_players():
            player.status = "defeated"
        
        completion = self.mission._check_mission_completion()
        assert completion["completed"]
        assert completion["status"] == "failed"
    
    def test_battle_status_retrieval(self):
        """Test battle status retrieval"""
        # Initialize battle
        players = [{
            "user_id": "123",
            "name": "Test Player",
            "level": 10
        }]
        self.mission.initialize_battle(players, "forest")
        
        status = self.mission.get_battle_status()
        
        assert "battle_id" in status
        assert "mission_id" in status
        assert "current_turn" in status
        assert "participants" in status
        assert "objectives" in status
        assert "environment" in status
    
    def test_mission_serialization(self):
        """Test mission serialization and deserialization"""
        # Initialize battle
        players = [{
            "user_id": "123",
            "name": "Test Player",
            "level": 10
        }]
        self.mission.initialize_battle(players, "forest")
        
        # Serialize
        mission_dict = self.mission.to_dict()
        
        # Deserialize
        new_mission = ShinobiOSMission.from_dict(mission_dict, self.engine)
        
        assert new_mission.id == self.mission.id
        assert new_mission.title == self.mission.title
        assert new_mission.battle_id == self.mission.battle_id
        assert new_mission.battle_state is not None

class TestBattleParticipant:
    """Test battle participant functionality"""
    
    def setup_method(self):
        self.engine = ShinobiOSEngine()
        self.stats = self.engine.create_shinobi("Test", level=10)
    
    def test_participant_creation(self):
        """Test participant creation"""
        participant = BattleParticipant(
            user_id="123",
            name="Test Participant",
            stats=self.stats,
            is_player=True
        )
        
        assert participant.user_id == "123"
        assert participant.name == "Test Participant"
        assert participant.stats == self.stats
        assert participant.is_player
        assert participant.status == "active"
    
    def test_participant_serialization(self):
        """Test participant serialization"""
        participant = BattleParticipant(
            user_id="123",
            name="Test Participant",
            stats=self.stats,
            is_player=True
        )
        
        # Serialize
        participant_dict = participant.to_dict()
        
        # Deserialize
        new_participant = BattleParticipant.from_dict(participant_dict, self.engine)
        
        assert new_participant.user_id == participant.user_id
        assert new_participant.name == participant.name
        assert new_participant.is_player == participant.is_player
        assert new_participant.status == participant.status

class TestBattleState:
    """Test battle state functionality"""
    
    def setup_method(self):
        self.engine = ShinobiOSEngine()
        self.battle_state = BattleState()
    
    def test_participant_management(self):
        """Test participant management"""
        stats = self.engine.create_shinobi("Test", level=10)
        participant = BattleParticipant("123", "Test", stats, True)
        
        self.battle_state.add_participant(participant)
        
        assert len(self.battle_state.participants) == 1
        assert len(self.battle_state.get_active_participants()) == 1
        assert len(self.battle_state.get_players()) == 1
        assert len(self.battle_state.get_enemies()) == 0
    
    def test_battle_log_management(self):
        """Test battle log management"""
        jutsu = self.engine.jutsu_database["fireball"]
        action = BattleAction(
            actor="Test Actor",
            target="Test Target",
            jutsu=jutsu,
            success=True,
            damage=30,
            chakra_used=30,
            effects=["burn_chance"],
            narration="Test narration",
            timestamp=datetime.now()
        )
        
        self.battle_state.add_battle_log(action)
        
        assert len(self.battle_state.battle_log) == 1
        assert self.battle_state.battle_log[0]["actor"] == "Test Actor"
        assert self.battle_state.battle_log[0]["jutsu"] == "Fireball Jutsu"
    
    def test_battle_state_serialization(self):
        """Test battle state serialization"""
        # Add participant
        stats = self.engine.create_shinobi("Test", level=10)
        participant = BattleParticipant("123", "Test", stats, True)
        self.battle_state.add_participant(participant)
        
        # Add environment
        self.battle_state.environment = self.engine.environments["forest"]
        
        # Add objectives
        self.battle_state.objectives = ["Defeat enemies", "Survive"]
        
        # Serialize
        state_dict = self.battle_state.to_dict()
        
        # Deserialize
        new_state = BattleState.from_dict(state_dict, self.engine)
        
        assert len(new_state.participants) == len(self.battle_state.participants)
        if new_state.environment and self.battle_state.environment:
            assert new_state.environment.name == self.battle_state.environment.name
        assert new_state.objectives == self.battle_state.objectives

class TestIntegration:
    """Integration tests for the complete ShinobiOS system"""
    
    def setup_method(self):
        self.engine = ShinobiOSEngine()
    
    @pytest.mark.asyncio
    async def test_complete_battle_flow(self):
        """Test a complete battle flow from start to finish"""
        # Create mission
        mission = ShinobiOSMission(
            engine=self.engine,
            id="integration_test",
            title="Integration Test Mission",
            description="Test complete battle flow",
            difficulty=MissionDifficulty.D_RANK,
            village="Konoha",
            reward={"experience": 100, "currency": 50},
            duration=timedelta(hours=1)
        )
        
        # Initialize battle
        players = [{
            "user_id": "123",
            "name": "Test Player",
            "level": 15
        }]
        mission.initialize_battle(players, "forest")
        
        # Verify initial state
        assert len(mission.battle_state.get_players()) == 1
        assert len(mission.battle_state.get_enemies()) == 1
        
        # Execute player action
        enemies = mission.battle_state.get_enemies()
        target_id = enemies[0].user_id
        
        result = await mission.execute_player_action("123", "Fireball Jutsu", target_id)
        assert result["success"]
        
        # Execute enemy turn
        enemy_actions = await mission.execute_enemy_turn()
        assert isinstance(enemy_actions, list)
        
        # Check battle state
        status = mission.get_battle_status()
        assert status["current_turn"] > 0
        assert len(status["recent_actions"]) > 0
    
    def test_environment_effect_integration(self):
        """Test environment effects in battle"""
        # Create shinobi
        shinobi = self.engine.create_shinobi("Test", level=10)
        # Test different environments
        environments = ["forest", "desert", "volcanic"]
        for env_name in environments:
            env = self.engine.environments[env_name]
            shinobi.chakra = max(0, shinobi.chakra - 10)
            original_chakra = shinobi.chakra
            self.engine.regenerate_stats(shinobi, env)
            assert shinobi.chakra > original_chakra
    
    def test_jutsu_progression_integration(self):
        """Test jutsu progression with level"""
        # Test different levels
        for level in [1, 10, 20, 30]:
            shinobi = self.engine.create_shinobi("Test", level=level)
            jutsu_list = self.engine.get_available_jutsu(shinobi)
            
            # Higher levels should have more jutsu
            if level > 1:
                assert len(jutsu_list) >= 4  # At least basic jutsu
            
            # Check for level-specific jutsu
            jutsu_names = [j.name.lower() for j in jutsu_list]
            
            if level >= 20:
                assert any("rasengan" in name for name in jutsu_names)
            if level >= 30:
                assert any("amaterasu" in name for name in jutsu_names)

if __name__ == "__main__":
    pytest.main([__file__]) 