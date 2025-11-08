"""
Tiny graphics utilities shared by multiple modules.
- lighter/darker: simple color adjustments for faux shading.
- draw_pixel_text: small HUD text (swap later for a custom pixel font if you like).
"""
from typing import Tuple
import pygame as pg

def darker(c: Tuple[int, int, int], amt: int = 30):
    return (max(0, c[0]-amt), max(0, c[1]-amt), max(0, c[2]-amt))

def lighter(c: Tuple[int, int, int], amt: int = 30):
    return (min(255, c[0]+amt), min(255, c[1]+amt), min(255, c[2]+amt))

def draw_pixel_text(surf: pg.Surface, text: str, x: int, y: int, color):
    font = pg.font.SysFont("couriernew", 10)
    surf.blit(font.render(text, True, color), (x, y))
