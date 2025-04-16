"""Real-time UI element detection for Cursor instances."""

import cv2
import numpy as np
import json
from pathlib import Path
from typing import Optional, Dict, Tuple, List
from dataclasses import dataclass
import logging

@dataclass
class BoundingBox:
    """Represents a detected UI element's location."""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    
    @property
    def center(self) -> Tuple[int, int]:
        """Get the center point of the bounding box."""
        return (
            self.x + self.width // 2,
            self.y + self.height // 2
        )
    
    @property
    def area(self) -> int:
        """Get the area of the bounding box."""
        return self.width * self.height
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "confidence": self.confidence,
            "center": self.center
        }

class CursorElementLocator:
    """Detects UI elements in Cursor window screenshots."""
    
    def __init__(
        self,
        training_data_dir: str = "./cursor_training_data",
        min_confidence: float = 0.8,
        debug: bool = False
    ):
        self.training_dir = Path(training_data_dir)
        self.min_confidence = min_confidence
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        
        # Template cache: {window_id: {element_type: [templates]}}
        self.templates: Dict[str, Dict[str, List[np.ndarray]]] = {}
        
        # Load templates for all windows
        self._load_templates()
        
    def _load_templates(self):
        """Load and cache templates from training data."""
        for window_dir in self.training_dir.glob("CURSOR-*"):
            window_id = window_dir.name
            self.templates[window_id] = {}
            
            metadata_file = window_dir / "labels.json"
            if not metadata_file.exists():
                continue
                
            try:
                metadata = json.loads(metadata_file.read_text())
                for entry in metadata:
                    element_type = entry["element_type"]
                    crop_path = Path(entry["cropped_image"])
                    
                    if not crop_path.exists():
                        self.logger.warning(f"Missing template: {crop_path}")
                        continue
                        
                    template = cv2.imread(str(crop_path))
                    if template is None:
                        self.logger.warning(f"Failed to load template: {crop_path}")
                        continue
                        
                    if element_type not in self.templates[window_id]:
                        self.templates[window_id][element_type] = []
                        
                    self.templates[window_id][element_type].append(template)
                    
                self.logger.info(
                    f"Loaded {len(self.templates[window_id])} element types "
                    f"for {window_id}"
                )
                    
            except Exception as e:
                self.logger.error(f"Error loading templates for {window_id}: {e}")
                continue
    
    def detect_element(
        self,
        element_type: str,
        screenshot: np.ndarray,
        window_id: str,
        method: int = cv2.TM_CCOEFF_NORMED
    ) -> Optional[BoundingBox]:
        """
        Detect a specific UI element in the screenshot.
        
        Args:
            element_type: Type of element to detect (e.g., "resume_button")
            screenshot: numpy array of the window screenshot
            window_id: ID of the Cursor window (e.g., "CURSOR-1")
            method: OpenCV template matching method
            
        Returns:
            BoundingBox if element is found with confidence > min_confidence,
            None otherwise
        """
        if window_id not in self.templates:
            self.logger.warning(f"No templates found for window {window_id}")
            return None
            
        if element_type not in self.templates[window_id]:
            self.logger.warning(
                f"No templates for {element_type} in window {window_id}"
            )
            return None
            
        best_match = None
        best_confidence = -1
        
        # Try all templates for this element type
        for template in self.templates[window_id][element_type]:
            # Ensure images are same depth and type
            if template.shape[-1] != screenshot.shape[-1]:
                continue
                
            try:
                # Get correlation map
                result = cv2.matchTemplate(screenshot, template, method)
                min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                
                # Different methods use different score interpretations
                confidence = max_val if method in [cv2.TM_CCOEFF_NORMED] else 1 - min_val
                
                if confidence > best_confidence:
                    h, w = template.shape[:2]
                    best_match = BoundingBox(
                        x=max_loc[0],
                        y=max_loc[1],
                        width=w,
                        height=h,
                        confidence=confidence
                    )
                    best_confidence = confidence
                    
            except Exception as e:
                self.logger.error(
                    f"Error matching template for {element_type}: {e}"
                )
                continue
                
        if best_match and best_match.confidence >= self.min_confidence:
            if self.debug:
                self.logger.info(
                    f"Found {element_type} with confidence {best_match.confidence:.2f}"
                )
            return best_match
            
        return None
    
    def detect_all_elements(
        self,
        screenshot: np.ndarray,
        window_id: str
    ) -> Dict[str, BoundingBox]:
        """
        Detect all known UI elements in the screenshot.
        
        Args:
            screenshot: numpy array of the window screenshot
            window_id: ID of the Cursor window
            
        Returns:
            Dictionary mapping element_type to BoundingBox for all detected elements
        """
        results = {}
        
        if window_id not in self.templates:
            return results
            
        for element_type in self.templates[window_id].keys():
            bbox = self.detect_element(element_type, screenshot, window_id)
            if bbox:
                results[element_type] = bbox
                
        return results
    
    def verify_element_state(
        self,
        element_type: str,
        screenshot: np.ndarray,
        window_id: str,
        required_confidence: float = None
    ) -> Tuple[bool, float]:
        """
        Check if an element exists and meets confidence threshold.
        
        Args:
            element_type: Type of element to verify
            screenshot: numpy array of the window screenshot
            window_id: ID of the Cursor window
            required_confidence: Optional override for min_confidence
            
        Returns:
            Tuple of (exists: bool, confidence: float)
        """
        bbox = self.detect_element(element_type, screenshot, window_id)
        if not bbox:
            return False, 0.0
            
        threshold = required_confidence or self.min_confidence
        return bbox.confidence >= threshold, bbox.confidence

def create_locator(
    training_data_dir: str = "./cursor_training_data",
    min_confidence: float = 0.8,
    debug: bool = False
) -> CursorElementLocator:
    """Factory function to create a configured element locator."""
    return CursorElementLocator(
        training_data_dir=training_data_dir,
        min_confidence=min_confidence,
        debug=debug
    ) 