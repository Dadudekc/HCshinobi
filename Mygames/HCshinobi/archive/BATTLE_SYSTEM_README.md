# Naruto Battle System

This extension adds a Naruto-themed battle system to the HCshinobi Discord bot, allowing players to engage in turn-based combat using jutsu from the Naruto universe.

## Features

- **Turn-Based Combat**: Players join the queue and take turns executing jutsu against opponents.
- **Element System**: Implements a Fire > Wind > Lightning > Earth > Water > Fire elemental advantage system.
- **Clan Integration**: Uses the existing clan system for character abilities.
- **Jutsu Database**: Pre-defined jutsu with different effects, costs, and elemental types.
- **Status Effects**: Jutsu can apply status effects that persist for several turns.
- **Custom Jutsu Creation**: Admins can create custom jutsu for special events.

## Setup & Integration

The battle system is implemented as a Discord.py Cog in the `discord/extensions/battle_system.py` file. It follows the project's dependency injection architecture, accessing required services through the bot instance.

### Integration with Existing Bot

The battle system has been designed to integrate seamlessly with your existing HCShinobiBot architecture:

1. **Dependency Injection**: The BattleCommands cog follows the same pattern as your other cogs, accepting services via the bot instance.
2. **Application Commands**: All commands have been implemented as slash commands using Discord's app_commands framework.
3. **Permission System**: Admin commands use the app_commands.default_permissions decorator for permission checks.

### Requirements

- discord.py >= 2.0.0
- message_content intent should be enabled in the Discord Developer Portal

## Commands

### User Commands

- `/join_battle` - Join the battle queue (before battle starts)
- `/use_jutsu [name] [target]` - Use a jutsu on a target during your turn
- `/battle_status` - View the current state of the battle and all combatants

### Admin Commands

- `/start_battle` - Start the battle with all joined players (admin only)
- `/reset_battle` - Reset the battle, allowing players to join again (admin only)
- `/create_jutsu [name] [rank] [cost] [effect] [duration] [element]` - Create a custom jutsu (admin only)

## Future Improvements

- Deeper integration with the ClanAssignmentEngine for clan-based abilities
- Persistent battle state storage (database integration)
- HP system instead of injury tracking
- More sophisticated effect application and interaction
- PvE battles against NPCs
- Advanced jutsu learning/progression system
- Battlefield hazards and environment effects

## Examples

### Starting a Battle

1. Players join: `/join_battle`
2. Admin starts: `/start_battle`  
3. Turn order is determined by initiative rolls
4. Each player uses `/use_jutsu [name] [target]` during their turn
5. Battle continues until one player remains

## Integration Notes

The cog currently uses temporary data for clans, elements, and jutsu. As development progresses, these should be integrated with your existing systems:

- Replace static clan_limits with data from your ClanData service
- Integrate with player character data to determine elements and available jutsu
- Potentially move jutsu_db to a persistent storage system or service
