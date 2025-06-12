import pytest
import inspect
from discord.ext import commands
from typing import List, Set, Dict, Any

def get_all_commands(bot: commands.Bot) -> Dict[str, commands.Command]:
    """Get all registered commands from the bot."""
    return {cmd.name: cmd for cmd in bot.commands}

def get_all_test_functions() -> Set[str]:
    """Get all test function names from the test files."""
    test_files = [
        'test_basic_commands.py',
        'test_mission_commands.py',
        'test_quest_commands.py',
        'test_clan_commands.py',
        'test_clan_mission_commands.py',
        'test_loot_commands.py',
        'test_room_commands.py',
        'test_devlog_commands.py',
        'test_announcement_commands.py'
    ]
    
    test_functions = set()
    for file in test_files:
        try:
            module = __import__(f'tests.commands.{file[:-3]}', fromlist=['*'])
            for name, obj in inspect.getmembers(module):
                if name.startswith('test_') and inspect.isfunction(obj):
                    # Convert test function name to command name
                    # e.g., test_mission_board_command -> mission_board
                    cmd_name = name.replace('test_', '').replace('_command', '')
                    test_functions.add(cmd_name)
        except ImportError:
            continue
    
    return test_functions

@pytest.mark.asyncio
async def test_command_coverage(bot):
    """Test that all registered commands have corresponding test functions."""
    # Get all registered commands
    all_commands = get_all_commands(bot)
    
    # Get all test functions
    test_functions = get_all_test_functions()
    
    # Find commands without tests
    untested_commands = set(all_commands.keys()) - test_functions
    
    # Assert that all commands have tests
    assert not untested_commands, (
        f"Found {len(untested_commands)} commands without tests:\n"
        f"{', '.join(sorted(untested_commands))}"
    )

@pytest.mark.asyncio
async def test_command_parameter_coverage(bot):
    """Test that all command parameters are properly tested."""
    all_commands = get_all_commands(bot)
    test_functions = get_all_test_functions()
    
    for cmd_name, cmd in all_commands.items():
        if cmd_name not in test_functions:
            continue
            
        # Get command parameters (excluding self and ctx)
        params = inspect.signature(cmd.callback).parameters
        required_params = {
            name for name, param in params.items()
            if name not in ('self', 'ctx') and param.default == inspect.Parameter.empty
        }
        
        # Get test function
        test_name = f"test_{cmd_name}_command"
        test_module = __import__(f'tests.commands.test_{cmd_name.split("_")[0]}_commands', fromlist=['*'])
        test_func = getattr(test_module, test_name, None)
        
        if test_func:
            # Check if test function calls command with all required parameters
            test_source = inspect.getsource(test_func)
            for param in required_params:
                assert param in test_source, (
                    f"Test for {cmd_name} is missing required parameter: {param}"
                ) 