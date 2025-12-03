"""
Shared game-world configuration.

BOARD_W / BOARD_H describe the full logical game area.

ZONE_* describes the brick placement / brick play zone inside that world.
Both breaker and placer should only place bricks inside ZONE_RECT, and
all brick coordinates sent over the network are in world space.
"""

import pygame

# Full logical game arena (matches breaker window size)
BOARD_W = 900
BOARD_H = 600

# Brick placement / brick zone (top portion of the world)
ZONE_TOP = 0
ZONE_H = 400

ZONE_RECT = pygame.Rect(0, ZONE_TOP, BOARD_W, ZONE_H)