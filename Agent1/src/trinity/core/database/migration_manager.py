from typing import List, Dict, Optional
import logging
import os
import json
from datetime import datetime
from pathlib import Path

class MigrationManager:
    """Manages database migrations with version tracking and rollback support."""
    
    def __init__(self, migrations_dir: str = "migrations"):
        """Initialize the migration manager.
        
        Args:
            migrations_dir: Directory where migration files are stored
        """
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)
        self.version_file = self.migrations_dir / "version.json"
        self.logger = logging.getLogger(__name__)
        self._initialize_version_tracking()
    
    def _initialize_version_tracking(self) -> None:
        """Initialize or load version tracking information."""
        if not self.version_file.exists():
            self._save_version_info({
                "current_version": 0,
                "migrations": [],
                "last_migration": None
            })
    
    def _save_version_info(self, info: Dict) -> None:
        """Save version tracking information to file.
        
        Args:
            info: Version information to save
        """
        with open(self.version_file, 'w') as f:
            json.dump(info, f, indent=2)
    
    def _load_version_info(self) -> Dict:
        """Load version tracking information from file.
        
        Returns:
            Dict containing version information
        """
        with open(self.version_file, 'r') as f:
            return json.load(f)
    
    def create_migration(self, name: str) -> str:
        """Create a new migration file.
        
        Args:
            name: Name of the migration
            
        Returns:
            Path to the created migration file
        """
        version_info = self._load_version_info()
        new_version = version_info["current_version"] + 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{new_version:04d}_{timestamp}_{name}.py"
        
        migration_path = self.migrations_dir / filename
        
        template = f'''"""Migration {new_version}: {name}"""

def upgrade(connection):
    """Upgrade to version {new_version}"""
    # TODO: Implement upgrade logic
    pass

def downgrade(connection):
    """Downgrade from version {new_version}"""
    # TODO: Implement downgrade logic
    pass
'''
        
        with open(migration_path, 'w') as f:
            f.write(template)
            
        self.logger.info(f"Created migration file: {filename}")
        return str(migration_path)
    
    def get_pending_migrations(self) -> List[str]:
        """Get list of pending migrations.
        
        Returns:
            List of migration filenames that need to be applied
        """
        version_info = self._load_version_info()
        current_version = version_info["current_version"]
        
        all_migrations = sorted([f for f in os.listdir(self.migrations_dir) 
                               if f.endswith('.py') and f[0].isdigit()])
        
        return [m for m in all_migrations 
                if int(m.split('_')[0]) > current_version]
    
    def apply_migration(self, migration_file: str, connection) -> bool:
        """Apply a single migration.
        
        Args:
            migration_file: Name of migration file to apply
            connection: Database connection object
            
        Returns:
            True if migration was successful, False otherwise
        """
        try:
            # Import the migration module
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "migration",
                self.migrations_dir / migration_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Apply the upgrade
            module.upgrade(connection)
            
            # Update version info
            version_info = self._load_version_info()
            version = int(migration_file.split('_')[0])
            version_info["current_version"] = version
            version_info["migrations"].append({
                "file": migration_file,
                "applied_at": datetime.now().isoformat(),
                "version": version
            })
            version_info["last_migration"] = migration_file
            
            self._save_version_info(version_info)
            self.logger.info(f"Successfully applied migration: {migration_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to apply migration {migration_file}: {str(e)}")
            return False
    
    def rollback(self, connection, steps: int = 1) -> bool:
        """Rollback the specified number of migrations.
        
        Args:
            connection: Database connection object
            steps: Number of migrations to roll back
            
        Returns:
            True if rollback was successful, False otherwise
        """
        version_info = self._load_version_info()
        if not version_info["migrations"]:
            self.logger.info("No migrations to roll back")
            return True
            
        try:
            for _ in range(steps):
                if not version_info["migrations"]:
                    break
                    
                last_migration = version_info["migrations"].pop()
                migration_file = last_migration["file"]
                
                # Import and run downgrade
                spec = importlib.util.spec_from_file_location(
                    "migration",
                    self.migrations_dir / migration_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.downgrade(connection)
                
                # Update version info
                if version_info["migrations"]:
                    version_info["current_version"] = version_info["migrations"][-1]["version"]
                    version_info["last_migration"] = version_info["migrations"][-1]["file"]
                else:
                    version_info["current_version"] = 0
                    version_info["last_migration"] = None
                    
            self._save_version_info(version_info)
            self.logger.info(f"Successfully rolled back {steps} migration(s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to roll back migrations: {str(e)}")
            return False
    
    def get_current_version(self) -> int:
        """Get the current database version.
        
        Returns:
            Current database version number
        """
        version_info = self._load_version_info()
        return version_info["current_version"]
    
    def get_migration_history(self) -> List[Dict]:
        """Get the migration history.
        
        Returns:
            List of applied migrations with timestamps
        """
        version_info = self._load_version_info()
        return version_info["migrations"] 