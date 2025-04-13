"""
Command-line interface for system health monitoring.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
import json
from typing import Optional, Dict, Any
import curses
from curses import window
import time

from .monitor import SystemHealthMonitor
from .utils.status_types import HealthStatus

class HealthMonitorCLI:
    """CLI interface for system health monitoring."""
    
    def __init__(self, monitor: SystemHealthMonitor):
        """Initialize the CLI interface."""
        self.monitor = monitor
        self.refresh_interval = 1.0  # seconds
        self.running = False
        self.screen: Optional[window] = None
        
    def start(self) -> None:
        """Start the CLI interface."""
        curses.wrapper(self._run_interface)
        
    def _run_interface(self, screen: window) -> None:
        """Run the main interface loop."""
        self.screen = screen
        self.running = True
        
        # Configure colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Healthy
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK) # Degraded
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)    # Unhealthy
        
        # Hide cursor
        curses.curs_set(0)
        
        while self.running:
            try:
                self._update_display()
                time.sleep(self.refresh_interval)
                
                # Check for quit command
                c = screen.getch()
                if c == ord('q'):
                    self.running = False
                    
            except KeyboardInterrupt:
                self.running = False
                
    def _update_display(self) -> None:
        """Update the display with current health metrics."""
        if not self.screen:
            return
            
        self.screen.clear()
        
        # Get current health
        health = self.monitor.get_system_health()
        
        # Display header
        self.screen.addstr(0, 0, "=== System Health Monitor ===")
        self.screen.addstr(1, 0, f"Timestamp: {health['timestamp']}")
        
        # Display overall status with color
        status = health["overall_status"]
        color = self._get_status_color(status)
        self.screen.addstr(2, 0, f"Overall Status: ", curses.A_BOLD)
        self.screen.addstr(status, color | curses.A_BOLD)
        
        # Display component status
        self.screen.addstr(4, 0, "Component Status:", curses.A_BOLD)
        row = 5
        
        for component, status in health["components"].items():
            color = self._get_status_color(status["status"])
            self.screen.addstr(row, 2, f"{component}: ")
            self.screen.addstr(status["status"], color)
            self.screen.addstr(" - " + status["message"])
            row += 1
            
            # Display component details if available
            if "metrics" in status:
                metrics = status["metrics"]
                for key, value in metrics.items():
                    if isinstance(value, (int, float, str, bool)):
                        self.screen.addstr(row, 4, f"{key}: {value}")
                        row += 1
            row += 1
            
        # Display resource usage
        usage = self.monitor.get_resource_usage()
        self.screen.addstr(row, 0, "Resource Usage:", curses.A_BOLD)
        row += 1
        self.screen.addstr(row, 2, f"CPU: {usage.get('cpu', 0)}%")
        row += 1
        self.screen.addstr(row, 2, f"Memory: {usage.get('memory', 0)}%")
        row += 1
        self.screen.addstr(row, 2, f"Disk: {usage.get('disk', 0)}%")
        
        # Display help
        row += 2
        self.screen.addstr(row, 0, "Press 'q' to quit")
        
        self.screen.refresh()
        
    def _get_status_color(self, status: str) -> int:
        """Get the color pair for a status."""
        if status == "HEALTHY":
            return curses.color_pair(1)
        elif status == "DEGRADED":
            return curses.color_pair(2)
        else:
            return curses.color_pair(3)

def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="System Health Monitor CLI"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Check interval in seconds"
    )
    parser.add_argument(
        "--history-size",
        type=int,
        default=1000,
        help="Number of historical metrics to keep"
    )
    
    args = parser.parse_args()
    
    # Create mock managers for demo
    class MockManager:
        pass
    
    driver_manager = MockManager()
    memory_manager = MockManager()
    thread_pool = MockManager()
    
    # Create and start monitor
    monitor = SystemHealthMonitor(
        driver_manager=driver_manager,
        memory_manager=memory_manager,
        thread_pool=thread_pool,
        check_interval=args.interval,
        history_size=args.history_size
    )
    
    monitor.start_monitoring()
    
    try:
        # Start CLI
        cli = HealthMonitorCLI(monitor)
        cli.start()
    finally:
        monitor.stop_monitoring()

if __name__ == "__main__":
    main() 