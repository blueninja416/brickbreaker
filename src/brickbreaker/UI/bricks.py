"""LEGO-like bricks (SIDE VIEW): data model + drawing.
- We render bricks from the SIDE: a rectangular body with semicircle studs along the top.
- `studs_x` controls visible width (stud count). `studs_y` is kept for data compatibility.
- Unbreakable bricks are grey with a chain overlay.
"""

from dataclasses import dataclass

import pygame as pg

from .config import BRICK_HEIGHT, COLORS, STUD_UNIT, BRICK_HIT_POINTS
from .graphics import darker, lighter


# Visual tuning for side-view studs
STUD_RADIUS = 3  # radius of the semicircle studs on the top edge
STUD_RIM_THICK = 1  # rim thickness for the stud outline
STUD_TOP_OFFSET = 0  # vertical offset from brick top for stud bases


@dataclass
class Brick:
    x: int
    y: int
    studs_x: int  # width in studs (e.g., 4 for a 1x4)
    studs_y: int  # depth in studs (kept for data, not used in side height)
    color_key: str
    unbreakable: bool = False
    hits_left: int = 1
    alive: bool = True

    def __post_init__(self):
        if not self.unbreakable:
            self.hits_left = BRICK_HIT_POINTS.get(self.color_key, 1)
        else:
            self.hits_left = 999_999

    @property
    def w(self) -> int:
        return self.studs_x * STUD_UNIT

    @property
    def h(self) -> int:
        return BRICK_HEIGHT  # constant in side view

    def rect(self) -> pg.Rect:
        return pg.Rect(self.x, self.y, self.w, self.h)


def _draw_side_stud(surf: pg.Surface, cx: int, top_y: int, base_color):
    # Stud as a semicircle sitting on the top edge with highlight + rim
    pg.draw.circle(surf, base_color, (cx, top_y), STUD_RADIUS)
    pg.draw.circle(surf, lighter(base_color, 35), (cx - 1, top_y - 1), max(1, STUD_RADIUS - 2))
    pg.draw.circle(surf, darker(base_color, 50), (cx, top_y), STUD_RADIUS, STUD_RIM_THICK)
    # Flat cutoff line to suggest it sits on the brick edge
    pg.draw.line(surf, base_color, (cx - STUD_RADIUS, top_y), (cx + STUD_RADIUS, top_y))


def draw_brick(surf: pg.Surface, b: Brick):
    base = COLORS[b.color_key]
    r = b.rect()

    # Body with top highlight & bottom shadow
    pg.draw.rect(surf, base, r)
    pg.draw.line(surf, lighter(base, 25), (r.left, r.top), (r.right - 1, r.top))
    pg.draw.line(surf, darker(base, 35), (r.left, r.bottom - 1), (r.right - 1, r.bottom - 1))

    # Studs along the top edge, one per stud cell
    top_y = r.top + STUD_TOP_OFFSET
    for i in range(b.studs_x):
        cx = r.left + STUD_UNIT // 2 + i * STUD_UNIT
        _draw_side_stud(surf, cx, top_y, lighter(base, 10))

    # Unbreakable overlay
    if b.unbreakable:
        chain_color = (210, 210, 210)
        mid_y = r.centery
        for i in range(r.left + 4, r.right - 4, 10):
            pg.draw.circle(surf, chain_color, (i, mid_y - 3), 3, 1)
            pg.draw.circle(surf, chain_color, (i + 5, mid_y + 3), 3, 1)
        pg.draw.rect(surf, darker(base, 40), r, 1)
