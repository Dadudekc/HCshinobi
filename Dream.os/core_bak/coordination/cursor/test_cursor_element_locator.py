"""Integration test and visualization for CursorElementLocator."""

import cv2
import numpy as np
import argparse
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
import win32gui
import win32ui
import win32con
import win32api
from PIL import Image
import logging
from datetime import datetime

from cursor_window_controller import CursorWindowController, WindowWrapper
from cursor_element_locator import create_locator, BoundingBox

class PerformanceMetrics:
    """Tracks performance metrics for window capture and element detection."""
    
    def __init__(self):
        self.capture_times = []
        self.detection_times = []
        self.total_frames = 0
        self.start_time = time.time()
        
    def add_capture_time(self, duration: float):
        self.capture_times.append(duration)
        
    def add_detection_time(self, duration: float):
        self.detection_times.append(duration)
        self.total_frames += 1
        
    @property
    def avg_capture_ms(self) -> float:
        return sum(self.capture_times) * 1000 / len(self.capture_times) if self.capture_times else 0
        
    @property
    def avg_detection_ms(self) -> float:
        return sum(self.detection_times) * 1000 / len(self.detection_times) if self.detection_times else 0
        
    @property
    def fps(self) -> float:
        elapsed = time.time() - self.start_time
        return self.total_frames / elapsed if elapsed > 0 else 0
        
    def __str__(self) -> str:
        return (
            f"FPS: {self.fps:.1f} | "
            f"Capture: {self.avg_capture_ms:.1f}ms | "
            f"Detection: {self.avg_detection_ms:.1f}ms"
        )

