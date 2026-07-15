from __future__ import annotations

import socket
import subprocess
import urllib.request
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Callable


class NetworkAccessBlocked(RuntimeError):
    pass


@dataclass
class NetworkCounters:
    external_network_request_count: int = 0
    unexpected_network_attempt_count: int = 0


class ZeroNetworkGuard(AbstractContextManager[NetworkCounters]):
    """Fail closed on network and network-capable subprocess use during a pilot."""

    def __init__(self) -> None:
        self.counters = NetworkCounters()
        self._restores: list[tuple[Any, str, Any]] = []

    def __enter__(self) -> NetworkCounters:
        self._patch(socket, "create_connection", self._blocked("socket.create_connection"))
        self._patch(socket.socket, "connect", self._blocked("socket.connect"))
        self._patch(socket.socket, "connect_ex", self._blocked("socket.connect_ex"))
        self._patch(urllib.request, "urlopen", self._blocked("urllib.request.urlopen"))
        self._patch(subprocess, "Popen", self._blocked("subprocess.Popen"))
        return self.counters

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        for owner, name, original in reversed(self._restores):
            setattr(owner, name, original)
        self._restores.clear()
        return False

    def _patch(self, owner: Any, name: str, replacement: Callable[..., Any]) -> None:
        self._restores.append((owner, name, getattr(owner, name)))
        setattr(owner, name, replacement)

    def _blocked(self, source: str) -> Callable[..., Any]:
        def fail(*_args: object, **_kwargs: object) -> Any:
            self.counters.unexpected_network_attempt_count += 1
            raise NetworkAccessBlocked(f"Network-capable operation blocked: {source}")

        return fail
