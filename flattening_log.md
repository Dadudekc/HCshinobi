# Directory Flattening Log

- Moved `_discord/extensions/__init__.py` to `_discord/extensions.py` and removed
  the now-empty `extensions/` folder.
- Updated `_discord/__init__.py` comment accordingly.
- Relocated test modules:
  - `tests/core/battle/*` -> `tests/battle/`
  - `tests/core/missions/*` -> `tests/missions/`
  Removed the empty `tests/core/` directory.

These changes reduce one level of nesting for Discord extensions and core tests.
