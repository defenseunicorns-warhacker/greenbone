import socket as _socket
from collections.abc import Generator
from contextlib import contextmanager

from fastapi import HTTPException
from gvm.connections import UnixSocketConnection
from gvm.connections._connection import AbstractGvmConnection
from gvm.errors import GvmError
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeCheckCommandTransform

from config import GVM_HOST, GVM_PASSWORD, GVM_PORT, GVM_USERNAME, SOCKET_PATH


GVM_ERRORS = {
    502: {"description": "GVM protocol error"},
    503: {"description": "GVM socket not available"},
}


class _PlainTCPConnection(AbstractGvmConnection):
    """Plain TCP connection for the socat-based gvmd proxy (no TLS)."""

    def __init__(self, hostname: str, port: int, timeout: int = 60) -> None:
        super().__init__(timeout=timeout)
        self._hostname = hostname
        self._port = port

    def connect(self) -> None:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        sock.settimeout(self._timeout)
        sock.connect((self._hostname, self._port))
        self._socket = sock


@contextmanager
def gmp_session() -> Generator[Gmp, None, None]:
    if GVM_HOST:
        connection = _PlainTCPConnection(hostname=GVM_HOST, port=GVM_PORT)
    else:
        try:
            connection = UnixSocketConnection(path=SOCKET_PATH)
        except FileNotFoundError:
            raise HTTPException(503, detail=f"GVM socket not found at {SOCKET_PATH}")
    try:
        with Gmp(connection=connection, transform=EtreeCheckCommandTransform()) as gmp:
            gmp.authenticate(GVM_USERNAME, GVM_PASSWORD)
            yield gmp
    except GvmError as exc:
        raise HTTPException(502, detail=str(exc))
