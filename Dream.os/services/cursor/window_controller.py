"""Controller for managing multiple Cursor window instances."""

import os
import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
import platform

# OS-specific imports
if platform.system() == 'Windows':
    import win32gui
    import win32con
    import win32process
elif platform.system() == 'Darwin':  # macOS
    try:
        from AppKit import NSWorkspace, NSRunningApplication
    except ImportError:
        raise ImportError("Please install pyobjc-framework-Cocoa for macOS support")
else:  # Linux
    try:
        import Xlib.display
        from Xlib.X import SubstructureNotifyMask, SubstructureRedirectMask
    except ImportError:
        raise ImportError("Please install python-xlib for Linux support")

logger = logging.getLogger(__name__)

@dataclass
class WindowWrapper:
    """Cross-platform window handle wrapper."""
    id: str  # CURSOR-1, CURSOR-2, etc.
    handle: int  # Window handle/id
    title: str
    pid: int
    geometry: Dict[str, int]  # x, y, width, height

class CursorWindowController:
    """Controls multiple Cursor window instances."""
    
    MAX_INSTANCES = 8
    
    def __init__(self):
        self.windows: List[WindowWrapper] = []
        self._os_type = platform.system()
        self._setup_os_specific_handlers()
        
    def _setup_os_specific_handlers(self):
        """Initialize OS-specific window management."""
        if self._os_type == 'Windows':
            self._enum_windows = win32gui.EnumWindows
            self._get_window_text = win32gui.GetWindowText
            self._get_window_rect = win32gui.GetWindowRect
            self._set_foreground = win32gui.SetForegroundWindow
            self._get_window_pid = lambda hwnd: win32process.GetWindowThreadProcessId(hwnd)[1]
        elif self._os_type == 'Darwin':
            self._workspace = NSWorkspace.sharedWorkspace()
        else:  # Linux
            self._display = Xlib.display.Display()
            self._root = self._display.screen().root
            
    def detect_all_instances(self, title_pattern: str = "Cursor") -> List[WindowWrapper]:
        """Detect all Cursor windows in the system."""
        self.windows.clear()
        
        if self._os_type == 'Windows':
            def enum_callback(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = self._get_window_text(hwnd)
                    if title_pattern.lower() in window_title.lower():
                        rect = self._get_window_rect(hwnd)
                        self.windows.append(WindowWrapper(
                            id=f"CURSOR-{len(self.windows) + 1}",
                            handle=hwnd,
                            title=window_title,
                            pid=self._get_window_pid(hwnd),
                            geometry={
                                'x': rect[0],
                                'y': rect[1],
                                'width': rect[2] - rect[0],
                                'height': rect[3] - rect[1]
                            }
                        ))
            
            self._enum_windows(enum_callback, None)
            
        elif self._os_type == 'Darwin':
            running_apps = self._workspace.runningApplications()
            for app in running_apps:
                if title_pattern.lower() in app.localizedName().lower():
                    windows = app.windows()  # Note: May require additional permissions
                    for window in windows:
                        frame = window.frame()
                        self.windows.append(WindowWrapper(
                            id=f"CURSOR-{len(self.windows) + 1}",
                            handle=window.windowNumber(),
                            title=app.localizedName(),
                            pid=app.processIdentifier(),
                            geometry={
                                'x': int(frame.origin.x),
                                'y': int(frame.origin.y),
                                'width': int(frame.size.width),
                                'height': int(frame.size.height)
                            }
                        ))
                        
        else:  # Linux
            def get_window_info(window):
                try:
                    geometry = window.get_geometry()
                    name = window.get_wm_name()
                    pid = window.get_wm_pid()
                    return name, pid, geometry
                except:
                    return None, None, None
            
            for window in self._root.query_tree().children:
                name, pid, geometry = get_window_info(window)
                if name and title_pattern.lower() in name.lower():
                    self.windows.append(WindowWrapper(
                        id=f"CURSOR-{len(self.windows) + 1}",
                        handle=window.id,
                        title=name,
                        pid=pid,
                        geometry={
                            'x': geometry.x,
                            'y': geometry.y,
                            'width': geometry.width,
                            'height': geometry.height
                        }
                    ))
                    
        # Limit to MAX_INSTANCES
        self.windows = self.windows[:self.MAX_INSTANCES]
        logger.info(f"Detected {len(self.windows)} Cursor instances")
        return self.windows
        
    def activate_window(self, window: WindowWrapper) -> bool:
        """Activate and bring a specific window to front."""
        try:
            if self._os_type == 'Windows':
                self._set_foreground(window.handle)
            elif self._os_type == 'Darwin':
                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(window.pid)
                app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
            else:  # Linux
                window_obj = self._display.create_resource_object('window', window.handle)
                window_obj.set_input_focus(Xlib.X.RevertToParent, Xlib.X.CurrentTime)
                window_obj.configure(stack_mode=Xlib.X.Above)
                self._display.sync()
            
            logger.info(f"Activated window {window.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to activate window {window.id}: {e}")
            return False
            
    def get_window_by_id(self, cursor_id: str) -> Optional[WindowWrapper]:
        """Get window wrapper by Cursor ID (e.g., 'CURSOR-1')."""
        for window in self.windows:
            if window.id == cursor_id:
                return window
        return None
        
    def print_window_map(self):
        """Print a formatted map of all detected Cursor windows."""
        if not self.windows:
            print("No Cursor windows detected.")
            return
            
        print("\n=== Cursor Window Map ===")
        for window in self.windows:
            print(f"\n{window.id}:")
            print(f"  Title: {window.title}")
            print(f"  PID: {window.pid}")
            print(f"  Position: ({window.geometry['x']}, {window.geometry['y']})")
            print(f"  Size: {window.geometry['width']}x{window.geometry['height']}")
        print("\n=======================") 