class ElementDetectionVisualizer:
    """Visualizes element detection results on live Cursor window screenshots."""
    
    # Color scheme for different element types (BGR format)
    COLORS = {
        "resume_button": (0, 255, 0),    # Green
        "accept_button": (0, 255, 255),  # Yellow
        "accept_all_button": (255, 165, 0),  # Orange
        "copy_message_button": (255, 0, 0),  # Blue
        "chat_input": (128, 0, 128),     # Purple
        "send_button": (0, 128, 255),    # Light Blue
        "stop_button": (0, 0, 255)       # Red
    }
    
    def __init__(
        self,
        window_controller: CursorWindowController,
        element_locator: create_locator,
        output_dir: Optional[str] = None
    ):
        self.window_controller = window_controller
        self.element_locator = element_locator
        self.output_dir = Path(output_dir) if output_dir else None
        if self.output_dir:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = PerformanceMetrics()
        self.logger = logging.getLogger(__name__)
    
    def capture_window(self, window: WindowWrapper) -> np.ndarray:
        """Capture a screenshot of a specific window using Win32 PrintWindow."""
        start_time = time.time()
        hwnd = window.handle
        
        # Briefly activate window if not minimized (helps with rendering)
        if win32gui.IsIconic(hwnd):
            self.logger.info(f"Window {window.id} is minimized - capturing headlessly")
        else:
            self.window_controller.activate_window(window)
            time.sleep(0.2)
        
        # Get window dimensions
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        try:
            # Get window device context
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Create bitmap buffer
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Capture window contents
            result = win32gui.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
            
            if result != 1:
                raise RuntimeError(f"PrintWindow failed for window {window.id}")
            
            # Convert bitmap to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Track performance
            capture_time = time.time() - start_time
            self.metrics.add_capture_time(capture_time)
            
            # Clean up GDI resources
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            self.logger.error(f"Failed to capture window {window.id}: {str(e)}")
            raise
    
    def draw_detection(
        self,
        image: np.ndarray,
        bbox: BoundingBox,
        element_type: str
    ) -> np.ndarray:
        """Draw detection box and label on image."""
        color = self.COLORS.get(element_type, (255, 255, 255))
        
        # Draw bounding box
        cv2.rectangle(
            image,
            (bbox.x, bbox.y),
            (bbox.x + bbox.width, bbox.y + bbox.height),
            color,
            2
        )
        
        # Draw label with confidence
        label = f"{element_type}: {bbox.confidence:.2f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        thickness = 1
        
        # Get text size for background rectangle
        (text_width, text_height), baseline = cv2.getTextSize(
            label, font, font_scale, thickness
        )
        
        # Draw label background
        cv2.rectangle(
            image,
            (bbox.x, bbox.y - text_height - baseline - 5),
            (bbox.x + text_width, bbox.y),
            color,
            -1
        )
        
        # Draw text
        cv2.putText(
            image,
            label,
            (bbox.x, bbox.y - baseline - 5),
            font,
            font_scale,
            (0, 0, 0),  # Black text
            thickness
        )
        
        return image
    
    def visualize_detections(
        self,
        window: WindowWrapper,
        target_element: Optional[str] = None,
        save: bool = False
    ):
        """Visualize element detections for a window."""
        try:
            # Capture window
            screenshot = self.capture_window(window)
            original = screenshot.copy()
            
            # Detect elements
            detect_start = time.time()
            if target_element:
                bbox = self.element_locator.detect_element(
                    target_element, screenshot, window.id
                )
                if bbox:
                    screenshot = self.draw_detection(
                        screenshot, bbox, target_element
                    )
            else:
                detections = self.element_locator.detect_all_elements(
                    screenshot, window.id
                )
                for element_type, bbox in detections.items():
                    screenshot = self.draw_detection(
                        screenshot, bbox, element_type
                    )
                    
            # Track detection performance
            self.metrics.add_detection_time(time.time() - detect_start)
            
            # Add performance overlay
            cv2.putText(
                screenshot,
                str(self.metrics),
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
            
            # Display results
            cv2.imshow(f"Detections - {window.id}", screenshot)
            
            if save and self.output_dir:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # Save original
                cv2.imwrite(
                    str(self.output_dir / f"original_{timestamp}.png"),
                    original
                )
                # Save annotated
                cv2.imwrite(
                    str(self.output_dir / f"detected_{timestamp}.png"),
                    screenshot
                )
            
            print(f"\nPress 'q' to quit, 's' to save current view, any other key to refresh")
            print(f"Performance: {self.metrics}")
            
            while True:
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    if self.output_dir:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        cv2.imwrite(
                            str(self.output_dir / f"detected_{timestamp}.png"),
                            screenshot
                        )
                        print(f"Saved detection view to {self.output_dir}")
                    else:
                        print("No output directory specified!")
                elif key != 255:  # Any other key
                    return self.visualize_detections(
                        window, target_element, save
                    )
            
            cv2.destroyAllWindows()
            
        except Exception as e:
            self.logger.error(f"Error during visualization: {e}")
            cv2.destroyAllWindows()

def main():
    parser = argparse.ArgumentParser(
        description="Test and visualize Cursor UI element detection"
    )
    parser.add_argument(
        "--window-id",
        type=str,
        help="Target Cursor window ID (e.g., CURSOR-1)"
    )
    parser.add_argument(
        "--element",
        type=str,
        help="Specific element type to detect"
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.8,
        help="Minimum confidence threshold"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save detection results"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./detection_results",
        help="Directory to save results"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize components
    window_controller = CursorWindowController()
    element_locator = create_locator(
        min_confidence=args.confidence,
        debug=True
    )
    
    visualizer = ElementDetectionVisualizer(
        window_controller,
        element_locator,
        args.output_dir if args.save else None
    )
    
    # Get available windows
    windows = window_controller.detect_all_instances()
    if not windows:
        print("No Cursor windows detected!")
        return
    
    # Filter to target window if specified
    if args.window_id:
        windows = [w for w in windows if w.id == args.window_id]
        if not windows:
            print(f"No window found with ID: {args.window_id}")
            return
    
    # Run visualization for each window
    for window in windows:
        print(f"\nProcessing window: {window.id} - {window.title}")
        visualizer.visualize_detections(
            window,
            args.element,
            args.save
        )

if __name__ == "__main__":
    main() 