"""Command line interface for Dream.OS agent coordination."""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from dreamos.coordinator import AgentDomain, AgentState
from dreamos.coordinator.cleanup import CleanupManager
from dreamos.coordinator.status import StatusManager

console = Console()

def setup_logging(verbose: bool) -> None:
    """Configure logging with appropriate verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)]
    )

class CleanupProgress:
    """Manages and visualizes cleanup progress."""
    
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        )
        
    def create_progress_table(self, domains: list[AgentDomain]) -> Table:
        """Create a progress table for cleanup tasks."""
        table = Table(show_header=True)
        table.add_column("Domain")
        table.add_column("Status")
        table.add_column("Tasks Completed")
        table.add_column("Dependencies")
        
        for domain in domains:
            table.add_row(
                domain.value,
                "[green]Ready[/green]",
                "0/0",
                ", ".join([d.value for d in self._get_domain_dependencies(domain)])
            )
        return table

    def _get_domain_dependencies(self, domain: AgentDomain) -> list[AgentDomain]:
        """Get dependencies for a given domain."""
        # Implement domain dependency logic here
        return []

async def dry_run_analysis(cleanup_manager: CleanupManager) -> None:
    """Perform dry run analysis of cleanup tasks."""
    table = Table(title="Cleanup Task Analysis")
    table.add_column("Task")
    table.add_column("Domain")
    table.add_column("Dependencies")
    table.add_column("Estimated Impact")
    
    tasks = await cleanup_manager.get_tasks()
    for task in tasks:
        table.add_row(
            task.name,
            task.domain.value,
            ", ".join([d.value for d in task.dependencies]),
            task.impact_level
        )
    
    console.print(table)

@click.group()
def cli():
    """Dream.OS agent coordination CLI."""
    pass

@cli.command()
@click.option(
    "--workspace-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Workspace directory containing agent files"
)
@click.option(
    "--task-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory containing task definitions"
)
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging")
def cleanup(workspace_dir: Path, task_dir: Path, dry_run: bool, verbose: bool):
    """Initialize and run system-wide cleanup."""
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    cleanup_manager = CleanupManager(workspace_dir, task_dir)
    progress = CleanupProgress()
    
    if dry_run:
        asyncio.run(dry_run_analysis(cleanup_manager))
        return
        
    try:
        with progress.progress:
            task = progress.progress.add_task("Running cleanup...", total=100)
            asyncio.run(cleanup_manager.run())
            progress.progress.update(task, completed=100)
    except KeyboardInterrupt:
        logger.warning("Cleanup interrupted by user")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        raise click.ClickException(str(e))

@cli.command()
@click.argument("domain", type=click.Choice([d.value for d in AgentDomain]), required=False)
def status(domain: Optional[str]):
    """Show status of a specific domain or all domains."""
    status_manager = StatusManager()
    
    table = Table(title="Agent Status")
    table.add_column("Domain")
    table.add_column("State")
    table.add_column("Current Task")
    table.add_column("Last Update")
    
    domains = [AgentDomain(domain)] if domain else list(AgentDomain)
    
    for d in domains:
        state = status_manager.get_domain_state(d)
        task = status_manager.get_current_task(d)
        last_update = status_manager.get_last_update(d)
        
        table.add_row(
            d.value,
            f"[{'green' if state == AgentState.IDLE else 'yellow' if state == AgentState.BUSY else 'red'}]{state.value}[/]",
            task or "None",
            last_update.strftime("%H:%M:%S") if last_update else "Never"
        )
    
    console.print(table)

if __name__ == "__main__":
    cli() 