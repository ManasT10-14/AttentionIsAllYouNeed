"""Ordinary tests are offline, even when a developer's shell has live keys."""

import os
import socket

import pytest

os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    # Windows asyncio creates its wakeup socketpair over loopback TCP.
    # Preserve that OS mechanism while refusing every external destination.
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex

    def guarded(original):
        def connect(sock, address):
            if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
                return original(sock, address)
            raise AssertionError("External network calls are forbidden in the offline test suite")

        return connect

    monkeypatch.setattr(socket.socket, "connect", guarded(original_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guarded(original_connect_ex))
