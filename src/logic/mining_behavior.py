import time
import random
import math
import cv2
import numpy as np
import pyautogui
from typing import Optional, Tuple, List
from pathlib import Path

def bezier_curve(p0, p1, p2, p3, t):
    """Calculate point on a cubic Bezier curve."""
    return (
        (1 - t)**3 * p0 +
        3 * (1 - t)**2 * t * p1 +
        3 * (1 - t) * t**2 * p2 +
        t**3 * p3
    )

def move_mouse_bezier(target_x, target_y):
    """Move mouse to target using a cubic Bezier curve for humanization."""
    start_x, start_y = pyautogui.position()
    
    # Control points for the curve
    cp1_x = start_x + (target_x - start_x) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
    cp1_y = start_y + (target_y - start_y) * random.uniform(0.1, 0.4) + random.randint(-50, 50)
    cp2_x = start_x + (target_x - start_x) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
    cp2_y = start_y + (target_y - start_y) * random.uniform(0.6, 0.9) + random.randint(-50, 50)
    
    steps = random.randint(15, 30)
    for i in range(steps + 1):
        t = i / steps
        x = bezier_curve(start_x, cp1_x, cp2_x, target_x, t)
        y = bezier_curve(start_y, cp1_y, cp2_y, target_y, t)
        pyautogui.moveTo(x, y)
        time.sleep(random.uniform(0.005, 0.015))

class MiningBot:
    def __init__(self, colors):
        self.colors = colors
        self.running = False
        self.window_rect = (0, 0, 800, 600) # (left, top, width, height)
        self._last_click_pos = None

    def set_window(self, left, top, width, height):
        self.window_rect = (left, top, width, height)

    def random_jitter(self, val, range_px=2):
        """Add slight random offset to simulate human eye movement."""
        return val + random.uniform(-range_px, range_px)

    def mine_ore(self) -> bool:
        """
        Refined Mining State:
        1. Search for ore clusters using contours.
        2. Select best target (largest/closest).
        3. Humanized click (Gaussian, Bezier, unique pixel).
        4. Monitor 5x5 cluster for depletion.
        """
        # 1. Search Phase
        clusters = self._find_ore_contours()
        if not clusters:
            print("No active ore detected.")
            return False

        # 2. Target Selection (Largest contour area)
        # Each cluster: (centroid_x, centroid_y, contour)
        best_target = max(clusters, key=lambda x: cv2.contourArea(x[2]))
        target_x, target_y, contour = best_target

        # 3. Humanized Click
        # Ensure we click within the inner 60% of the contour
        click_x, click_y = self._get_safe_gaussian_click(contour, target_x, target_y)
        
        # Unique pixel check (avoid repeating exact coordinate)
        if (click_x, click_y) == self._last_click_pos:
            click_x += random.choice([-1, 1])
            click_y += random.choice([-1, 1])
        
        print(f"Moving to ore at ({click_x}, {click_y})...")
        move_mouse_bezier(click_x, click_y)
        pyautogui.click()
        self._last_click_pos = (click_x, click_y)

        # 4. Persistence Monitoring
        return self._monitor_depletion_lock(click_x, click_y)

    def _get_safe_gaussian_click(self, contour, cx, cy) -> Tuple[int, int]:
        """Calculate a click point using Gaussian distribution within the contour's inner 60%."""
        # Get bounding box for variance calculation
        x, y, w, h = cv2.boundingRect(contour)
        
        # Use standard deviation relative to 60% of the width/height
        std_x = (w * 0.3) / 3 
        std_y = (h * 0.3) / 3
        
        for _ in range(10): # Try a few times to get a point inside the contour
            rx = int(random.gauss(cx, std_x))
            ry = int(random.gauss(cy, std_y))
            
            # Check if (rx, ry) is within the contour (relative to window)
            # pointPolygonTest expects points relative to contour coordinates
            rel_px = rx - self.window_rect[0]
            rel_py = ry - self.window_rect[1]
            if cv2.pointPolygonTest(contour, (rel_px, rel_py), False) >= 0:
                return (rx, ry)
        
        return (cx, cy) # Fallback to centroid

    def _find_ore_contours(self) -> List[Tuple[int, int, np.ndarray]]:
        """Find ore using cv2.findContours and return centroids."""
        profile = self.colors.get("ore_active_color")
        if not profile or not profile.enabled:
            return []

        left, top, width, height = self.window_rect
        # Capture window with jitter
        jitter_x = self.random_jitter(left)
        jitter_y = self.random_jitter(top)
        
        screenshot = np.array(pyautogui.screenshot(region=(int(jitter_x), int(jitter_y), width, height)))
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        lower = np.array([profile.b - profile.tolerance, profile.g - profile.tolerance, profile.r - profile.tolerance])
        upper = np.array([profile.b + profile.tolerance, profile.g + profile.tolerance, profile.r + profile.tolerance])
        
        mask = cv2.inRange(screenshot, lower, upper)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        results = []
        for cnt in contours:
            if cv2.contourArea(cnt) > 20:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"]) + int(jitter_x)
                    cy = int(M["m01"] / M["m00"]) + int(jitter_y)
                    results.append((cx, cy, cnt))
        return results

    def _monitor_depletion_lock(self, x, y, timeout=20.0) -> bool:
        """Monitor a 5x5 cluster around (x, y) until depleted color appears or timeout."""
        start_time = time.time()
        depleted_profile = self.colors.get("ore_depleted_color")
        
        print(f"Waiting for depletion at ({x}, {y})...")
        while time.time() - start_time < timeout:
            if not self.running: return False
            
            # Check 5x5 cluster around (x, y)
            # pyautogui.screenshot is slow, so we just check pixels in the cluster
            is_depleted = False
            match_count = 0
            
            # Sample 5x5 cluster
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    px = x + dx
                    py = y + dy
                    r, g, b = pyautogui.pixel(int(px), int(py))
                    dist = math.sqrt((r - depleted_profile.r)**2 + (g - depleted_profile.g)**2 + (b - depleted_profile.b)**2)
                    if dist <= depleted_profile.tolerance:
                        match_count += 1
            
            # If > 50% of pixels match depleted color, consider it gone
            if match_count >= 13:
                print("Depletion detected via pixel cluster.")
                time.sleep(random.uniform(0.8, 2.4)) # Humanized delay
                return True
            
            time.sleep(0.5)
            
        print("Mining state timed out.")
        return False

    def check_level(self) -> bool:
        """Dynamic check for upper level."""
        profile = self.colors.get("ladder_descend_color")
        if not profile: return False
        
        left, top, width, height = self.window_rect
        screenshot = np.array(pyautogui.screenshot(region=(left, top, width, height)))
        screenshot = cv2.cvtColor(screenshot, cv2.COLOR_RGB2BGR)
        
        lower = np.array([profile.b - profile.tolerance, profile.g - profile.tolerance, profile.r - profile.tolerance])
        upper = np.array([profile.b + profile.tolerance, profile.g + profile.tolerance, profile.r + profile.tolerance])
        
        mask = cv2.inRange(screenshot, lower, upper)
        return np.any(mask > 0)
