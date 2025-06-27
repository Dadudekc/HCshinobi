# HCShinobi Product Requirements Document

## Overview
HCShinobi is a hardcore Naruto-themed MMO Discord bot. It aims to provide clan assignment, training, missions, and an interactive battle system. Players progress by earning currency and tokens, training attributes, and completing AI-generated missions. The bot integrates with Discord using slash commands and is designed for modularity so features can evolve over time.

## Goals
1. Offer engaging RPG mechanics in a Discord server.
2. Allow players to create shinobi characters, join clans, and battle each other.
3. Provide progression through missions, training, and currency systems.
4. Support AI-driven content generation for quests and character narratives.
5. Log activities for transparency and debugging.

## Core Features
- **Character Creation**: Players create characters and store profiles.
- **Clan Assignment**: Weighted rolls with personality modifiers and optional token boosts.
- **Token Economy**: Earn and spend tokens to reroll clans or unlock effects.
- **Currency System**: Manage ryo for purchases, shops, and mission rewards.
- **Training System**: Improve attributes through timed training sessions.
- **Mission Board**: List available missions, accept missions, and track progress.
- **Interactive Battle System**: Turn-based battles with jutsu, HP bars, and status effects.
- **NPC System**: Fallen players become NPCs for missions or battles.
- **AI Integration**: Generate quests, NPC backgrounds, and narrative events.
- **Logging**: Structured logging for monitoring and audit trails.

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
- Test suite using `pytest` with >90% coverage goal (see `tests/README.md`).

## Future Considerations
- Persistent database for character and battle history.
- AI-generated story arcs using external LLM services.
- Web dashboard for admins.
