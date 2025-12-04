"""Run the Brick Breaker game with optional LEGO menu fallback."""

import argparse
from types import SimpleNamespace

from brickbreaker import breaker, placer
from brickbreaker.net.transport import DEFAULT_PORT, NetNode


def _main():
    parser = argparse.ArgumentParser(description="Brick Breaker networking")
    parser.add_argument("--host", action="store_true")
    parser.add_argument("--join", type=str)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--role", choices=["placer", "breaker"])  # optional
    args = parser.parse_args()

    # If no role was specified, use the LEGO menu UI to choose
    if not args.role:
        from brickbreaker.UI.menu import run_menu  # UI-only

        error_message = None
        while True:
            sel = run_menu(error_message=error_message)
            error_message = None
            if not sel:
                return

            if sel["mode"] == "host":
                # Prefer a NetNode created by the menu via host_async, if provided.
                net = sel.get("net_node")
                if net is None:
                    net = NetNode.host(port=sel["port"])
                args = SimpleNamespace(host=True, join=None, port=sel["port"], role="breaker")
                break

            else:
                try:
                    net = NetNode.join(sel["join_ip"], port=sel["port"])
                    args = SimpleNamespace(host=False, join=sel["join_ip"], port=sel["port"], role="placer")
                    break
                except ConnectionRefusedError:
                    error_message = "Could not connect to host (connection refused)."
                except OSError:
                    error_message = "Network error while trying to join host."

        if args.role == "breaker":
            breaker.main(net)
        else:
            placer.main(net)
        return

    # CLI route (unchanged)
    if args.host:
        net = NetNode.host(port=args.port)
    elif args.join:
        net = NetNode.join(args.join, port=args.port)
    else:
        net = None

    if args.role == "breaker":
        breaker.main(net)
    else:
        placer.main(net)


if __name__ == "__main__":
    _main()
