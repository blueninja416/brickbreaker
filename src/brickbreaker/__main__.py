"""Run the Brick Breaker game with optional LEGO menu fallback."""

import argparse
from types import SimpleNamespace

from brickbreaker import breaker, placer
from brickbreaker.net.transport import DEFAULT_PORT, NetNode


def _main():
    """
    Entry point for the actual game. parses args and either launches the menu UI,
    or can start the breaker/placer clients directly (mostly for debugging).
    The main menu is the "official/supported" method of starting the game.
    """
    parser = argparse.ArgumentParser(description="Brick Breaker")
    parser.add_argument("--host", action="store_true")
    parser.add_argument("--join", type=str)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT) # unused in UI menu
    parser.add_argument("--role", choices=["placer", "breaker"])  # optional
    args = parser.parse_args()

    # If no role was specified, use the LEGO menu UI to choose
    if not args.role:
        from brickbreaker.UI.menu import run_menu  # UI-only

        error_message = None
        while True:
            # run the main menu
            sel = run_menu(error_message=error_message)
            error_message = None
            if not sel:
                return

            # if we are hosting
            if sel["mode"] == "host":
                # Prefer a NetNode created by the menu via host_async, if provided
                net = sel.get("net_node")
                if net is None:
                    net = NetNode.host(port=sel["port"])
                args = SimpleNamespace(host=True, join=None, port=sel["port"], role="breaker")
                break

            # if we are joining
            else:
                try:
                    net = NetNode.join(sel["join_ip"], port=sel["port"])
                    args = SimpleNamespace(host=False, join=sel["join_ip"], port=sel["port"], role="placer")
                    break
                # error handling for connection failures
                except ConnectionRefusedError:
                    error_message = "Could not connect to host (connection refused)."
                except OSError:
                    error_message = "Network error while trying to join host."

        if args.role == "breaker":
            breaker.main(net)
        else:
            placer.main(net)
        return

    # CLI route (for quick testing of game clients)
    if args.host:
        net = NetNode.host(port=args.port)
    elif args.join:
        net = NetNode.join(args.join, port=args.port)
    else:
        net = None

    if args.role == "breaker":
        breaker.main(net)
    elif args.role == "placer":
        placer.main(net)


if __name__ == "__main__":
    _main()
