# HCshinobi Game Bot

This project implements a Discord bot for a hardcore Naruto-themed MMO game concept.
It focuses on clan assignments, token management, and NPC interactions.

## Features

*   **Clan Assignment:** Players can roll for clan assignments based on weighted rarities.
    *   Personality traits influence clan probabilities.
    *   Tokens can be used to boost chances for specific clans or reroll assignments.
*   **Token System:** Players earn and spend tokens for various benefits.
*   **NPC System:** Players marked as dead are converted into NPCs, preserving their legacy.
*   **Discord Integration:** Slash commands for easy interaction.
*   **AI Integration:** Placeholder for generating NPC background stories, quests, etc.
*   **Logging:** Structured logging for events, errors, and commands.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd HCshinobi
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create a `.env` file** in the `HCshinobi` root directory with your bot token and guild ID:
    ```dotenv
    DISCORD_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
    DISCORD_GUILD_ID=YOUR_SERVER_ID_HERE 
    ```
    *Replace `YOUR_BOT_TOKEN_HERE` with your actual Discord bot token.*
    *Replace `YOUR_SERVER_ID_HERE` with the ID of your Discord server (guild). This is recommended for faster command syncing during development.*

4.  **Run the bot:**
    ```bash
    python HCshinobi/main.py
    ```

## Project Structure

```
HCshinobi/
├── ai/                  # AI integration modules
│   ├── npc_prompt_generator.py
│   └── __init__.py
├── core/                # Core game logic modules
│   ├── assignment_engine.py
│   ├── clan_data.py
│   ├── npc_manager.py
│   ├── personality_modifiers.py
│   ├── token_system.py
│   └── __init__.py
├── data/                # Data files (JSON)
│   ├── assignment_history.json
│   ├── clans.json
│   ├── npcs.json
│   ├── personality_modifiers.json
│   ├── player_tokens.json
│   └── token_transactions.json
├── discord/             # Discord integration modules
│   ├── announcements.py
│   ├── bot_commands.py
│   ├── rolling.py
│   └── __init__.py
├── logs/                # Log files
│   ├── events/
│   ├── errors.json
│   └── game.log
├── utils/               # Utility modules
│   ├── logging.py
│   └── __init__.py
├── __init__.py
├── main.py              # Bot entry point
├── README.md
└── requirements.txt
```

## Usage

Interact with the bot using slash commands in Discord:

*   `/roll_clan`: Roll for your clan assignment.
*   `/clan_info [clan_name]`: Get information about a specific clan.
*   `/clan_list`: List all available clans.
*   `/my_clan`: Check your current clan assignment.
*   `/tokens`: Check your token balance.
*   `/add_tokens [user] [amount]` (Admin): Add tokens to a user.
*   `/unlock_feature [feature]` : Unlock a feature using tokens.
*   `/mark_death [user] [clan] [death_story]` (Admin): Mark a player as dead.
*   `/npc_list [clan]` : List NPCs.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request. 