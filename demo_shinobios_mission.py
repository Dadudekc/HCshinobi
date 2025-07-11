"""
ShinobiOS Mission System Live Demonstration
Shows how the immersive battle system works
"""

import asyncio
import json
import random
from datetime import timedelta

from core.missions.shinobios_engine import ShinobiOSEngine
from core.missions.shinobios_mission import ShinobiOSMission, BattleMissionType
from core.missions.mission import MissionDifficulty

async def demo_shinobios_mission():
    """Demonstrate a live ShinobiOS mission"""
    
    print("🌅 SHINOBIOS MISSION SYSTEM DEMONSTRATION")
    print("=" * 50)
    
    # Initialize the engine
    engine = ShinobiOSEngine()
    
    # Create a test character
    print("\n👤 Creating Test Character...")
    character_data = {
        "user_id": "demo_user_123",
        "name": "Kakashi Hatake",
        "level": 15,
        "stats": {
            "ninjutsu": 75,
            "taijutsu": 70,
            "genjutsu": 65,
            "intelligence": 80,
            "speed": 75,
            "strength": 65,
            "defense": 70,
            "chakra_control": 85,
            "elemental_affinity": "lightning"
        }
    }
    
    # Create mission
    print("📋 Creating Mission...")
    mission = ShinobiOSMission(
        engine=engine,
        id="demo_mission_001",
        title="Forest Ambush",
        description="A dangerous mission in the dense forest where enemies lurk in the shadows",
        difficulty=MissionDifficulty.B_RANK,
        village="Konoha",
        reward={"experience": 200, "currency": 100, "special_item": "Forest Scroll"},
        duration=timedelta(hours=3)
    )
    
    # Initialize battle
    print("⚔️ Initializing Battle...")
    players = [character_data]
    mission.initialize_battle(players, "forest")
    
    # Display initial status
    print("\n🎯 MISSION STATUS:")
    print(f"Mission: {mission.title}")
    print(f"Difficulty: {mission.difficulty}")
    print(f"Environment: {mission.battle_state.environment.name}")
    print(f"Objectives: {', '.join(mission.battle_state.objectives)}")
    
    # Show participants
    print("\n👥 BATTLE PARTICIPANTS:")
    for participant in mission.battle_state.participants:
        status = "🟢 PLAYER" if participant.is_player else "🔴 ENEMY"
        print(f"{status} {participant.name} - HP: {participant.stats.health}/{participant.stats.max_health} | Chakra: {participant.stats.chakra}/{participant.stats.max_chakra}")
    
    # Show available jutsu
    print("\n📜 AVAILABLE JUTSU:")
    player = mission.battle_state.get_players()[0]
    available_jutsu = engine.get_available_jutsu(player.stats)
    for jutsu in available_jutsu:
        print(f"🔥 {jutsu.name} - Cost: {jutsu.chakra_cost} | Damage: {jutsu.damage} | Element: {jutsu.element}")
    
    # Start battle simulation
    print("\n⚔️ BATTLE COMMENCES!")
    print("=" * 50)
    
    turn = 1
    max_turns = 10
    
    while turn <= max_turns and mission.battle_state.get_players() and mission.battle_state.get_enemies():
        print(f"\n🔄 TURN {turn}")
        print("-" * 30)
        
        # Player turn
        if mission.battle_state.get_players():
            player = mission.battle_state.get_players()[0]
            enemies = mission.battle_state.get_enemies()
            
            if enemies:
                # Choose a jutsu
                jutsu = random.choice(available_jutsu)
                target = random.choice(enemies)
                
                print(f"🎯 {player.name} uses {jutsu.name} on {target.name}!")
                
                # Execute player action
                result = await mission.execute_player_action(
                    player.user_id, 
                    jutsu.name, 
                    target.user_id
                )
                
                if result["success"]:
                    action = result["action"]
                    print(f"   {action['narration']}")
                    print(f"   Damage: {action['damage']} | Success: {'✅' if action['success'] else '❌'}")
                    
                    if target.stats.health <= 0:
                        print(f"   💀 {target.name} has been defeated!")
                else:
                    print(f"   ❌ Action failed: {result.get('error', 'Unknown error')}")
        
        # Enemy turn
        print("\n👹 ENEMY TURN:")
        enemy_actions = await mission.execute_enemy_turn()
        
        for action in enemy_actions:
            print(f"   {action['narration']}")
            print(f"   Damage: {action['damage']} | Success: {'✅' if action['success'] else '❌'}")
        
        # Show current status
        print(f"\n📊 STATUS UPDATE:")
        for participant in mission.battle_state.participants:
            if participant.status == "active":
                status = "🟢" if participant.is_player else "🔴"
                print(f"   {status} {participant.name}: HP {participant.stats.health}/{participant.stats.max_health} | Chakra {participant.stats.chakra}/{participant.stats.max_chakra}")
        
        # Check completion
        completion = mission._check_mission_completion()
        if completion["completed"]:
            print(f"\n🏁 MISSION {completion['status'].upper()}!")
            print(f"   Reason: {completion['reason']}")
            break
        
        turn += 1
    
    # Final status
    print("\n" + "=" * 50)
    print("🏁 MISSION COMPLETE")
    print("=" * 50)
    
    final_status = mission.get_battle_status()
    print(f"Final Turn: {final_status['current_turn']}")
    print(f"Total Actions: {len(final_status['recent_actions'])}")
    
    if mission.battle_state.get_players():
        print("🎉 Mission Success! Player survived!")
    else:
        print("💀 Mission Failed! Player was defeated!")
    
    print("\n📜 BATTLE LOG (Last 5 Actions):")
    for action in final_status['recent_actions'][-5:]:
        print(f"   Turn {action['turn']}: {action['actor']} → {action['target']} ({action['jutsu']}) - {action['damage']} damage")

if __name__ == "__main__":
    asyncio.run(demo_shinobios_mission()) 