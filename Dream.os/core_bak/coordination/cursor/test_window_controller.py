"""Test script for CursorWindowController."""

import time
from cursor_window_controller import CursorWindowController

def test_window_detection():
    """Test detecting and activating Cursor windows."""
    controller = CursorWindowController()
    
    print("Scanning for Cursor windows...")
    windows = controller.detect_all_instances()
    
    if not windows:
        print("No Cursor windows found. Please open at least one Cursor instance.")
        return
        
    # Print initial window map
    controller.print_window_map()
    
    # Test window activation
    print("\nTesting window activation sequence...")
    for window in windows:
        print(f"\nActivating {window.id}...")
        if controller.activate_window(window):
            print("✓ Window activated successfully")
        else:
            print("✗ Failed to activate window")
        time.sleep(1)  # Give time to visually verify
        
    print("\nWindow controller test complete!")

if __name__ == "__main__":
    test_window_detection() 