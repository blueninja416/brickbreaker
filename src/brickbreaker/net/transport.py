# net/transport.py
import socket, threading, queue, time
from .protocol import encode, decode_lines

DEFAULT_PORT = 7777
BUF_SIZE = 65536

class NetNode:
    """Thin JSON-over-TCP helper used by the breaker/placer game.

    A NetNode wraps a connected TCP socket, spins up a background
    thread to handle all blocking I/O, and exposes two thread-safe queues:

    * incoming - messages (dicts) received from the peer
    * outgoing - messages to be sent to the peer

    Messages are encoded/decoded using encode / decode_lines from
    brickbreaker.net.protocol."""

    def __init__(self, sock: socket.socket, is_host: bool):
        """Create a NetNode around an already-connected socket.

        The is_host flag is used by the game logic to distinguish the
        authoritative breaker (host) from the placer (client). The background
        I/O thread is started automatically."""
        self.sock = sock
        self.is_host = is_host  # used by game logic to distinguish breaker vs placer
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._in = queue.Queue()
        self._out = queue.Queue()
        self._alive = True
        self._rx_buf = bytearray()
        self._t = threading.Thread(target=self._pump, daemon=True)
        self._t.start()

    @property
    def incoming(self):
        """Queue of messages received from the peer.

        Each item is a dict that was sent by the remote side and decoded
        from JSON by the background I/O thread."""
        return self._in

    @property
    def outgoing(self):
        """Queue of messages to send to the peer.

        Normally game code should call send() instead of pushing directly
        onto this queue."""
        return self._out

    def send(self, msg: dict):
        """Schedule a message to be sent to the peer.

        The call returns immediately; the message is enqueued and later written
        to the socket by the background I/O thread. Messages are silently
        dropped once the node has been closed."""
        if self._alive:
            self._out.put(msg)

    def close(self):
        """Shut down the TCP connection and stop the background thread.

        After close(), no further messages will be sent or received, and
        send() becomes a no-op."""
        self._alive = False
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    # ---- host helpers ----
    @staticmethod
    def host(port=DEFAULT_PORT):
        """Listen for a single incoming connection and return a host node.

        Used by the breaker role to become the authoritative host for a
        two-player session."""
        ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ls.bind(("", port))
        ls.listen(1)
        conn, _addr = ls.accept()
        ls.close()
        return NetNode(conn, is_host=True)

    @staticmethod
    def join(host, port=DEFAULT_PORT):
        """Connect to an existing host and return a client node."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        return NetNode(s, is_host=False)
    
    @staticmethod
    def host_async(port=DEFAULT_PORT, on_accept=None):
        """Begin listening asynchronously.

        Spawns a background thread that blocks on accept(). When a client
        connects, it wraps the socket in a NetNode(is_host=True) and calls
        on_accept(node).
        """
        ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ls.bind(("", port))
        ls.listen(1)

        def waiter():
            try:
                conn, _addr = ls.accept()  # blocking, but on background thread
            except OSError:
                return
            finally:
                try:
                    ls.close()
                except OSError:
                    pass

            node = NetNode(conn, is_host=True)
            if on_accept:
                on_accept(node)

        threading.Thread(target=waiter, daemon=True).start()
        return ls

    # ---- background I/O thread ----
    def _pump(self):
        """Internal worker loop that moves bytes to/from the socket.

        This method runs on a dedicated daemon thread. It:

        * pulls any pending messages from self._out and sends them, and
        * reads from the socket, decodes complete JSON frames, and pushes them
          onto self._in."""
        self.sock.settimeout(0.05)
        try:
            while self._alive:
                # flush outgoing
                try:
                    while True:
                        msg = self._out.get_nowait()
                        self.sock.sendall(encode(msg))
                except queue.Empty:
                    pass

                # read incoming
                try:
                    chunk = self.sock.recv(BUF_SIZE)
                    if not chunk:
                        break
                    self._rx_buf.extend(chunk)
                    for msg in decode_lines(self._rx_buf):
                        self._in.put(msg)
                except socket.timeout:
                    pass
                except OSError:
                    break

                # tiny sleep to avoid spin
                time.sleep(0.001)
        finally:
            self._alive = False
            try:
                self.sock.close()
            except OSError:
                pass
