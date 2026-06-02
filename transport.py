"""Low-level transport layer: VISA (GPIB/USB/VXI-11) or raw TCP socket."""

import socket
import time
from typing import Optional
from .exceptions import CMWError, CMWTimeoutError


class VisaTransport:
    """Uses PyVISA — supports GPIB, USB-TMC, VXI-11 (LAN), and HiSLIP."""

    def __init__(self, resource_string: str, timeout_ms: int = 10_000):
        try:
            import pyvisa
        except ImportError:
            raise CMWError("pyvisa is not installed. Run: pip install pyvisa pyvisa-py")
        rm = pyvisa.ResourceManager()
        self._dev = rm.open_resource(resource_string)
        self._dev.timeout = timeout_ms
        self._dev.read_termination = "\n"
        self._dev.write_termination = "\n"

    def write(self, cmd: str) -> None:
        self._dev.write(cmd)

    def query(self, cmd: str) -> str:
        return self._dev.query(cmd).strip()

    def read(self) -> str:
        return self._dev.read().strip()

    def close(self) -> None:
        self._dev.close()


class TcpTransport:
    """Raw TCP socket transport (port 5025 — SCPI raw socket standard)."""

    PORT = 5025

    def __init__(self, host: str, port: int = PORT, timeout: float = 10.0):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._connect()

    def _connect(self) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(self._timeout)
        try:
            self._sock.connect((self._host, self._port))
        except OSError as exc:
            raise CMWError(f"Cannot connect to {self._host}:{self._port} — {exc}") from exc

    def write(self, cmd: str) -> None:
        self._sock.sendall((cmd + "\n").encode())

    def read(self) -> str:
        buf = b""
        while True:
            try:
                chunk = self._sock.recv(4096)
            except socket.timeout as exc:
                raise CMWTimeoutError("Socket read timed out") from exc
            if not chunk:
                break
            buf += chunk
            if buf.endswith(b"\n"):
                break
        return buf.decode().strip()

    def query(self, cmd: str) -> str:
        self.write(cmd)
        return self.read()

    def close(self) -> None:
        if self._sock:
            self._sock.close()
            self._sock = None
