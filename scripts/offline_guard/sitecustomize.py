"""Offline guard: with TAQPSO_OFFLINE=1 any non-loopback socket connection raises.

Put this directory on PYTHONPATH when starting the API; worker processes inherit it, so a passing
demo run proves the backend needs no internet (see `make demo-offline`).
"""

import os
import socket

if os.environ.get("TAQPSO_OFFLINE") == "1":
    _orig = socket.socket.connect

    def _guarded(self, address):  # type: ignore[no-untyped-def]
        host = address[0] if isinstance(address, tuple) else address
        if isinstance(host, str) and host not in ("127.0.0.1", "::1", "localhost") and not host.startswith("/"):
            raise OSError(f"offline guard: blocked connection to {host}")
        return _orig(self, address)

    socket.socket.connect = _guarded  # type: ignore[method-assign]
