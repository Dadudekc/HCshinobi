# Announcement Update Rules

## Overview
This document defines the rules for updating the bot's announcement message when implementing new features or making changes.

## When to Update
The announcement message MUST be updated in the following cases:
1. When a new feature is implemented
2. When a feature moves from testing to official status
3. When a feature is removed or deprecated
4. When the bot's version number changes
5. When the bot's status or mode changes

## Feature Categories
Features must be categorized as:
- ✅ **Official Features**: Fully tested and stable features
- 🧪 **Testing Features**: Features in development/testing
- 🚧 **Coming Soon**: Planned features not yet implemented

## Required Information
The announcement message must include:
1. Bot status (Online/Offline)
2. Current version number
3. Development mode status
4. List of all available commands categorized by status
5. Clear indication of which features are official vs testing

## Implementation
The announcement message is implemented in the `on_ready` event in `run.py`. When making changes:
1. Update the feature list in the announcement embed
2. Update the version number if applicable
3. Ensure all new features are properly categorized
4. Maintain consistent formatting and emoji usage

## Example Format
```python
embed = discord.Embed(
    title="🟢 Shinobi Chronicles Online",
    description="The bot is now online and ready for action!",
    color=discord.Color.green()
)

# Commands section
embed.add_field(
    name="📜 Available Commands",
    value="Use these slash commands:\n\n"
          "**Official Features** ✅\n"
          "• `/command1` - Description\n"
          "• `/command2` - Description\n\n"
          "**Testing Features** 🧪\n"
          "• `/command3` - Description\n\n"
          "**Coming Soon** 🚧\n"
          "• `/command4` - Description\n"
          "• `/command5` - Description\n\n"
          "More features are in development!",
    inline=False
)

# Status section
embed.add_field(
    name="ℹ️ Bot Status",
    value="Version: X.Y.Z\n"
          "Status: Online\n"
          "Mode: Development",
    inline=False
)
```

## Version Numbering
Version numbers should follow semantic versioning:
- Major version (X): Breaking changes
- Minor version (Y): New features
- Patch version (Z): Bug fixes and minor updates

## Review Process
Before committing changes:
1. Verify all new features are listed
2. Check feature categorization is correct
3. Ensure version number is updated if needed
4. Test the announcement message locally 