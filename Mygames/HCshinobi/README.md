# HCShinobi Dream Modules

This project extracts the core functionality from the HCShinobi Discord bot into modular, reusable components that can be easily integrated into other projects.

## Project Structure

```
dream_modules/
├── core/
│   ├── module_interface.py - Base interfaces for modules
│   └── service_container.py - Dependency injection container
├── modules/
│   ├── character/
│   │   ├── character_model.py - Character data model
│   │   └── character_manager.py - Character management service
│   ├── clan/
│   │   ├── clan_model.py - Clan data model
│   │   └── clan_manager.py - Clan management service
│   └── discord/
│       └── character_commands.py - Discord commands for character management
├── __init__.py - Package exports
├── factory.py - Factory functions for creating modules
├── example_bot.py - Example Discord bot implementation
└── README.md - Module documentation
```

## Features

- **Modular Design**: Each component is designed to be independent and reusable.
- **Dependency Injection**: Using a service container for managing dependencies.
- **OOP Principles**: Clean interfaces and proper encapsulation.
- **Discord Integration**: Ready-to-use Discord commands for character management.
- **Extensible**: Easy to extend with new features and customizations.

## Getting Started

1. Copy the `dream_modules` directory to your project.
2. Import the modules you need:

```python
# Import the factory functions
from dream_modules.factory import setup_rpg_systems

# Create and configure the modules
systems = setup_rpg_systems(bot, config)
```

3. See the example bot (`dream_modules/example_bot.py`) for a complete implementation.

## Usage

### Basic Example

```python
import discord
from discord.ext import commands
from dream_modules.factory import setup_rpg_systems, shutdown_all_systems

# Create bot
bot = commands.Bot(command_prefix='!', intents=discord.Intents.default())

# Configuration
config = {
    "character": {
        "data_dir": "data/characters",
    },
    "clan": {
        "data_dir": "data/clans",
    },
    "commands": {
        "role_management": {
            "enabled": True,
        }
    }
}

@bot.event
async def on_ready():
    # Set up RPG systems
    systems = setup_rpg_systems(bot, config)
    await bot.tree.sync()

# Run bot
bot.run("YOUR_TOKEN_HERE")
```

### Accessing Services

You can access the services using the service container:

```python
from dream_modules.core.service_container import get_container

# Get the character manager service
character_manager = get_container().get("character_manager")

# Get a character
character = character_manager.get_character("user_id")
```

## Documentation

For detailed documentation on each module, see the README file in the `dream_modules` directory.

## Integration with Dream.OS

These modules are designed to be compatible with Dream.OS. To integrate them:

1. Copy the `dream_modules` directory to your Dream.OS project.
2. Register the services with the Dream.OS service container.
3. Use the factory functions to create and configure the modules.

## License

This project is licensed under the MIT License. 