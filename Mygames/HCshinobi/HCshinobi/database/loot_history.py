import sqlite3
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LootHistoryDB:
    DB_SUBDIR = "database"
    DB_FILENAME = "loot_history.db"
    
    def __init__(self, data_dir: str): 
        self.data_dir = data_dir
        self.db_dir = os.path.join(self.data_dir, self.DB_SUBDIR)
        self.db_path = os.path.join(self.db_dir, self.DB_FILENAME)
        logger.info(f"Initializing LootHistoryDB. Database path: {self.db_path}")
        self._ensure_dir_exists()
        self._init_db()

    def _ensure_dir_exists(self):
        """Ensures the database directory exists."""
        try:
            os.makedirs(self.db_dir, exist_ok=True)
            logger.debug(f"Database directory ensured: {self.db_dir}")
        except OSError as e:
            logger.error(f"Failed to create database directory {self.db_dir}: {e}", exc_info=True)
            raise

    def _init_db(self):
        """Initializes the loot history database table."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS loot_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        loot_amount INTEGER NOT NULL,
                        rarity TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                """)
                conn.commit()
                logger.info("Loot history database table initialized successfully.")
        except sqlite3.Error as e:
            logger.error(f"Database error during initialization at {self.db_path}: {e}", exc_info=True) 
            raise # Re-raise to signal failure

    def log_loot(self, user_id, loot_amount, rarity):
        """Logs a loot drop event to the database."""
        timestamp = datetime.utcnow().isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO loot_history (user_id, loot_amount, rarity, timestamp)
                    VALUES (?, ?, ?, ?)
                """, (user_id, loot_amount, rarity, timestamp))
                conn.commit()
                logger.debug(f"Logged loot for user {user_id}: Amount={loot_amount}, Rarity={rarity}")
        except sqlite3.Error as e:
            logger.error(f"Database error logging loot for user {user_id} at {self.db_path}: {e}", exc_info=True)
            # Decide if this should raise or just log. Logging only for now.

    def get_loot_history(self, user_id):
        """Retrieves loot history for a given user."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row # Return rows as dict-like objects
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT loot_amount, rarity, timestamp FROM loot_history
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                """, (user_id,))
                history = cursor.fetchall()
                logger.debug(f"Retrieved {len(history)} loot history records for user {user_id}")
                return history
        except sqlite3.Error as e:
            logger.error(f"Database error retrieving loot history for user {user_id} at {self.db_path}: {e}", exc_info=True)
            return [] # Return empty list on error 