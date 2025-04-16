"""Headless Cursor instance controller for fleet automation."""

import win32gui
import win32con
import win32api
import asyncio
import logging
from typing import Dict, Optional, List, Tuple, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
from queue import Queue
from threading import Lock
import time
import cv2
import numpy as np
from PIL import Image

from cursor_window_controller import CursorWindowController, WindowWrapper
from cursor_element_locator import create_locator, BoundingBox

@dataclass
class CommandResult:
    """Result of an automated command execution."""
    success: bool
    message: str
    timestamp: datetime
    duration: float
    element_type: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[Exception] = None
    retry_count: int = 0

    def to_dict(self) -> Dict:
        """Convert result to dictionary format."""
        return {
            "success": self.success,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration": self.duration,
            "element_type": self.element_type,
            "confidence": self.confidence,
            "error": str(self.error) if self.error else None,
            "retry_count": self.retry_count
        }

class CursorCommand:
    """Represents a command to be executed on a Cursor instance."""
    
    def __init__(
        self,
        command_type: str,
        params: Dict = None,
        timeout: float = 5.0,
        retry_count: int = 3,
        next_command: Optional['CursorCommand'] = None,
        retry_delay: float = 1.0
    ):
        self.command_type = command_type
        self.params = params or {}
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.next_command = next_command
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[CommandResult] = None
        self._current_retry = 0
        
    @property
    def has_next(self) -> bool:
        """Check if this command has a next command in chain."""
        return self.next_command is not None
        
    def chain(self, next_command: 'CursorCommand') -> 'CursorCommand':
        """Chain another command to be executed after this one."""
        self.next_command = next_command
        return next_command
        
    @property
    def can_retry(self) -> bool:
        """Check if command can be retried."""
        return self._current_retry < self.retry_count
        
    def increment_retry(self):
        """Increment retry counter."""
        self._current_retry += 1

