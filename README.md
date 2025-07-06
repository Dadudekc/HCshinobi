# HCShinobi

HCShinobi is a hardcore Naruto-themed MMO Discord bot, featuring clan assignments, token economy, NPC management, AI-driven content, and reusable RPG modules. It is organized around a simple data pipeline so you can experiment with strategy logic and order execution.

## Features

- **Clan Assignment**: Weighted rolls with personality modifiers and token boosts.
- **Token System**: Earn and spend tokens to unlock effects or reroll.
- **NPC System**: Fallen players become NPCs with generated backgrounds.
- **AI Integration**: Hooks for generating quests and character narratives.
- **Discord Slash Commands**: Intuitive commands like `/roll_clan`, `/tokens`, and more.
- **Logging**: Configurable structured logging for operational visibility.
- **Reusable Modules**: Pluggable components for integrating RPG systems into other bots.

## Project Structure

```
.
├── HCshinobi/             # Main bot package
│   ├── ai/                # AI integration modules
│   ├── core/              # Game logic
│   ├── data/              # JSON data files
│   ├── discord/           # Discord command handlers
│   ├── utils/             # Utility functions
│   ├── main.py            # Bot entrypoint
│   └── README.md          # In-package documentation
├── scripts/               # Helper scripts (create_character, data fixes, etc.)
│   ├── create_character.py
│   └── fix_character_files.py
├── config/                # Configuration templates
├── tests/                 # Test suite
├── .env-example           # Environment variable sample
├── requirements.txt       # Core dependencies
├── requirements-test.txt  # Test dependencies
├── setup.py               # Package installation script
├── run.py                 # Launcher script
└── README.md              # This file
```

## Architecture Overview

The core loop flows through four stages:

1. **Data Feed** – gathers information from Discord events and game state.
2. **Signal Generation** – strategies analyze the data and decide on actions.
3. **Command Execution** – executes game actions such as starting missions or updating character stats.
4. **Logging** – records the outcome of each step for auditing.

Some modules (for example, the command execution engine and strategy definitions)
are still placeholders and will be implemented over time.

### Hard-coded Actions

During development you can define fixed actions directly inside a strategy. The
example below shows creating a character using the built-in system and printing
the result:

```python
from HCshinobi.core.character_system import CharacterSystem

system = CharacterSystem()
char = await system.create_character(user_id=123, name="Naruto", clan="Uzumaki")
print(char)
```

## Getting Started

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd <repo_root>
   ```
2. Create a virtual environment:
   - PowerShell: `fix_venv.ps1`
   - Command Prompt: `fix_venv.bat`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -e .
   ```
4. Configure environment variables:
   ```bash
   cp .env-example .env
   # Edit .env to set DISCORD_BOT_TOKEN, DISCORD_GUILD_ID, etc.
   ```
5. Run the bot:
   ```bash
   hcshinobi
   # or: python run.py
   ```

## Testing

Run all tests with:
```bash
pytest
```

## License

This project is licensed under the MIT License.
