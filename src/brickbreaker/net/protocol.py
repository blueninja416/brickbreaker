# net/protocol.py
import json

def encode(msg: dict) -> bytes:
    """Encode a message dict as a single-line JSON frame.

    The returned bytes are UTF-8 encoded JSON terminated by a newline so that
    the transport layer can safely frame and reassemble individual messages."""
    return (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")

def decode_lines(buffer: bytearray):
    """Yield complete JSON messages from a byte buffer.

        This helper consumes complete "\\n"-terminated frames from ``buffer``,
        deserializes them from JSON into ``dict`` objects, and leaves any partial
        trailing line in ``buffer`` for the next read."""
    start = 0
    while True:
        nl = buffer.find(b"\n", start)
        if nl == -1:
            break
        line = buffer[:nl]
        del buffer[:nl+1]
        if line.strip():
            yield json.loads(line.decode("utf-8"))
