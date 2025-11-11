# net/protocol.py
import json

def encode(msg: dict) -> bytes:
    return (json.dumps(msg, separators=(",", ":")) + "\n").encode("utf-8")

def decode_lines(buffer: bytearray):
    """Yield complete JSON messages from a byte buffer; leave partial line in buffer."""
    start = 0
    while True:
        nl = buffer.find(b"\n", start)
        if nl == -1:
            break
        line = buffer[:nl]
        del buffer[:nl+1]
        if line.strip():
            yield json.loads(line.decode("utf-8"))
