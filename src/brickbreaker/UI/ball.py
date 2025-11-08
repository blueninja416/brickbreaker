"""
Ball represented as a LEGO stud.
- Keep velocity normalized to BALL_SPEED for consistent gameplay.
- Generic helpers (AABB vs circle, reflect) work for both paddle and bricks.
"""
from dataclasses import dataclass
import math
import pygame as pg
from config import BALL_RADIUS, BALL_SPEED

@dataclass
class Ball:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    stuck_to_paddle: bool = True  # if True, position follows paddle until launch

    def speed_lock(self):
        """Normalize velocity to BALL_SPEED (prevents speed creep after many bounces)."""
        speed = math.hypot(self.vx, self.vy)
        if speed == 0:
            return
        s = BALL_SPEED / speed
        self.vx *= s
        self.vy *= s

def aabb_circle_collision(rect: pg.Rect, cx: float, cy: float, radius: float) -> bool:
    """Circle-vs-AABB overlap test."""
    nx = max(rect.left, min(cx, rect.right))
    ny = max(rect.top, min(cy, rect.bottom))
    dx, dy = cx - nx, cy - ny
    return dx*dx + dy*dy <= radius*radius

def reflect_off_rect(ball: Ball, rect: pg.Rect):
    """Reflect ball velocity across the closest rect side (simple brick-breaker rule)."""
    cx, cy = ball.x, ball.y
    left_d = abs(cx - rect.left)
    right_d = abs(cx - rect.right)
    top_d = abs(cy - rect.top)
    bottom_d = abs(cy - rect.bottom)
    m = min(left_d, right_d, top_d, bottom_d)
    if m in (left_d, right_d):
        ball.vx *= -1
    else:
        ball.vy *= -1

def draw_ball_stud(surf: pg.Surface, ball: Ball, color=(235, 235, 235)):
    """Render a stud-like ball with rim and highlight (plastic look)."""
    pg.draw.circle(surf, color, (int(ball.x), int(ball.y)), BALL_RADIUS)
    pg.draw.circle(surf, (180, 180, 180), (int(ball.x), int(ball.y)), BALL_RADIUS, 1)
    pg.draw.circle(surf, (255, 255, 255), (int(ball.x)-1, int(ball.y)-1), max(1, BALL_RADIUS-2))
