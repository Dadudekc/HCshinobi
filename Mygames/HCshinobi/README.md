# HCShinobi

HCShinobi is a hardcore Naruto-themed MMO Discord bot, featuring clan assignments, token economy, NPC management, AI-driven content, and reusable RPG modules.

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