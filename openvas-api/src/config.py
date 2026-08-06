import os

SOCKET_PATH = os.environ.get("GVM_SOCKET_PATH", "/run/gvmd/gvmd.sock")
GVM_USERNAME = os.environ.get("GVM_USERNAME", "admin")
GVM_PASSWORD = os.environ.get("GVM_PASSWORD", "password")
# When GVM_HOST is set, connect to gvmd via TLS on GVM_PORT instead of the Unix socket.
GVM_HOST = os.environ.get("GVM_HOST", "")
GVM_PORT = int(os.environ.get("GVM_PORT", "9390"))

