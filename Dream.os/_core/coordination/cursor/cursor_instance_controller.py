from .cursor_window_controller import CursorWindowController, WindowWrapper
from .cursor_element_locator import create_locator, BoundingBox # Assuming create_locator is factory
from .cursor_command import CursorCommand # Assuming CursorCommand class exists
from .command_result import CommandResult # Assuming CommandResult class exists
# Need pyautogui or similar for typing
import pyautogui 

logger = logging.getLogger("CursorInstanceController")

class CursorInstance:
    """Controls a single Cursor window instance."""
    
    def __init__(self, 
                 window: WindowWrapper, 
                 element_locator: Any, # Use Any if create_locator returns specific type
                 command_queue: Queue, 
                 state_lock: Lock, 
                 min_confidence: float = 0.8):
        # ... (initialization as before) ...
        pass # Added pass

    # ... (_process_command_queue, shutdown, click_element, wait_for_element as before) ...
    async def _process_command_queue(self):
        # ... (implementation as before) ...
        pass # Added pass
    async def shutdown(self):
        # ... (implementation as before) ...
        pass # Added pass
    async def click_element(self, 
                           element_type: str, 
                           confidence_threshold: Optional[float] = None
                          ) -> CommandResult:
         # ... (implementation as before) ...
         pass # Added pass
    async def wait_for_element(self, 
                              element_type: str, 
                              present: bool = True, 
                              timeout: float = 5.0, 
                              confidence_threshold: Optional[float] = None
                             ) -> CommandResult:
          # ... (implementation as before) ...
          pass # Added pass
          
    def capture(self) -> Optional[np.ndarray]:
        """Capture a screenshot of the window. Returns BGR numpy array or None."""
        # ... (implementation likely using OS-specific APIs or libraries) ...
        # Placeholder implementation
        hwnd = self.window.handle
        try:
            # Using the PrintWindow logic from test_cursor_element_locator as an example
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                self.logger.warning("Window has invalid dimensions, cannot capture.")
                return None

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # PW_RENDERFULLCONTENT (value 2) might capture more reliably than 0
            result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2) 
            
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Clean up GDI resources
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            if result != 1:
                 # PrintWindow can return 0 even on success sometimes, 
                 # but logging a warning might be useful.
                 self.logger.warning(f"PrintWindow returned {result} for window {self.window.id}. Capture might be incomplete.")
                 # Still attempt to return image if possible
                 # return None # Or choose to return None if result is not 1

            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            self.logger.error(f"Failed to capture window {self.window.id}: {e}", exc_info=True)
            # Ensure resources are released even on error if possible (might need more robust cleanup)
            try: win32gui.DeleteObject(saveBitMap.GetHandle()) 
            except: pass
            try: saveDC.DeleteDC() 
            except: pass
            try: mfcDC.DeleteDC() 
            except: pass
            try: win32gui.ReleaseDC(hwnd, hwndDC) 
            except: pass
            return None
        
    async def type_text(self, 
                      element_type: Optional[str], 
                      text: str, 
                      confidence_threshold: Optional[float] = None) -> CommandResult:
        """Types text, optionally focusing on an element first."""
        start_time = time.time()
        bbox = None
        click_result = None
        focused = False

        try:
            # 1. Optional: Find and Click Element to Focus
            if element_type:
                self.logger.info(f"Attempting to focus element '{element_type}' before typing...")
                click_result = await self.click_element(element_type, confidence_threshold)
                if not click_result.success:
                    # Return failure if we couldn't focus the required element
                    return CommandResult(
                        success=False,
                        message=f"Failed to focus element '{element_type}' before typing: {click_result.message}",
                        timestamp=datetime.now(),
                        duration=time.time() - start_time,
                        element_type=element_type,
                        error=click_result.error
                    )
                focused = True
                await asyncio.sleep(0.2) # Small delay after click before typing
            else:
                # Type without focusing a specific element (assumes correct window is active)
                # Ensure window is active
                self.window_controller.activate_window(self.window)
                await asyncio.sleep(0.2)
                focused = True # Assume focus is correct if no element specified
            
            # 2. Type Text using pyautogui
            if focused:
                 self.logger.info(f"Typing text (length {len(text)}): '{text[:50]}...'")
                 # PyAutoGUI interaction should ideally run in a separate thread 
                 # or process to avoid blocking asyncio loop if typing is slow.
                 # For simplicity here, calling directly.
                 try:
                     pyautogui.write(text, interval=0.01) # Small interval between keys
                     message = f"Typed text into '{element_type or 'active window'}'"
                     success = True
                     error = None
                 except Exception as type_e:
                     logger.error(f"pyautogui.write failed: {type_e}", exc_info=True)
                     message = f"Typing failed: {type_e}"
                     success = False
                     error = type_e
            else:
                 # Should not happen if click_element succeeded or no element was specified
                 message = "Focus failed before typing."
                 success = False
                 error = None

            return CommandResult(
                success=success,
                message=message,
                timestamp=datetime.now(),
                duration=time.time() - start_time,
                element_type=element_type,
                confidence=click_result.confidence if click_result else None,
                error=error
            )

        except Exception as e:
            logger.error(f"type_text failed: {str(e)}", exc_info=True)
            return CommandResult(
                success=False,
                message=f"type_text failed: {str(e)}",
                timestamp=datetime.now(),
                duration=time.time() - start_time,
                element_type=element_type,
                error=e
            )

    async def process_command(self, command: CursorCommand) -> CommandResult:
        """Process a single command with retries."""
        self.last_command = command
        command.started_at = datetime.now()
        result = None
        
        action_map = {
            "click": self.click_element,
            "wait": self.wait_for_element,
            "type": self.type_text, # <<< Added type command
            # Add other command types here
        }

        handler = action_map.get(command.command_type)
        if not handler:
            msg = f"Unknown command type: {command.command_type}"
            logger.error(msg)
            return CommandResult(success=False, message=msg, timestamp=datetime.now(), duration=0)

        current_retry = 0
        while current_retry <= command.retry_count:
            try:
                # Use ** to pass params dictionary as keyword arguments
                result = await handler(**command.params)
                result.retry_count = current_retry

                if result.success:
                    logger.info(f"Command '{command.command_type}' succeeded.")
                    break # Exit retry loop on success
                else:
                    logger.warning(f"Command '{command.command_type}' failed (Attempt {current_retry + 1}/{command.retry_count + 1}): {result.message}")
                    if current_retry >= command.retry_count:
                         logger.error(f"Command '{command.command_type}' failed after max retries.")
                         break # Max retries reached

            except Exception as e:
                logger.error(f"Exception during command '{command.command_type}' (Attempt {current_retry + 1}): {e}", exc_info=True)
                if current_retry >= command.retry_count:
                    result = CommandResult(success=False, message=str(e), timestamp=datetime.now(), duration=0, error=e, retry_count=current_retry)
                    break # Max retries reached
            
            # Wait before retrying
            current_retry += 1
            if current_retry <= command.retry_count:
                 logger.info(f"Retrying in {command.retry_delay}s...")
                 await asyncio.sleep(command.retry_delay)
                 
        command.completed_at = datetime.now()
        command.result = result
        return result

