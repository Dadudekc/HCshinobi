import sqlite3
import aiosqlite
from typing import Optional, List, Dict, Any
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlparse

class Database:
    def __init__(self, db_path: str):
        self.db_uri = db_path  # Store the original URI
        self._actual_db_path = self._parse_db_path(db_path)
        self._ensure_db_directory()
        
    def _parse_db_path(self, db_uri: str) -> str:
        """Parse the database URI/path to get the actual file path."""
        parsed = urlparse(db_uri)
        actual_file_path = ''

        if parsed.scheme == 'sqlite':
            path_part = parsed.path
            # Handle relative paths like 'sqlite:///file.db' -> file.db
            if db_uri.startswith('sqlite:///'):
                 # Remove the scheme and leading slashes
                actual_file_path = db_uri.split(':///', 1)[1]
            # Handle absolute paths like 'sqlite:////abs/path/file.db' -> /abs/path/file.db
            elif db_uri.startswith('sqlite:////'):
                 # The path part already includes the leading '/'
                 actual_file_path = path_part
                 # On Windows, urlparse might add a leading '/' to drive letters, e.g., /C:/path
                 if os.name == 'nt' and actual_file_path.startswith('/') and len(actual_file_path) > 2 and actual_file_path[2] == ':':
                     actual_file_path = actual_file_path[1:] # Remove leading '/' -> C:/path
            else:
                 # Fallback or handle other sqlite URI formats if necessary, might just be filename
                 actual_file_path = path_part if path_part else db_uri # If path_part is empty, assume it's just the filename
                 # Strip leading slashes if they exist and it's not an absolute path identifier
                 if actual_file_path.startswith('/') and not (os.name == 'nt' and len(actual_file_path) > 2 and actual_file_path[2] == ':'):
                     actual_file_path = actual_file_path.lstrip('/')

        else:
             # Assume it's a direct file path if not a sqlite URI
             actual_file_path = db_uri

        # Ensure we have a valid path, default to db_uri if parsing failed unexpectedly
        return actual_file_path if actual_file_path else db_uri

    def _ensure_db_directory(self):
        """Ensure the database directory exists"""
        # Use the parsed actual file path
        db_dir = os.path.dirname(self._actual_db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

    async def init(self):
        """Initialize the database connection and create tables if needed"""
        # Use the actual path for connection
        async with aiosqlite.connect(self._actual_db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS characters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    level INTEGER DEFAULT 1,
                    experience INTEGER DEFAULT 0,
                    clan TEXT,
                    clan_joined_at TIMESTAMP,
                    village TEXT,
                    stats TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.execute('''
                CREATE TABLE IF NOT EXISTS clans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    village TEXT,
                    population INTEGER DEFAULT 0,
                    rarity TEXT,
                    kekkei_genkai TEXT,
                    traits TEXT,
                    required_level INTEGER DEFAULT 0,
                    required_village TEXT,
                    required_strength INTEGER DEFAULT 0,
                    required_speed INTEGER DEFAULT 0,
                    required_defense INTEGER DEFAULT 0,
                    required_chakra INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.commit()

    async def execute(self, query: str, params: tuple = ()) -> None:
        """Execute a query without returning results"""
        # Use the actual path for connection
        async with aiosqlite.connect(self._actual_db_path) as db:
            await db.execute(query, params)
            await db.commit()

    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch a single row from the database"""
        # Use the actual path for connection
        async with aiosqlite.connect(self._actual_db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from the database"""
        # Use the actual path for connection
        async with aiosqlite.connect(self._actual_db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def execute_many(self, query: str, params_list: List[tuple]) -> None:
        """Execute many queries with different parameters"""
        # Use the actual path for connection
        async with aiosqlite.connect(self._actual_db_path) as db:
            await db.executemany(query, params_list)
            await db.commit()

    def dict_to_json(self, data: Dict[str, Any]) -> str:
        """Convert a dictionary to a JSON string"""
        return json.dumps(data)

    def json_to_dict(self, json_str: str) -> Dict[str, Any]:
        """Convert a JSON string to a dictionary"""
        return json.loads(json_str) if json_str else {} 