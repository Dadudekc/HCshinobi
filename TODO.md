# HCShinobi Character + Jutsu System: High-Level Summary & Roadmap

## ✅ Features Included

| Command              | Purpose                                                 |
| -------------------- | ------------------------------------------------------- |
| `/create`            | Create a new ninja with optional clan                   |
| `/profile`           | View full character stats and rank info                 |
| `/jutsu`             | View all jutsu (learned, available, close to unlocking) |
| `/jutsu_info`        | Get full stats + effects of a specific jutsu            |
| `/unlock_jutsu`      | Manually unlock jutsu (with requirement feedback)       |
| `/auto_unlock_jutsu` | Bulk-unlocks all valid jutsu                            |
| `/progression`       | View XP, rank progress, and next-level rewards          |
| `/delete_character`  | Deletes the character file and cache                    |

## 🔧 System Design Highlights

- Uses `self._character_to_dict` for uniform jutsu logic
- Inline handling of XP progress bar (`█░` style)
- Supports unlockable requirements (level, stats, achievements)
- Modular emoji + color mapping by rarity/element
- Fully ephemeral-friendly responses for errors or personal data

## 🔥 Suggested Next Upgrades

### 1. Combat System Integration
- Add `/duel @target`, `/battle_log`, `/use_jutsu` commands
- Leverage jutsu accuracy, damage, chakra cost in real-time
- Queue turn system or reaction-based combat loop

### 2. Passive Stats & Bonuses
- Apply elemental affinities, clan bonuses, or passive effects per jutsu learned

### 3. Achievements System
- Create `/achievements`, `/claim_reward`, `/badge` display
- Tie to story arcs, event quests, rare jutsu unlocks

### 4. JSON → SQLite Migration
- Migrate character storage to SQLite for faster, relational queries
- Enables leaderboard support, guild-wide stats, and backup-safe handling

---

## 📁 Commit Summary

```
feat: full integration of character and jutsu commands

- Character creation, stat display, and clan assignment
- Jutsu viewing, unlocking, filtering by requirements
- Auto-unlock flow for valid jutsu
- XP and level progression display
- Safe delete with confirmation and memory cleanup
``` 