# ... (CursorInstanceController class remains the same, but execute_chain needs update) ...
class CursorInstanceController:
    # ... (__init__, _init_instances, get_available_instance, queue_command, shutdown, get_instance_states, chain_commands as before) ...
    def __init__(self, 
                 min_confidence: float = 0.8, 
                 max_instances: int = 8, 
                 training_data_dir: str = "./cursor_training_data"):
        # ... (implementation as before) ...
        pass # Added pass
    def _init_instances(self):
        # ... (implementation as before) ...
        pass # Added pass
    def get_available_instance(self) -> Optional[CursorInstance]:
        # ... (implementation as before) ...
        pass # Added pass
    async def queue_command(self, 
                           command: CursorCommand, 
                           instance_id: Optional[str] = None
                          ) -> None:
         # ... (implementation as before) ...
         pass # Added pass
    async def shutdown(self):
        # ... (implementation as before) ...
        pass # Added pass
    def get_instance_states(self) -> Dict[str, Dict]:
        # ... (implementation as before) ...
        pass # Added pass
    def chain_commands(self, *commands: CursorCommand) -> CursorCommand:
         # ... (implementation as before) ...
         pass # Added pass
         
    async def execute_chain(
        self, 
        *commands: CursorCommand, 
        instance: Optional[CursorInstance] = None, # Changed from instance_id
        instance_id: Optional[str] = None # Keep for backward compatibility or alternative lookup?
    ) -> List[CommandResult]:
        """Executes a chain of commands on a specific or available instance."""
        results: List[CommandResult] = []
        target_instance = instance

        # Determine target instance
        if not target_instance:
            if instance_id:
                target_instance = self.get_instance_by_id(instance_id)
            else:
                target_instance = self.get_available_instance()

        if not target_instance:
            msg = "No available/specified instance to execute command chain."
            logger.error(msg)
            # Return a single failure result for the chain
            return [CommandResult(success=False, message=msg, timestamp=datetime.now(), duration=0)] 

        logger.info(f"Executing command chain ({len(commands)} commands) on instance {target_instance.window.id}")
        
        # Ensure instance isn't busy (using the state lock)
        # This logic might need refinement based on how instance busyness is truly managed
        async with target_instance.state_lock:
            if target_instance.is_busy:
                msg = f"Instance {target_instance.window.id} is busy. Cannot execute chain."
                logger.warning(msg)
                return [CommandResult(success=False, message=msg, timestamp=datetime.now(), duration=0)] 
            target_instance.is_busy = True
            
        try:
            current_command: Optional[CursorCommand] = commands[0] if commands else None
            while current_command:
                # Pass command to the instance's process_command method
                result = await target_instance.process_command(current_command)
                results.append(result)
                
                if not result.success:
                    logger.error(f"Command '{current_command.command_type}' failed in chain. Stopping chain execution.")
                    break # Stop chain on failure
                
                # Move to the next command in the explicit chain (if defined)
                # If using *commands, we just iterate through them.
                # The logic below assumes the chain might be defined via .next_command
                # It needs clarification: are we executing the sequence passed via *commands OR 
                # the chain defined by command.next_command? Assuming *commands sequence for now.
                # current_command = current_command.next_command 
                
                # Find the index of the current command to get the next one from *commands
                try:
                    current_index = commands.index(current_command)
                    if current_index + 1 < len(commands):
                         current_command = commands[current_index + 1]
                    else:
                         current_command = None # End of sequence
                except ValueError:
                     logger.error("Internal error: Could not find current command in sequence.")
                     current_command = None # Should not happen
                     break
        finally:
            # Release instance busy flag
             async with target_instance.state_lock:
                 target_instance.is_busy = False
                 logger.info(f"Instance {target_instance.window.id} released.")

        return results

    def get_instance_by_id(self, instance_id: str) -> Optional[CursorInstance]:
        """Helper to get a specific instance by its ID."""
        for instance in self.instances:
            if instance.window.id == instance_id:
                return instance
        logger.warning(f"Instance with ID '{instance_id}' not found.")
        return None

# ... (main demo function if present) ...
async def main():
    # ... (implementation as before) ...
    pass # Added pass 