class CursorInstance:
    """Controls a single Cursor window instance."""
    
    def __init__(
        self,
        window: WindowWrapper,
        element_locator: create_locator,
        command_queue: Queue,
        state_lock: Lock,
        min_confidence: float = 0.8
    ):
        self.window = window
        self.element_locator = element_locator
        self.command_queue = command_queue
        self.state_lock = state_lock
        self.min_confidence = min_confidence
        self.logger = logging.getLogger(f"CursorInstance[{window.id}]")
        
        # Instance state
        self.is_busy = False
        self.last_command: Optional[CursorCommand] = None
        self.last_screenshot = None
        self.last_detection: Optional[Dict[str, BoundingBox]] = None
        
        # Start command processing
        self._command_task = asyncio.create_task(self._process_command_queue())
        
    async def _process_command_queue(self):
        """Process commands from the queue continuously."""
        while True:
            try:
                # Get next command
                command = await asyncio.get_event_loop().run_in_executor(
                    None, self.command_queue.get
                )
                
                # Process command
                with self.state_lock:
                    result = await self.process_command(command)
                
                # Log result
                if result.success:
                    self.logger.info(
                        f"Command {command.command_type} completed: {result.message}"
                    )
                else:
                    self.logger.warning(
                        f"Command {command.command_type} failed: {result.message}"
                    )
                
                # Mark task done
                self.command_queue.task_done()
                
            except Exception as e:
                self.logger.error(f"Error processing command queue: {str(e)}")
                await asyncio.sleep(1)  # Prevent tight loop on error

    async def shutdown(self):
        """Clean shutdown of the instance."""
        if hasattr(self, '_command_task'):
            self._command_task.cancel()
            try:
                await self._command_task
            except asyncio.CancelledError:
                pass

    async def click_element(
        self,
        element_type: str,
        confidence_threshold: Optional[float] = None
    ) -> CommandResult:
        """Click a UI element using Win32 messages."""
        start_time = time.time()
        
        try:
            # Get fresh screenshot
            screenshot = self.capture()
            
            # Detect element
            bbox = self.element_locator.detect_element(
                element_type,
                screenshot,
                self.window.id,
            )
            
            if not bbox:
                return CommandResult(
                    success=False,
                    message=f"Element {element_type} not found",
                    timestamp=datetime.now(),
                    duration=time.time() - start_time,
                    element_type=element_type
                )
            
            threshold = confidence_threshold or self.min_confidence
            if bbox.confidence < threshold:
                return CommandResult(
                    success=False,
                    message=f"Low confidence ({bbox.confidence:.2f} < {threshold})",
                    timestamp=datetime.now(),
                    duration=time.time() - start_time,
                    element_type=element_type,
                    confidence=bbox.confidence
                )
            
            # Convert to screen coordinates
            screen_x = self.window.geometry['x'] + bbox.center[0]
            screen_y = self.window.geometry['y'] + bbox.center[1]
            
            # Send click via Win32
            win32api.SendMessage(
                self.window.handle,
                win32con.WM_LBUTTONDOWN,
                win32con.MK_LBUTTON,
                win32api.MAKELONG(screen_x, screen_y)
            )
            await asyncio.sleep(0.1)  # Brief pause between down/up
            win32api.SendMessage(
                self.window.handle,
                win32con.WM_LBUTTONUP,
                0,
                win32api.MAKELONG(screen_x, screen_y)
            )
            
            return CommandResult(
                success=True,
                message=f"Clicked {element_type} at ({screen_x}, {screen_y})",
                timestamp=datetime.now(),
                duration=time.time() - start_time,
                element_type=element_type,
                confidence=bbox.confidence
            )
            
        except Exception as e:
            self.logger.error(f"Click failed: {str(e)}")
            return CommandResult(
                success=False,
                message=f"Click failed: {str(e)}",
                timestamp=datetime.now(),
                duration=time.time() - start_time,
                element_type=element_type,
                error=e
            )
    
    async def wait_for_element(
        self,
        element_type: str,
        present: bool = True,
        timeout: float = 5.0,
        confidence_threshold: Optional[float] = None
    ) -> CommandResult:
        """Wait for an element to appear or disappear."""
        start_time = time.time()
        threshold = confidence_threshold or self.min_confidence
        
        try:
            while (time.time() - start_time) < timeout:
                screenshot = self.capture()
                exists, confidence = self.element_locator.verify_element_state(
                    element_type,
                    screenshot,
                    self.window.id,
                    threshold
                )
                
                if exists == present:
                    return CommandResult(
                        success=True,
                        message=f"Element {element_type} {'found' if present else 'gone'}",
                        timestamp=datetime.now(),
                        duration=time.time() - start_time,
                        element_type=element_type,
                        confidence=confidence
                    )
                
                await asyncio.sleep(0.1)
            
            return CommandResult(
                success=False,
                message=f"Timeout waiting for {element_type}",
                timestamp=datetime.now(),
                duration=timeout,
                element_type=element_type
            )
            
        except Exception as e:
            self.logger.error(f"Wait failed: {str(e)}")
            return CommandResult(
                success=False,
                message=f"Wait failed: {str(e)}",
                timestamp=datetime.now(),
                duration=time.time() - start_time,
                element_type=element_type,
                error=e
            )
    
    def capture(self) -> np.ndarray:
        """Capture window screenshot using PrintWindow."""
        hwnd = self.window.handle
        
        # Get window dimensions
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        # Get window DC and create compatible DC
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        
        # Create bitmap buffer
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        
        try:
            # Capture window contents
            result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
            if result != 1:
                raise RuntimeError("PrintWindow failed")
            
            # Convert to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
        finally:
            # Clean up GDI resources
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
    
    async def process_command(self, command: CursorCommand) -> CommandResult:
        """Process a command in the instance's context with retry logic."""
        self.is_busy = True
        self.last_command = command
        command.started_at = datetime.now()
        start_time = time.time()
        
        while True:
            try:
                if command.command_type == "click":
                    result = await self.click_element(
                        command.params["element_type"],
                        command.params.get("confidence_threshold")
                    )
                elif command.command_type == "wait":
                    result = await self.wait_for_element(
                        command.params["element_type"],
                        command.params.get("present", True),
                        command.params.get("timeout", 5.0),
                        command.params.get("confidence_threshold")
                    )
                else:
                    result = CommandResult(
                        success=False,
                        message=f"Unknown command type: {command.command_type}",
                        timestamp=datetime.now(),
                        duration=time.time() - start_time,
                        retry_count=command._current_retry
                    )
                
                # If successful, break retry loop
                if result.success:
                    break
                    
                # Check if we can retry
                if command.can_retry:
                    command.increment_retry()
                    self.logger.warning(
                        f"Retrying command {command.command_type} "
                        f"(attempt {command._current_retry}/{command.retry_count})"
                    )
                    await asyncio.sleep(command.retry_delay)
                    continue
                    
                # No more retries available
                break
                
            except Exception as e:
                self.logger.error(f"Command failed: {str(e)}")
                if command.can_retry:
                    command.increment_retry()
                    await asyncio.sleep(command.retry_delay)
                    continue
                result = CommandResult(
                    success=False,
                    message=f"Command failed: {str(e)}",
                    timestamp=datetime.now(),
                    duration=time.time() - start_time,
                    error=e,
                    retry_count=command._current_retry
                )
                break
        
        command.completed_at = datetime.now()
        command.result = result
        
        # Process next command in chain if exists and current command succeeded
        if command.has_next and result.success:
            self.logger.info(f"Processing next command in chain")
            next_result = await self.process_command(command.next_command)
            if not next_result.success:
                # If chained command fails, mark this command as failed too
                result.success = False
                result.message += f" (Chain failed: {next_result.message})"
        
        self.is_busy = False
        return result

