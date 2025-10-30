"""A Brick Breaker game for CMSC 495."""

import pygame


class Game:
    """Main Brick Breaker game class."""

    def run(self) -> None:
        """Run the game."""
        pygame.init()
        pygame.display.set_caption("Brick Breaker")
        screen = pygame.display.set_mode((800, 600))

        background = pygame.Surface(screen.get_size())
        background = background.convert()
        background.fill((0, 0, 0))

        screen.blit(background, (0, 0))
        pygame.display.flip()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
