import asyncio
import socket
import sys
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


@pytest.fixture(autouse=True)
def enforce_offline_sockets(request, monkeypatch):
    """Guarantees zero outbound external network calls can occur during test execution.
    Any attempt to connect to a non-loopback IP socket raises a fatal RuntimeError.
    Loopback connections ('127.0.0.1', 'localhost', '::1') are permitted for local IPC.
    Live integration tests requiring network must explicitly opt in with @pytest.mark.live_api.
    """
    if "live_api" in request.keywords or "network" in request.keywords:
        return

    orig_connect = socket.socket.connect

    def forbidden_connect(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise RuntimeError(
                f"FATAL: Prohibited outbound external network call detected to {address} during offline test execution! "
                f"Mark test with @pytest.mark.live_api if live network is explicitly intended."
            )
        return orig_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", forbidden_connect)
