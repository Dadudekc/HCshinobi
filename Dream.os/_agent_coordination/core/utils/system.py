"""System utilities for DreamOS agent coordination.

This module provides utilities for system operations like:
- Command execution
- File system operations
- Directory monitoring
- Process management
"""

import os
import sys
import time
import shutil
import logging
import asyncio
import subprocess
from pathlib import Path
from typing import Callable, Optional, Union, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from .base import RetryManager

logger = logging.getLogger(__name__)

@dataclass
class CommandResult:
    """Result of a command execution."""
    success: bool
    return_code: int
    stdout: str
    stderr: str
    duration: float
    command: List[str]

class CommandExecutor:
    """Utility for executing system commands with retry support."""
    
    def __init__(self, 
                 max_retries: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 10.0):
        self.retry_manager = RetryManager(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=max_delay
        )
        
    async def run_command(self,
                         command: Union[str, List[str]],
                         cwd: Optional[Union[str, Path]] = None,
                         env: Optional[Dict[str, str]] = None,
                         timeout: Optional[float] = None,
                         check: bool = True) -> CommandResult:
        """Execute a command with retry support.
        
        Args:
            command: Command to execute (string or list)
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout in seconds
            check: Whether to raise on non-zero exit
            
        Returns:
            CommandResult object with execution details
            
        Raises:
            subprocess.CalledProcessError: If check=True and return code != 0
            asyncio.TimeoutError: If command exceeds timeout
        """
        if isinstance(command, str):
            command = command.split()
            
        async def _execute():
            start_time = time.time()
            try:
                process = await asyncio.create_subprocess_exec(
                    *command,
                    cwd=cwd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
                
                duration = time.time() - start_time
                result = CommandResult(
                    success=(process.returncode == 0),
                    return_code=process.returncode,
                    stdout=stdout.decode().strip(),
                    stderr=stderr.decode().strip(),
                    duration=duration,
                    command=command
                )
                
                if check and process.returncode != 0:
                    raise subprocess.CalledProcessError(
                        process.returncode,
                        command,
                        stdout,
                        stderr
                    )
                    
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"Command timed out after {timeout}s: {' '.join(command)}")
                raise
            except Exception as e:
                logger.error(f"Error executing command {' '.join(command)}: {e}")
                raise
                
        return await self.retry_manager.execute(_execute)

class DirectoryMonitor:
    """Utility for monitoring directory changes."""
    
    def __init__(self,
                 watch_dir: Union[str, Path],
                 success_dir: Union[str, Path],
                 error_dir: Union[str, Path],
                 file_pattern: str = "*",
                 poll_interval: float = 10.0):
        self.watch_dir = Path(watch_dir)
        self.success_dir = Path(success_dir)
        self.error_dir = Path(error_dir)
        self.file_pattern = file_pattern
        self.poll_interval = poll_interval
        self._stop_event = asyncio.Event()
        
        # Create directories
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self.success_dir.mkdir(parents=True, exist_ok=True)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        
    async def process_file(self, file_path: Path) -> bool:
        """Process a single file. Override this method in subclasses."""
        raise NotImplementedError
        
    def _move_file(self, file_path: Path, dest_dir: Path) -> Path:
        """Move file to destination directory with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        dest_path = dest_dir / new_name
        shutil.move(str(file_path), str(dest_path))
        return dest_path
        
    async def _process_pending_files(self) -> None:
        """Process all pending files in watch directory."""
        for file_path in self.watch_dir.glob(self.file_pattern):
            try:
                success = await self.process_file(file_path)
                dest_dir = self.success_dir if success else self.error_dir
                moved_path = self._move_file(file_path, dest_dir)
                logger.info(f"Moved {file_path} to {moved_path}")
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self._move_file(file_path, self.error_dir)
                
    async def start(self) -> None:
        """Start monitoring directory."""
        logger.info(f"Starting directory monitor for {self.watch_dir}")
        while not self._stop_event.is_set():
            try:
                await self._process_pending_files()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(1.0)  # Brief pause before retry
                
    async def stop(self) -> None:
        """Stop monitoring directory."""
        self._stop_event.set()
        logger.info(f"Stopped directory monitor for {self.watch_dir}")

class FileManager:
    """Utility for file system operations with retry support."""
    
    def __init__(self, max_retries: int = 3):
        self.retry_manager = RetryManager(max_retries=max_retries)
        
    async def safe_move(self,
                       src: Union[str, Path],
                       dst: Union[str, Path],
                       overwrite: bool = False) -> None:
        """Move file with retry support."""
        async def _move():
            src_path = Path(src)
            dst_path = Path(dst)
            
            if not overwrite and dst_path.exists():
                raise FileExistsError(f"Destination exists: {dst_path}")
                
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src_path), str(dst_path))
            
        await self.retry_manager.execute(_move)
        
    async def safe_copy(self,
                       src: Union[str, Path],
                       dst: Union[str, Path],
                       overwrite: bool = False) -> None:
        """Copy file with retry support."""
        async def _copy():
            src_path = Path(src)
            dst_path = Path(dst)
            
            if not overwrite and dst_path.exists():
                raise FileExistsError(f"Destination exists: {dst_path}")
                
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src_path), str(dst_path))
            
        await self.retry_manager.execute(_copy)
        
    async def safe_delete(self, path: Union[str, Path]) -> None:
        """Delete file with retry support."""
        async def _delete():
            path_obj = Path(path)
            if path_obj.is_file():
                path_obj.unlink()
            elif path_obj.is_dir():
                shutil.rmtree(str(path_obj))
                
        await self.retry_manager.execute(_delete)
        
    async def safe_read(self, path: Union[str, Path]) -> str:
        """Read file with retry support."""
        async def _read():
            with open(path, 'r') as f:
                return f.read()
                
        return await self.retry_manager.execute(_read)
        
    async def safe_write(self,
                        path: Union[str, Path],
                        content: str,
                        mode: str = 'w') -> None:
        """Write file with retry support."""
        async def _write():
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path_obj, mode) as f:
                f.write(content)
                
        await self.retry_manager.execute(_write) 