class CursorInstanceController:
    """Controls multiple Cursor instances for fleet automation."""
    
    def __init__(
        self,
        min_confidence: float = 0.8,
        max_instances: int = 8,
        training_data_dir: str = "./cursor_training_data"
    ):
        self.window_controller = CursorWindowController()
        self.element_locator = create_locator(
            training_data_dir=training_data_dir,
            min_confidence=min_confidence
        )
        self.max_instances = max_instances
        self.min_confidence = min_confidence
        self.logger = logging.getLogger("CursorInstanceController")
        
        # Instance management
        self.instances: Dict[str, CursorInstance] = {}
        self.command_queues: Dict[str, Queue] = {}
        self.state_locks: Dict[str, Lock] = {}
        
        # Add shutdown flag
        self._shutdown = False
        
        # Initialize instances
        self._init_instances()
    
    def _init_instances(self):
        """Initialize controller with available Cursor instances."""
        windows = self.window_controller.detect_all_instances()
        
        for window in windows[:self.max_instances]:
            self.command_queues[window.id] = Queue()
            self.state_locks[window.id] = Lock()
            
            self.instances[window.id] = CursorInstance(
                window=window,
                element_locator=self.element_locator,
                command_queue=self.command_queues[window.id],
                state_lock=self.state_locks[window.id],
                min_confidence=self.min_confidence
            )
            
        self.logger.info(
            f"Initialized {len(self.instances)} Cursor instances"
        )
    
    def get_available_instance(self) -> Optional[CursorInstance]:
        """Get the first non-busy instance."""
        for instance in self.instances.values():
            if not instance.is_busy:
                return instance
        return None
    
    async def queue_command(
        self,
        command: CursorCommand,
        instance_id: Optional[str] = None
    ) -> None:
        """Queue a command for execution on a specific or available instance."""
        if instance_id:
            if instance_id not in self.instances:
                raise ValueError(f"Unknown instance: {instance_id}")
            queue = self.command_queues[instance_id]
        else:
            # Find least busy queue
            queue = min(
                self.command_queues.values(),
                key=lambda q: q.qsize()
            )
        
        await asyncio.get_event_loop().run_in_executor(
            None, queue.put, command
        )
    
    async def shutdown(self):
        """Shutdown all instances cleanly."""
        self._shutdown = True
        shutdown_tasks = []
        for instance in self.instances.values():
            shutdown_tasks.append(instance.shutdown())
        await asyncio.gather(*shutdown_tasks)

    def get_instance_states(self) -> Dict[str, Dict]:
        """Get current state of all instances."""
        states = {}
        for instance_id, instance in self.instances.items():
            with instance.state_lock:
                states[instance_id] = {
                    "busy": instance.is_busy,
                    "last_command": {
                        "type": instance.last_command.command_type,
                        "params": instance.last_command.params,
                        "result": instance.last_command.result.to_dict()
                    } if instance.last_command else None,
                    "window_title": instance.window.title,
                    "minimized": win32gui.IsIconic(instance.window.handle)
                }
        return states

    def chain_commands(self, *commands: CursorCommand) -> CursorCommand:
        """Chain multiple commands together."""
        if not commands:
            raise ValueError("No commands provided")
            
        for i in range(len(commands) - 1):
            commands[i].chain(commands[i + 1])
            
        return commands[0]
    
    async def execute_chain(
        self,
        *commands: CursorCommand,
        instance_id: Optional[str] = None
    ) -> List[CommandResult]:
        """Execute a chain of commands and return all results."""
        if not commands:
            raise ValueError("No commands provided")
            
        # Chain commands
        chain = self.chain_commands(*commands)
        
        # Queue first command (rest will execute via chain)
        await self.queue_command(chain, instance_id)
        
        # Wait for all commands to complete
        if instance_id:
            await asyncio.get_event_loop().run_in_executor(
                None, self.command_queues[instance_id].join
            )
        else:
            for queue in self.command_queues.values():
                await asyncio.get_event_loop().run_in_executor(
                    None, queue.join
                )
        
        # Collect results
        results = []
        current = chain
        while current:
            if current.result:
                results.append(current.result)
            current = current.next_command
            
        return results

async def main():
    """Example usage of CursorInstanceController."""
    controller = CursorInstanceController()
    
    try:
        # Create command chain
        commands = [
            CursorCommand(
                "wait",
                {"element_type": "accept_button", "timeout": 5.0},
                retry_count=3
            ),
            CursorCommand(
                "click",
                {"element_type": "accept_button"},
                retry_count=2
            ),
            CursorCommand(
                "wait",
                {"element_type": "resume_button", "timeout": 5.0},
                retry_count=3
            ),
            CursorCommand(
                "click",
                {"element_type": "resume_button"},
                retry_count=2
            )
        ]
        
        # Execute chain
        results = await controller.execute_chain(*commands)
        
        # Print results
        print("\nCommand chain results:")
        for i, result in enumerate(results):
            print(f"\nCommand {i + 1}:")
            print(json.dumps(result.to_dict(), indent=2))
        
        # Get final states
        states = controller.get_instance_states()
        print("\nFinal instance states:")
        print(json.dumps(states, indent=2))
        
    finally:
        await controller.shutdown()

if __name__ == "__main__":
    asyncio.run(main()) 