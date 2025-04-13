from typing import Any, Dict, List, Optional, Tuple
from abc import ABC, abstractmethod
import logging

class DatabaseAdapter(ABC):
    """Abstract base class for database adapters."""
    
    @abstractmethod
    def get_version(self) -> str:
        """Get database version."""
        pass
        
    @abstractmethod
    def check_connection(self) -> bool:
        """Check if connection is valid."""
        pass
        
    @abstractmethod
    def begin_transaction(self) -> None:
        """Begin a transaction."""
        pass
        
    @abstractmethod
    def commit_transaction(self) -> None:
        """Commit a transaction."""
        pass
        
    @abstractmethod
    def rollback_transaction(self) -> None:
        """Rollback a transaction."""
        pass
        
    @abstractmethod
    def create_savepoint(self, name: str) -> None:
        """Create a savepoint."""
        pass
        
    @abstractmethod
    def rollback_to_savepoint(self, name: str) -> None:
        """Rollback to a savepoint."""
        pass
        
    @abstractmethod
    def release_savepoint(self, name: str) -> None:
        """Release a savepoint."""
        pass
        
    @abstractmethod
    def get_tables(self) -> List[str]:
        """Get list of tables."""
        pass
        
    @abstractmethod
    def get_columns(self, table: str) -> List[str]:
        """Get columns for a table."""
        pass
        
    @abstractmethod
    def check_consistency(self) -> bool:
        """Check database consistency."""
        pass
        
    @abstractmethod
    def set_timeout(self, seconds: int) -> None:
        """Set query timeout."""
        pass

class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter."""
    
    def __init__(self, connection):
        self.connection = connection
        self.logger = logging.getLogger(__name__)
        
    def get_version(self) -> str:
        cursor = self.connection.execute("SELECT sqlite_version()")
        return cursor.fetchone()[0]
        
    def check_connection(self) -> bool:
        try:
            self.connection.execute("SELECT 1")
            return True
        except:
            return False
            
    def begin_transaction(self) -> None:
        self.connection.execute("BEGIN TRANSACTION")
        
    def commit_transaction(self) -> None:
        self.connection.execute("COMMIT")
        
    def rollback_transaction(self) -> None:
        self.connection.execute("ROLLBACK")
        
    def create_savepoint(self, name: str) -> None:
        self.connection.execute(f"SAVEPOINT {name}")
        
    def rollback_to_savepoint(self, name: str) -> None:
        self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        
    def release_savepoint(self, name: str) -> None:
        self.connection.execute(f"RELEASE SAVEPOINT {name}")
        
    def get_tables(self) -> List[str]:
        cursor = self.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        return [row[0] for row in cursor.fetchall()]
        
    def get_columns(self, table: str) -> List[str]:
        cursor = self.connection.execute(f"SELECT * FROM {table} LIMIT 1")
        return [desc[0] for desc in cursor.description]
        
    def check_consistency(self) -> bool:
        try:
            self.connection.execute("PRAGMA integrity_check")
            self.connection.execute("PRAGMA foreign_key_check")
            return True
        except:
            return False
            
    def set_timeout(self, seconds: int) -> None:
        self.connection.execute(f"PRAGMA busy_timeout = {seconds * 1000}")

class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL database adapter."""
    
    def __init__(self, connection):
        self.connection = connection
        self.logger = logging.getLogger(__name__)
        
    def get_version(self) -> str:
        cursor = self.connection.execute("SHOW server_version")
        return cursor.fetchone()[0]
        
    def check_connection(self) -> bool:
        try:
            self.connection.execute("SELECT 1")
            return True
        except:
            return False
            
    def begin_transaction(self) -> None:
        self.connection.execute("BEGIN")
        
    def commit_transaction(self) -> None:
        self.connection.execute("COMMIT")
        
    def rollback_transaction(self) -> None:
        self.connection.execute("ROLLBACK")
        
    def create_savepoint(self, name: str) -> None:
        self.connection.execute(f"SAVEPOINT {name}")
        
    def rollback_to_savepoint(self, name: str) -> None:
        self.connection.execute(f"ROLLBACK TO SAVEPOINT {name}")
        
    def release_savepoint(self, name: str) -> None:
        self.connection.execute(f"RELEASE SAVEPOINT {name}")
        
    def get_tables(self) -> List[str]:
        cursor = self.connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        return [row[0] for row in cursor.fetchall()]
        
    def get_columns(self, table: str) -> List[str]:
        cursor = self.connection.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            [table]
        )
        return [row[0] for row in cursor.fetchall()]
        
    def check_consistency(self) -> bool:
        try:
            # Check for bloat and index corruption
            self.connection.execute("VACUUM ANALYZE")
            return True
        except:
            return False
            
    def set_timeout(self, seconds: int) -> None:
        self.connection.execute(f"SET statement_timeout = {seconds * 1000}")

def create_adapter(connection, db_type: str = None) -> DatabaseAdapter:
    """Create appropriate database adapter.
    
    Args:
        connection: Database connection
        db_type: Database type ('sqlite' or 'postgresql')
        
    Returns:
        DatabaseAdapter instance
    """
    if db_type is None:
        # Try to auto-detect database type
        try:
            connection.execute("SELECT sqlite_version()")
            return SQLiteAdapter(connection)
        except:
            try:
                connection.execute("SHOW server_version")
                return PostgreSQLAdapter(connection)
            except:
                raise ValueError("Unable to detect database type")
                
    db_type = db_type.lower()
    if db_type == 'sqlite':
        return SQLiteAdapter(connection)
    elif db_type == 'postgresql':
        return PostgreSQLAdapter(connection)
    else:
        raise ValueError(f"Unsupported database type: {db_type}") 