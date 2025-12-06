"""
Screen/layout helpers for breaker and placer.

We keep a single world coordinate system (BOARD_W x BOARD_H) and then
decide how to frame that world inside each window.

- Breaker: window = BOARD_W x (BOARD_H + HUD_H)
- Placer:  window = (BOARD_W + SIDEBAR_W) x (BOARD_H + HUD_H)
"""

import pygame
from .world import BOARD_W, BOARD_H

# Top HUD height
HUD_H = 60

# Placer sidebar width
SIDEBAR_W = 220

# Total window height = world height + HUD on top
WINDOW_HEI = BOARD_H + HUD_H


def get_breaker_layout():
    """Return (window_size, board_rect, hud_rect) for the breaker role."""
    window_size = (BOARD_W, WINDOW_HEI)

    # Full game board shifted down under the HUD
    board_rect = pygame.Rect(0, HUD_H, BOARD_W, BOARD_H)

    # HUD spans the full width, above the board
    hud_rect = pygame.Rect(0, 0, BOARD_W, HUD_H)

    return window_size, board_rect, hud_rect


def get_placer_layout():
    """
    Return (window_size, board_rect, sidebar_rect, hud_rect) for the placer role.
    """
    window_size = (BOARD_W + SIDEBAR_W, WINDOW_HEI)

    # Same full board as breaker, same position
    board_rect = pygame.Rect(0, HUD_H, BOARD_W, BOARD_H)

    # Sidebar sits to the right of the board
    sidebar_rect = pygame.Rect(board_rect.right, 0, SIDEBAR_W, WINDOW_HEI)

    # HUD only spans the board area; sidebar has its own layout
    hud_rect = pygame.Rect(0, 0, BOARD_W, HUD_H)

    return window_size, board_rect, sidebar_rect, hud_rect


def world_to_screen(point: tuple[float, float], container: pygame.Rect) -> tuple[int, int]:
    """Map a (x, y) in world space into screen coordinates, anchored at container."""
    x, y = point
    return int(container.x + x), int(container.y + y)


def screen_to_world(point: tuple[float, float], container: pygame.Rect) -> tuple[float, float]:
    """Inverse of world_to_screen: screen → world, relative to container."""
    x, y = point
    return x - container.x, y - container.y