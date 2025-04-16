"""Dream.OS Base Window Component."""

from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

class DreamOSWindow(QMainWindow):
    """Base window class for Dream.OS GUI components."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set window flags
        self.setWindowFlags(
            Qt.Window |
            Qt.CustomizeWindowHint |
            Qt.WindowTitleHint |
            Qt.WindowSystemMenuHint |
            Qt.WindowMinMaxButtonsHint |
            Qt.WindowCloseButtonHint
        )
        
        # Set minimum size
        self.setMinimumSize(QSize(800, 600))
        
        # Set window icon
        self.setWindowIcon(QIcon("assets/icons/dream_os.png"))
        
        # Initialize window state
        self._maximized = False
        self._fullscreen = False
    
    def toggleMaximized(self):
        """Toggle window maximized state."""
        if self.isMaximized():
            self.showNormal()
            self._maximized = False
        else:
            self.showMaximized()
            self._maximized = True
    
    def toggleFullscreen(self):
        """Toggle window fullscreen state."""
        if self.isFullScreen():
            if self._maximized:
                self.showMaximized()
            else:
                self.showNormal()
            self._fullscreen = False
        else:
            self.showFullScreen()
            self._fullscreen = True
    
    def apply_theme(self):
        """Apply Dream.OS theme to the window.
        
        This method should be overridden by subclasses to apply
        specific theming to their components.
        """
        pass 