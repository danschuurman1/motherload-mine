import cv2
import mss
import numpy as np
from typing import Tuple

class ScreenCapture:
    """Retina-safe screen capture using mss."""
    def __init__(self) -> None:
        self._sct = mss.mss()

    def grab(self, region: Tuple[int, int, int, int]) -> np.ndarray:
        monitor = {
            "left": int(region[0]),
            "top": int(region[1]),
            "width": int(region[2]),
            "height": int(region[3]),
        }
        raw = self._sct.grab(monitor)
        # Convert to BGR for OpenCV
        frame = np.array(raw)[:, :, :3]
        
        # Handle Retina scaling: resize back to logical dimensions if they don't match
        physical_height, physical_width = frame.shape[:2]
        if physical_width != region[2] or physical_height != region[3]:
            frame = cv2.resize(frame, (region[2], region[3]), interpolation=cv2.INTER_AREA)
        return frame
