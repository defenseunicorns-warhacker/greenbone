import os

SOCKET_PATH = os.environ.get("GVM_SOCKET_PATH", "/run/gvmd/gvmd.sock")
GVM_USERNAME = os.environ.get("GVM_USERNAME", "admin")
GVM_PASSWORD = os.environ.get("GVM_PASSWORD", "password")
# When GVM_HOST is set, connect to gvmd via TLS on GVM_PORT instead of the Unix socket.
GVM_HOST = os.environ.get("GVM_HOST", "")
GVM_PORT = int(os.environ.get("GVM_PORT", "9390"))

# Well-known UUIDs seeded into every Greenbone CE installation
DEFAULT_PORT_LIST_ID = "33d0cd82-57c6-11e1-8251-406186ea4fc5"   # All IANA assigned TCP
DEFAULT_SCAN_CONFIG_ID = "daba56c8-73ec-11df-a475-002264764cea"  # Full and fast
DEFAULT_SCANNER_ID = "08b69003-5fc2-4037-a479-93b440211c73"      # OpenVAS Default
