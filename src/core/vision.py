import random
import cv2
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple

@dataclass
class DetectedObject:
    contour: np.ndarray
    centroid: Tuple[int, int]
    bounds: Tuple[int, int, int, int]
    area: int
    click_point: Tuple[int, int]

class ObjectFinder:
    """Detect matching color regions and find safe interior click points."""
    def __init__(self, profile, min_blob_area: int = 20, click_padding: int = 4) -> None:
        self._profile = profile
        self._min_blob_area = min_blob_area
        self._click_padding = click_padding

    def find_objects(self, frame: np.ndarray, region_offset: Tuple[int, int] = (0, 0)) -> List[DetectedObject]:
        # Build mask using distance in color space
        arr = frame.astype(np.int32)
        b, g, r = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        dist = np.sqrt((r - self._profile.r)**2 + (g - self._profile.g)**2 + (b - self._profile.b)**2)
        mask = (dist <= self._profile.tolerance).astype(np.uint8) * 255
        
        # Clean mask
        kernel = np.ones((3, 3), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=1)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        results: List[DetectedObject] = []
        for contour in contours:
            area = int(cv2.contourArea(contour))
            if area < self._min_blob_area:
                continue

            moments = cv2.moments(contour)
            if not moments["m00"]:
                continue

            cx = int(moments["m10"] / moments["m00"])
            cy = int(moments["m01"] / moments["m00"])
            x, y, w, h = cv2.boundingRect(contour)
            click_point = self._random_point_in_contour(contour, x, y, w, h)
            if click_point is None:
                continue

            results.append(DetectedObject(
                contour=contour,
                centroid=(cx + region_offset[0], cy + region_offset[1]),
                bounds=(x + region_offset[0], y + region_offset[1], w, h),
                area=area,
                click_point=(click_point[0] + region_offset[0], click_point[1] + region_offset[1])
            ))
        return results

    def _random_point_in_contour(self, contour, x, y, w, h) -> Optional[Tuple[int, int]]:
        local_mask = np.zeros((h, w), dtype=np.uint8)
        shifted = contour.copy()
        shifted[:, 0, 0] -= x
        shifted[:, 0, 1] -= y
        cv2.drawContours(local_mask, [shifted], contourIdx=-1, color=255, thickness=-1)

        if self._click_padding > 0:
            distance = cv2.distanceTransform(local_mask, cv2.DIST_L2, 3)
            valid = np.argwhere(distance >= self._click_padding)
        else:
            valid = np.argwhere(local_mask > 0)

        if len(valid) == 0:
            valid = np.argwhere(local_mask > 0)
        if len(valid) == 0:
            return None

        scored = valid.tolist()
        # Filter for points closer to the interior
        if self._click_padding > 0:
            scored = sorted(scored, key=lambda p: float(distance[p[0], p[1]]), reverse=True)
            
        safe_pool = scored[: max(1, min(24, len(scored) // 3))]
        chosen = random.choice(safe_pool)
        return x + int(chosen[1]), y + int(chosen[0])
