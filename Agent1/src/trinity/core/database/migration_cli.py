import argparse
import logging
import sys
from typing import Optional
from pathlib import Path

from .migration_service import MigrationService

def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.
    
    Args:
        verbose: Whether to enable debug logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def get_connection(database_url: str):
    """Get database connection based on URL.
    
    Args:
        database_url: Database connection URL
        
    Returns:
        Database connection object
    """
    # This is a placeholder - implement actual connection logic based on your database
    # For example, using SQLAlchemy:
    # from sqlalchemy import create_engine
    # return create_engine(database_url).connect()
    pass

def create_migration(service: MigrationService, name: str, description: str) -> None:
    """Create a new migration.
    
    Args:
        service: Migration service instance
        name: Name of the migration
        description: Description of what the migration does
    """
    path = service.create_migration(name, description)
    print(f"Created new migration at: {path}")
    print("Please implement the upgrade() and downgrade() functions in this file.")

def run_migrations(service: MigrationService, target_version: Optional[int] = None) -> None:
    """Run pending migrations.
    
    Args:
        service: Migration service instance
        target_version: Optional specific version to migrate to
    """
    if service.migrate(target_version):
        print("Migrations completed successfully")
    else:
        print("Migration failed", file=sys.stderr)
        sys.exit(1)

def rollback_migrations(service: MigrationService, steps: int) -> None:
    """Roll back migrations.
    
    Args:
        service: Migration service instance
        steps: Number of migrations to roll back
    """
    if service.rollback(steps):
        print(f"Successfully rolled back {steps} migration(s)")
    else:
        print("Rollback failed", file=sys.stderr)
        sys.exit(1)

def show_status(service: MigrationService) -> None:
    """Show current migration status.
    
    Args:
        service: Migration service instance
    """
    status = service.get_status()
    
    print("\nCurrent version:", status["current_version"])
    
    if status["pending_migrations"]:
        print("\nPending migrations:")
        for migration in status["pending_migrations"]:
            print(f"  - {migration}")
    else:
        print("\nNo pending migrations")
    
    if status["history"]:
        print("\nMigration history:")
        for migration in status["history"]:
            timestamp = migration["applied_at"] or "Unknown"
            print(f"  - Version {migration['version']}: {migration['file']} (applied: {timestamp})")
    else:
        print("\nNo migration history")

def verify_migrations(service: MigrationService) -> None:
    """Verify migration integrity.
    
    Args:
        service: Migration service instance
    """
    if service.verify_integrity():
        print("Migration history integrity verified")
    else:
        print("Migration history integrity check failed", file=sys.stderr)
        sys.exit(1)

def repair_history(service: MigrationService) -> None:
    """Repair migration history.
    
    Args:
        service: Migration service instance
    """
    if service.repair_history():
        print("Successfully repaired migration history")
    else:
        print("Failed to repair migration history", file=sys.stderr)
        sys.exit(1)

def main() -> None:
    """Main entry point for the migration CLI."""
    parser = argparse.ArgumentParser(description="Database migration management tool")
    
    parser.add_argument(
        "--database",
        "-d",
        required=True,
        help="Database connection URL"
    )
    
    parser.add_argument(
        "--migrations-dir",
        "-m",
        default="migrations",
        help="Directory containing migration files"
    )
    
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("name", help="Name of the migration")
    create_parser.add_argument(
        "--description",
        "-d",
        default="",
        help="Description of what the migration does"
    )
    
    # migrate command
    migrate_parser = subparsers.add_parser("migrate", help="Run pending migrations")
    migrate_parser.add_argument(
        "--version",
        "-v",
        type=int,
        help="Target version to migrate to"
    )
    
    # rollback command
    rollback_parser = subparsers.add_parser("rollback", help="Roll back migrations")
    rollback_parser.add_argument(
        "--steps",
        "-s",
        type=int,
        default=1,
        help="Number of migrations to roll back"
    )
    
    # status command
    subparsers.add_parser("status", help="Show migration status")
    
    # verify command
    subparsers.add_parser("verify", help="Verify migration integrity")
    
    # repair command
    subparsers.add_parser("repair", help="Repair migration history")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    setup_logging(args.verbose)
    
    try:
        connection = get_connection(args.database)
        service = MigrationService(connection, args.migrations_dir)
        
        if args.command == "create":
            create_migration(service, args.name, args.description)
        elif args.command == "migrate":
            run_migrations(service, args.version)
        elif args.command == "rollback":
            rollback_migrations(service, args.steps)
        elif args.command == "status":
            show_status(service)
        elif args.command == "verify":
            verify_migrations(service)
        elif args.command == "repair":
            repair_history(service)
            
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 