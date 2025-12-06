"""Paddle (bottom bouncer bar) — styled like a smooth white LEGO tile.
- Width is expressed in studs for consistent styling with bricks.
- update() handles input + clamps to the provided bounds.
- draw() renders a white tile with subtle highlight/shadow.
"""

from dataclasses import dataclass

import pygame as pg

from .config import COLORS, PADDLE_H, PADDLE_SPEED, STUD_UNIT


@dataclass
class Paddle:
    x: float
    y: float
    studs_w: int  # width in studs

    @property
    def w(self) -> int:
        """Pixel width of the paddle determined by stud width"""
        return self.studs_w * STUD_UNIT

    @property
    def h(self) -> int:
        """Pixel height of the paddle"""
        return PADDLE_H

    def rect(self) -> pg.Rect:
        """Return the paddle bounds as a pygame.Rect."""
        return pg.Rect(int(self.x), int(self.y), self.w, self.h)

    def update(self, dt: float, left_bound: int, right_bound: int, keys):
        """Move the paddle horizontally based on input and clamp to the given bounds.
        dt is the frame time in seconds. left_bound and right_bound define the
        horizontal limits of movement in pixels. keys is the current pygame key state.
        """
        dx = 0
        if keys[pg.K_LEFT] or keys[pg.K_a]:
            dx -= PADDLE_SPEED * dt
        if keys[pg.K_RIGHT] or keys[pg.K_d]:
            dx += PADDLE_SPEED * dt
        self.x = max(left_bound, min(self.x + dx, right_bound - self.w))

    def draw(self, surf: pg.Surface):
        """Draw the paddle with a LEGO-like highlight/shadow effect."""
        r = self.rect()
        pg.draw.rect(surf, COLORS["paddle"], r, border_radius=2)
        pg.draw.line(surf, (255, 255, 255), (r.left, r.top), (r.right - 1, r.top))
        pg.draw.line(surf, (200, 200, 200), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))
