#!/usr/bin/env python3
"""
Manual Command Testing Checklist for HCShinobi Bot
Use this to systematically test commands in Discord
"""

def print_testing_checklist():
    """Print a comprehensive testing checklist"""
    
    print("🧪 HCSHINOBI BOT - MANUAL COMMAND TESTING CHECKLIST")
    print("=" * 60)
    print("Copy and paste these commands into Discord to test:")
    print()
    
    # Character Commands
    print("🥷 CHARACTER COMMANDS:")
    print("  /help                    - Show all commands")
    print("  /create                  - Create character (test permadeath logic)")
    print("  /profile                 - View character profile")
    print("  /delete_character        - Delete character (CAREFUL!)")
    print()
    
    # Economy Commands  
    print("💰 ECONOMY COMMANDS:")
    print("  /balance                 - Check currency")
    print("  /balance @user           - Check other user's balance") 
    print("  /transfer @user 100      - Transfer currency")
    print("  /daily                   - Claim daily reward")
    print("  /tokens                  - Check token balance")
    print("  /earn_tokens             - Earn tokens")
    print("  /spend_tokens            - Spend tokens")
    print()
    
    # Combat Commands
    print("⚔️ COMBAT COMMANDS:")
    print("  /challenge @user         - Challenge another player")
    print("  /battle_status           - Check active battles")
    print("  /solomon                 - Ultimate boss battle")
    print("  /battle_npc Victor       - Fight NPC bosses")
    print("  /npc_list                - List available NPCs")
    print()
    
    # Training Commands
    print("🏃‍♂️ TRAINING COMMANDS:")
    print("  /train strength          - Train specific attribute")
    print("  /training_status         - Check training progress")
    print("  /complete_training       - Complete training session")
    print("  /cancel_training         - Cancel training")
    print("  /training_info           - Training information")
    print()
    
    # Mission Commands
    print("🎯 MISSION COMMANDS:")
    print("  /mission_board           - View available missions")
    print("  /shinobios_mission       - Start ShinobiOS mission")
    print("  /battle_action fireball enemy1 - Mission battle action")
    print("  /clan_mission_board      - Clan-specific missions")
    print("  /clan_mission_accept     - Accept clan mission")
    print()
    
    # Clan Commands
    print("🏛️ CLAN COMMANDS:")
    print("  /my_clan                 - Your current clan")
    print("  /clan_list               - Browse all clans")
    print("  /join_clan Uchiha        - Join specific clan")
    print("  /create_clan             - Create new clan")
    print("  /roll_clan               - Roll for random clan")
    print()
    
    # Shop Commands
    print("🛒 SHOP COMMANDS:")
    print("  /shop                    - Browse shop items")
    print("  /buy kunai               - Purchase item")
    print("  /item_info kunai         - Get item details")
    print()
    
    # Utility Commands
    print("🎮 UTILITY & INFO COMMANDS:")
    print("  /jutsu                   - Browse jutsu collection") 
    print("  /achievements            - View achievements")
    print("  /jutsu_shop              - Browse jutsu for purchase")
    print("  /announce                - Make announcement (admin)")
    print("  /battle_announce         - Battle announcement (admin)")
    print()
    
    print("=" * 60)
    print("🎯 TESTING STRATEGY:")
    print("1. Start with /help to verify it shows all commands")
    print("2. Test /create to make a character")
    print("3. Test /profile to view character")
    print("4. Test /balance and /daily for economy")
    print("5. Test /clan_list and /roll_clan for clans")
    print("6. Test combat with /solomon or /battle_npc")
    print("7. Test /train for progression")
    print("8. Test missions with /mission_board")
    print()
    print("⚠️  IMPORTANT:")
    print("- Test permadeath: /create should block if character alive")
    print("- Test 404 errors are just timeouts (normal)")
    print("- Test all 56 commands appear in Discord's / menu")
    print()
    print("📋 Record results and any errors found!")

def create_test_scenarios():
    """Create specific test scenarios"""
    
    print("\n" + "=" * 60)
    print("🧪 SPECIFIC TEST SCENARIOS:")
    print("=" * 60)
    
    scenarios = [
        {
            "name": "New User Journey",
            "steps": [
                "1. /help - See command overview",
                "2. /create - Create first character", 
                "3. /profile - View new character",
                "4. /roll_clan - Get a clan",
                "5. /balance - Check starting currency",
                "6. /daily - Claim daily reward",
                "7. /train strength - Start training"
            ]
        },
        {
            "name": "Permadeath Testing", 
            "steps": [
                "1. /create - Should work if no character",
                "2. /create - Should BLOCK with permadeath message",
                "3. /delete_character - Manually delete",
                "4. /create - Should work again after deletion"
            ]
        },
        {
            "name": "Combat System",
            "steps": [
                "1. /npc_list - See available NPCs",
                "2. /battle_npc Victor - Start NPC battle",
                "3. /battle_status - Check battle state",
                "4. /solomon - Try ultimate boss (might fail - OK)"
            ]
        },
        {
            "name": "Economy System",
            "steps": [
                "1. /balance - Check currency",
                "2. /tokens - Check token balance", 
                "3. /daily - Claim daily (100 ryo)",
                "4. /shop - Browse items",
                "5. /transfer @friend 50 - Test transfers"
            ]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🎯 SCENARIO {i}: {scenario['name']}")
        for step in scenario['steps']:
            print(f"   {step}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    print_testing_checklist()
    create_test_scenarios() 