import math
import random
import time
from typing import List, Optional, Tuple
from pynput.mouse import Button, Controller as MouseControllerBackend

class MouseController:
    """Bezier mouse movement with per-click jitter."""
    def __init__(self) -> None:
        self._mouse = MouseControllerBackend()
        self._last_click: Optional[Tuple[int, int]] = None

    def move_and_click(self, target: Tuple[int, int]) -> Tuple[int, int]:
        destination = self._unique_destination(target)
        start_pos = self.position()
        path = self._bezier_path(start_pos, destination, steps=random.randint(22, 40))
        for point in path:
            self._mouse.position = point
            time.sleep(random.uniform(0.006, 0.016))
        time.sleep(random.uniform(0.04, 0.09))
        self._mouse.click(Button.left, 1)
        self._last_click = destination
        return destination

    def position(self) -> Tuple[int, int]:
        pos = self._mouse.position
        return int(pos[0]), int(pos[1])

    def _unique_destination(self, target: Tuple[int, int]) -> Tuple[int, int]:
        for _ in range(12):
            jittered = (
                target[0] + random.randint(-2, 2),
                target[1] + random.randint(-2, 2),
            )
            if jittered != self._last_click:
                return jittered
        return target

    def _bezier_path(self, start: Tuple[int, int], end: Tuple[int, int], steps: int) -> List[Tuple[int, int]]:
        x0, y0 = start
        x3, y3 = end
        dx, dy = x3 - x0, y3 - y0
        distance = math.hypot(dx, dy) or 1.0
        midpoint_x = (x0 + x3) / 2
        midpoint_y = (y0 + y3) / 2
        perp_x, perp_y = -dy / distance, dx / distance
        arc = random.uniform(0.08, 0.22) * distance * random.choice([-1, 1])
        x1 = midpoint_x + perp_x * arc
        y1 = midpoint_y + perp_y * arc
        x2 = midpoint_x + perp_x * arc * 0.5
        y2 = midpoint_y + perp_y * arc * 0.5

        points: List[Tuple[int, int]] = []
        for step in range(steps):
            t = step / (steps - 1)
            mt = 1.0 - t
            x = mt**3 * x0 + 3 * mt**2 * t * x1 + 3 * mt * t**2 * x2 + t**3 * x3
            y = mt**3 * y0 + 3 * mt**2 * t * y1 + 3 * mt * t**2 * y2 + t**3 * y3
            points.append((int(x), int(y)))
        return points
