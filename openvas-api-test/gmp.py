from collections.abc import Generator
from contextlib import contextmanager

from fastapi import HTTPException
from gvm.connections import UnixSocketConnection
from gvm.errors import GvmError
from gvm.protocols.gmp import Gmp
from gvm.transforms import EtreeCheckCommandTransform

from config import GVM_PASSWORD, GVM_USERNAME, SOCKET_PATH


GVM_ERRORS = {
    502: {"description": "GVM protocol error"},
    503: {"description": "GVM socket not available"},
}


@contextmanager
def gmp_session() -> Generator[Gmp, None, None]:
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
