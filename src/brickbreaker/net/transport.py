# net/transport.py
import socket, threading, queue, time
from .protocol import encode, decode_lines

DEFAULT_PORT = 7777
BUF_SIZE = 65536

class NetNode:
    def __init__(self, sock: socket.socket, is_host: bool):
        self.sock = sock
        self.is_host = is_host
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._in = queue.Queue()
        self._out = queue.Queue()
        self._alive = True
        self._rx_buf = bytearray()
        self._t = threading.Thread(target=self._pump, daemon=True)
        self._t.start()

    @property
    def incoming(self):  # queue.Queue of dicts from network
        return self._in

    @property
    def outgoing(self):  # queue.Queue of dicts to send to network
        return self._out

    def send(self, msg: dict):
        if self._alive:
            self._out.put(msg)

    def close(self):
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
        ls = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ls.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ls.bind(("", port))
        ls.listen(1)
        conn, _addr = ls.accept()
        ls.close()
        return NetNode(conn, is_host=True)

    @staticmethod
    def join(host, port=DEFAULT_PORT):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        return NetNode(s, is_host=False)

    # ---- background I/O thread ----
    def _pump(self):
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
