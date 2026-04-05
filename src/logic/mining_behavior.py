import time
import random
import cv2
import numpy as np
from typing import Optional, Tuple, List
from core.screen import ScreenCapture
from core.mouse import MouseController
from core.vision import ObjectFinder, DetectedObject

class MiningBot:
    def __init__(self, colors):
        self.colors = colors
        self.running = False
        self.window_rect = (0, 0, 800, 600)
        self._screen = ScreenCapture()
        self._mouse = MouseController()
        
        # State
        self._active_target: Optional[DetectedObject] = None

    def set_window(self, left, top, width, height):
        self.window_rect = (left, top, width, height)

    def mine_ore(self) -> bool:
        """Find and click ore using FullScreenFinder-style logic."""
        profile = self.colors.get("ore_active_color")
        if not profile or not profile.enabled:
            return False

        # 1. Grab Full Window Frame
        frame = self._screen.grab(self.window_rect)
        
        # 2. Find All Ore Objects
        finder = ObjectFinder(profile, min_blob_area=25, click_padding=5)
        # Offset results by window origin for screen-space clicking
        ores = finder.find_objects(frame, region_offset=(self.window_rect[0], self.window_rect[1]))
        
        if not ores:
            print("No active ore found.")
            return False

        # 3. Choose Target (Closest to screen center/player)
        cx, cy = self.window_rect[0] + self.window_rect[2]//2, self.window_rect[1] + self.window_rect[3]//2
        target = self._choose_best_ore(ores, (cx, cy))
        
        if target:
            print(f"Targeting ore at {target.click_point} (Area: {target.area})")
            # 4. Humanized Click
            self._mouse.move_and_click(target.click_point)
            self._active_target = target
            
            # 5. Wait for Depletion (Willow-style localized monitoring)
            return self._wait_for_depletion(target)
            
        return False

    def _choose_best_ore(self, ores: List[DetectedObject], anchor: Tuple[int, int]) -> Optional[DetectedObject]:
        if not ores: return None
        # Score by distance + slight randomness to avoid bot-like pattern
        def score(o: DetectedObject):
            dist = math.sqrt((o.centroid[0]-anchor[0])**2 + (o.centroid[1]-anchor[1])**2)
            return dist + random.uniform(0, 20)
        
        import math # ensure math is available for score
        return min(ores, key=score)

    def _wait_for_depletion(self, target: DetectedObject, timeout: float = 25.0) -> bool:
        """Monitor target region for color change."""
        start_time = time.time()
        active_profile = self.colors.get("ore_active_color")
        depleted_profile = self.colors.get("ore_depleted_color")
        
        # Monitor slightly larger area than bounds
        pad = 10
        monitor_region = (
            target.bounds[0] - pad,
            target.bounds[1] - pad,
            target.bounds[2] + (pad*2),
            target.bounds[3] + (pad*2)
        )

        print(f"Monitoring ore at {target.centroid}...")
        while time.time() - start_time < timeout:
            if not self.running: return False
            
            frame = self._screen.grab(monitor_region)
            arr = frame.astype(np.int32)
            b, g, r = arr[:,:,0], arr[:,:,1], arr[:,:,2]
            
            # Check if active color is still present
            active_dist = np.sqrt((r - active_profile.r)**2 + (g - active_profile.g)**2 + (b - active_profile.b)**2)
            active_pixels = np.sum(active_dist <= active_profile.tolerance)
            
            # Check for depleted color
            depleted_dist = np.sqrt((r - depleted_profile.r)**2 + (g - depleted_profile.g)**2 + (b - depleted_profile.b)**2)
            depleted_pixels = np.sum(depleted_dist <= depleted_profile.tolerance)
            
            # Transition: active color gone or depleted color dominant
            if active_pixels < (target.area * 0.2) or depleted_pixels > (target.area * 0.5):
                print(f"Depletion detected (Active: {active_pixels}, Depleted: {depleted_pixels})")
                time.sleep(random.uniform(0.8, 2.2))
                return True
                
            time.sleep(0.6)
        
        print("Depletion wait timed out.")
        return False

    def check_level(self) -> bool:
        """Check for ladder color in viewport."""
        profile = self.colors.get("ladder_descend_color")
        if not profile or not profile.enabled: return True # Default to True if profile not setup
        
        frame = self._screen.grab(self.window_rect)
        arr = frame.astype(np.int32)
        b, g, r = arr[:,:,0], arr[:,:,1], arr[:,:,2]
        dist = np.sqrt((r - profile.r)**2 + (g - profile.g)**2 + (b - profile.b)**2)
        return np.any(dist <= profile.tolerance)
