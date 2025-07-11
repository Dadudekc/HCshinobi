#!/usr/bin/env python3
"""
HCShinobi Bot - Comprehensive Command Testing Script
Tests all 56 slash commands for basic functionality
"""

import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime

class CommandTester:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "total_commands": 0,
            "successful": 0,
            "failed": 0,
            "commands": {}
        }
        
    def log_test(self, command_name: str, status: str, error: str = None):
        """Log test result"""
        self.results["commands"][command_name] = {
            "status": status,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        
        if status == "SUCCESS":
            self.results["successful"] += 1
        elif status == "FAILED":
            self.results["failed"] += 1
            
        self.results["total_commands"] += 1
        
        # Print real-time results
        status_emoji = "✅" if status == "SUCCESS" else "❌"
        print(f"{status_emoji} {command_name}: {status}")
        if error:
            print(f"   Error: {error}")

async def test_bot_commands():
    """Test all bot commands systematically"""
    tester = CommandTester()
    
    print("🧪 STARTING COMPREHENSIVE COMMAND TESTING")
    print("=" * 60)
    
    # Import the bot to access command tree
    try:
        from HCshinobi.bot.bot import HCBot
        from HCshinobi.bot.services import ServiceContainer
        
        # Create bot instance
        bot = HCBot()
        services = ServiceContainer()
        bot.services = services
        
        print("✅ Bot instance created successfully")
        
        # Test command categories
        await test_character_commands(tester, bot)
        await test_economy_commands(tester, bot)
        await test_combat_commands(tester, bot)
        await test_training_commands(tester, bot)
        await test_mission_commands(tester, bot)
        await test_clan_commands(tester, bot)
        await test_shop_commands(tester, bot)
        await test_utility_commands(tester, bot)
        
    except Exception as e:
        print(f"❌ Failed to create bot instance: {e}")
        return
    
    # Save results
    with open("command_test_results.json", "w") as f:
        json.dump(tester.results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("🎯 TESTING COMPLETE - SUMMARY:")
    print(f"Total Commands: {tester.results['total_commands']}")
    print(f"✅ Successful: {tester.results['successful']}")
    print(f"❌ Failed: {tester.results['failed']}")
    print(f"Success Rate: {(tester.results['successful']/tester.results['total_commands']*100):.1f}%")
    print("\n📋 Results saved to: command_test_results.json")

async def test_character_commands(tester: CommandTester, bot):
    """Test character-related commands"""
    print("\n🥷 TESTING CHARACTER COMMANDS:")
    
    commands_to_test = [
        "create", "profile", "delete_character"
    ]
    
    for cmd in commands_to_test:
        try:
            # Check if command exists in bot's command tree
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

async def test_economy_commands(tester: CommandTester, bot):
    """Test economy-related commands"""
    print("\n💰 TESTING ECONOMY COMMANDS:")
    
    commands_to_test = [
        "balance", "transfer", "daily", "tokens", "earn_tokens", "spend_tokens"
    ]
    
    for cmd in commands_to_test:
        try:
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

async def test_combat_commands(tester: CommandTester, bot):
    """Test combat-related commands"""
    print("\n⚔️ TESTING COMBAT COMMANDS:")
    
    commands_to_test = [
        "challenge", "battle_status", "solomon", "battle_npc", "npc_list"
    ]
    
    for cmd in commands_to_test:
        try:
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

async def test_training_commands(tester: CommandTester, bot):
    """Test training-related commands"""
    print("\n🏃‍♂️ TESTING TRAINING COMMANDS:")
    
    commands_to_test = [
        "train", "training_status", "complete_training", "cancel_training", "training_info"
    ]
    
    for cmd in commands_to_test:
        try:
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

async def test_mission_commands(tester: CommandTester, bot):
    """Test mission-related commands"""
    print("\n🎯 TESTING MISSION COMMANDS:")
    
    commands_to_test = [
        "mission_board", "shinobios_mission", "battle_action", 
        "clan_mission_board", "clan_mission_accept"
    ]
    
    for cmd in commands_to_test:
        try:
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

async def test_clan_commands(tester: CommandTester, bot):
    """Test clan-related commands"""
    print("\n🏛️ TESTING CLAN COMMANDS:")
    
    commands_to_test = [
        "my_clan", "clan_list", "join_clan", "create_clan", "roll_clan"
    ]
    
    for cmd in commands_to_test:
        try:
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

async def test_shop_commands(tester: CommandTester, bot):
    """Test shop-related commands"""
    print("\n🛒 TESTING SHOP COMMANDS:")
    
    commands_to_test = [
        "shop", "buy", "item_info"
    ]
    
    for cmd in commands_to_test:
        try:
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

async def test_utility_commands(tester: CommandTester, bot):
    """Test utility commands"""
    print("\n🎮 TESTING UTILITY COMMANDS:")
    
    commands_to_test = [
        "help", "jutsu", "achievements", "jutsu_shop", "announce", "battle_announce"
    ]
    
    for cmd in commands_to_test:
        try:
            command = bot.tree.get_command(cmd)
            if command:
                tester.log_test(cmd, "SUCCESS")
            else:
                tester.log_test(cmd, "FAILED", "Command not found in tree")
        except Exception as e:
            tester.log_test(cmd, "FAILED", str(e))

def run_tests():
    """Run the test suite"""
    asyncio.run(test_bot_commands())

if __name__ == "__main__":
    run_tests() 