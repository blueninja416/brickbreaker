# net/protocol.py
import json

MSG_SYNC_REQUEST = "sync_request"
MSG_SYNC_BRICKS  = "sync_bricks"
MSG_BRICK_ADD    = "brick_add"
MSG_BRICK_REMOVE = "brick_remove"
MSG_TIMER_STATE  = "timer_state"
MSG_RENDER_STATE = "render_state"
MSG_GAME_OVER    = "game_over"

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
