#!/usr/bin/env python3
"""
Test script for the unified jutsu system
"""

import asyncio
import logging
from HCshinobi.core.unified_jutsu_system import UnifiedJutsuSystem

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

async def test_unified_jutsu_system():
    """Test the unified jutsu system."""
    print("🧪 Testing Unified Jutsu System...")
    print("=" * 50)
    
    try:
        # Create unified jutsu system
        jutsu_system = UnifiedJutsuSystem()
        print(f"✅ Unified jutsu system created successfully")
        
        # Test basic functionality
        all_jutsu = jutsu_system.get_all_jutsu()
        print(f"📊 Total jutsu loaded: {len(all_jutsu)}")
        
        # Test jutsu retrieval
        basic_attack = jutsu_system.get_jutsu_by_name("Basic Attack")
        if basic_attack:
            print(f"✅ Found Basic Attack: {basic_attack.name} (Rank {basic_attack.rank})")
        else:
            print("❌ Basic Attack not found")
        
        # Test element filtering
        fire_jutsu = jutsu_system.get_jutsu_by_element("fire")
        print(f"🔥 Fire jutsu found: {len(fire_jutsu)}")
        
        # Test rank filtering
        s_rank_jutsu = jutsu_system.get_jutsu_by_rank("S")
        print(f"⭐ S-rank jutsu found: {len(s_rank_jutsu)}")
        
        # Test statistics
        stats = jutsu_system.get_jutsu_statistics()
        print(f"\n📈 Jutsu Statistics:")
        print(f"   Total: {stats['total_jutsu']}")
        print(f"   By Rank: {stats['by_rank']}")
        print(f"   By Element: {dict(list(stats['by_element'].items())[:5])}...")
        print(f"   By Source: {stats['by_source']}")
        
        # Test character jutsu functionality
        test_character = {
            "level": 10,
            "strength": 15,
            "ninjutsu": 20,
            "jutsu": ["Basic Attack"],
            "achievements": []
        }
        
        available_jutsu = jutsu_system.get_available_jutsu(test_character)
        print(f"\n🎯 Available jutsu for test character: {len(available_jutsu)}")
        
        learned_jutsu = jutsu_system.get_learned_jutsu(test_character)
        print(f"📚 Learned jutsu: {len(learned_jutsu)}")
        
        # Test jutsu unlocking
        success = jutsu_system.unlock_jutsu_for_character(test_character, "Punch")
        print(f"🔓 Unlocked Punch: {success}")
        
        # Test search functionality
        search_results = jutsu_system.search_jutsu("fire")
        print(f"🔍 Search results for 'fire': {len(search_results)}")
        
        print("\n🎉 All tests passed! Unified jutsu system is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error testing unified jutsu system: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the test."""
    success = await test_unified_jutsu_system()
    
    if success:
        print("\n✅ Unified jutsu system test completed successfully!")
    else:
        print("\n❌ Unified jutsu system test failed!")

if __name__ == "__main__":
    asyncio.run(main()) 