"""Run the Brick Breaker game with optional LEGO menu fallback."""
import argparse
from types import SimpleNamespace

from transport import NetNode, DEFAULT_PORT
import breaker
import placer

def _main():
    parser = argparse.ArgumentParser(description="Brick Breaker networking")
    parser.add_argument("--host", action="store_true")
    parser.add_argument("--join", type=str)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--role", choices=["placer", "breaker"])  # optional
    args = parser.parse_args()

    # If no role was specified, use the LEGO menu UI to choose
    if not args.role:
        from menu import run_menu  # UI-only
        sel = run_menu()
        if not sel:
            return
        if sel["mode"] == "host":
            net = NetNode.host(port=sel["port"])
            args = SimpleNamespace(host=True, join=None, port=sel["port"], role="breaker")
        else:
            net = NetNode.join(sel["join_ip"], port=sel["port"])
            args = SimpleNamespace(host=False, join=sel["join_ip"], port=sel["port"], role="placer")
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
