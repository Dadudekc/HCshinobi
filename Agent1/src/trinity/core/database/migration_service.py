from typing import List, Dict, Optional
import logging
from pathlib import Path
from .migration_manager import MigrationManager

class MigrationService:
    """Service for managing database migrations."""
    
    def __init__(self, db_connection, migrations_dir: str = "migrations"):
        """Initialize the migration service.
        
        Args:
            db_connection: Database connection object
            migrations_dir: Directory where migration files are stored
        """
        self.connection = db_connection
        self.manager = MigrationManager(migrations_dir)
        self.logger = logging.getLogger(__name__)
        
    def create_migration(self, name: str, description: str = "") -> str:
        """Create a new migration file.
        
        Args:
            name: Name of the migration
            description: Optional description of what the migration does
            
        Returns:
            Path to the created migration file
        """
        migration_path = self.manager.create_migration(name)
        self.logger.info(f"Created migration '{name}' at {migration_path}")
        return migration_path
        
    def migrate(self, target_version: Optional[int] = None) -> bool:
        """Run all pending migrations or migrate to a specific version.
        
        Args:
            target_version: Optional specific version to migrate to
            
        Returns:
            True if all migrations were successful, False otherwise
        """
        pending = self.manager.get_pending_migrations()
        if not pending:
            self.logger.info("No pending migrations")
            return True
            
        current_version = self.manager.get_current_version()
        
        if target_version is not None:
            if target_version < current_version:
                return self.rollback(current_version - target_version)
            pending = [m for m in pending 
                      if int(m.split('_')[0]) <= target_version]
        
        success = True
        for migration in pending:
            if not self.manager.apply_migration(migration, self.connection):
                success = False
                break
                
        if success:
            self.logger.info("All migrations applied successfully")
        else:
            self.logger.error("Migration failed")
            
        return success
        
    def rollback(self, steps: int = 1) -> bool:
        """Rollback the specified number of migrations.
        
        Args:
            steps: Number of migrations to roll back
            
        Returns:
            True if rollback was successful, False otherwise
        """
        return self.manager.rollback(self.connection, steps)
        
    def get_status(self) -> Dict:
        """Get current migration status.
        
        Returns:
            Dict containing current version and pending migrations
        """
        current_version = self.manager.get_current_version()
        pending = self.manager.get_pending_migrations()
        history = self.manager.get_migration_history()
        
        return {
            "current_version": current_version,
            "pending_migrations": pending,
            "history": history
        }
        
    def verify_integrity(self) -> bool:
        """Verify the integrity of the migration history.
        
        Returns:
            True if migration history is valid, False otherwise
        """
        try:
            history = self.manager.get_migration_history()
            if not history:
                return True
                
            # Check version sequence
            versions = [m["version"] for m in history]
            if sorted(versions) != versions:
                self.logger.error("Migration versions are not sequential")
                return False
                
            # Check file existence
            for migration in history:
                migration_path = Path(self.manager.migrations_dir) / migration["file"]
                if not migration_path.exists():
                    self.logger.error(f"Migration file missing: {migration['file']}")
                    return False
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify migration integrity: {str(e)}")
            return False
            
    def repair_history(self) -> bool:
        """Attempt to repair the migration history if it's corrupted.
        
        Returns:
            True if repair was successful, False otherwise
        """
        try:
            # Get all migration files
            migration_files = sorted([f for f in Path(self.manager.migrations_dir).glob("*.py")
                                   if f.name[0].isdigit()])
                                   
            # Reconstruct history from files
            history = []
            for file in migration_files:
                version = int(file.name.split('_')[0])
                history.append({
                    "file": file.name,
                    "version": version,
                    "applied_at": None  # Can't recover exact timestamp
                })
                
            # Update version info
            version_info = {
                "current_version": history[-1]["version"] if history else 0,
                "migrations": history,
                "last_migration": history[-1]["file"] if history else None
            }
            
            self.manager._save_version_info(version_info)
            self.logger.info("Successfully repaired migration history")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to repair migration history: {str(e)}")
            return False 