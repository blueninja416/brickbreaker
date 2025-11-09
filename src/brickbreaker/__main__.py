"""Run the Brick Breaker game."""

import argparse
from brickbreaker import Game
from brickbreaker.net.transport import NetNode


def _main() -> None:
    parser = argparse.ArgumentParser(description="Brick Breaker game networking options")
    parser.add_argument("--host", action="store_true", help="Host a game")
    parser.add_argument("--join", type=str, help="Join a game at the specified address")
    parser.add_argument("--role", choices=["placer", "breaker"], required=True, help="Role in the game")
    args = parser.parse_args()

    if args.host:
        net = NetNode.host()
    elif args.join:
        net = NetNode.join(args.join)
    else:
        net = None

    Game().run(net=net, args=args)


if __name__ == "__main__":
    _main()
