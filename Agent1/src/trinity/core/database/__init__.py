"""
Database functionality for Chat.Mate
"""

__version__ = "0.1.0"

from .db_adapter import DatabaseAdapter
from .migration_manager import MigrationManager
from .security_manager import SecurityManager
from .recovery_manager import RecoveryManager

__all__ = [
    'MigrationManager',
    'SecurityManager',
    'RecoveryManager'
] 