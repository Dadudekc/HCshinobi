# HCShinobi Product Requirements Document

## Overview
HCShinobi is a hardcore Naruto-themed MMO Discord bot. It aims to provide clan assignment, training, missions, and an interactive battle system. Players progress by earning currency and tokens, training attributes, and completing AI-generated missions. The bot integrates with Discord using slash commands and is designed for modularity so features can evolve over time.

**New in v2.0:**
- Fully unified D20-based battle system (dice mechanics, modifiers, criticals)
- Modernized jutsu, progression, and mission logic (single source of truth)
- Dynamic battle logs and error handling for transparency

## Goals
1. Offer engaging RPG mechanics in a Discord server.
2. Allow players to create shinobi characters, join clans, and battle each other.
3. Provide progression through missions, training, and currency systems.
4. Support AI-driven content generation for quests and character narratives.
5. Log activities for transparency and debugging.
6. Deliver a robust, extensible D20 battle experience.

## Core Features
- **Character Creation**: Players create characters and store profiles.
- **Clan Assignment**: Weighted rolls with personality modifiers and optional token boosts.
- **Token Economy**: Earn and spend tokens to reroll clans or unlock effects.
- **Currency System**: Manage ryo for purchases, shops, and mission rewards.
- **Training System**: Improve attributes through timed training sessions.
- **Mission Board**: List available missions, accept missions, and track progress.
- **Interactive Battle System (D20 Engine)**:
    - True D20 dice mechanics for all actions (attacks, jutsu, saving throws)
    - Stat-based modifiers (ninjutsu, taijutsu, genjutsu, etc.)
    - Critical hits, misses, and saving throws
    - Unified jutsu system: all jutsu, requirements, and effects in one database
    - Progression engine: automatic jutsu unlocks, rank advancement
    - Dynamic battle logs with templates (no hardcoded messages)
    - HP bars, chakra, and status effects
    - Boss battles, PvP, and mission encounters all use the same D20 logic
- **NPC System**: Fallen players become NPCs for missions or battles.
- **AI Integration**: Generate quests, NPC backgrounds, and narrative events.
- **Logging**: Structured logging for monitoring and audit trails.
- **Error Handling**: Global and per-command error reporting with user feedback and logs.

## Non-Goals
- Creating a full graphical client outside Discord.
- Real-money transactions.

## Users & Personas
- **Casual Players** who want quick battles and missions.
- **Hardcore RPG Fans** interested in progression and clan systems.
- **Server Administrators** managing events and monitoring logs.

## Technical Requirements
- Discord.py 2.5+ for slash commands.
- Python 3.8+.
- Data stored in JSON files for the MVP; future database support considered.
- Modular service container for injecting systems (character, currency, tokens, etc.).
- Unified D20 battle/jutsu/mission engine (modular, extensible).
- Test suite using `pytest` with >90% coverage goal (see `tests/README.md`).

## Future Considerations
- Persistent database for character and battle history.
- AI-generated story arcs using external LLM services.
- Web dashboard for admins.
- Extensible D20 logic (custom dice, homebrew rules, analytics).
