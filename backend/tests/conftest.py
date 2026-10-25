"""Backend unit tests never publish traces, even with local credentials configured."""

import os
import socket

import pytest

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    original = socket.socket.connect

    def connect(sock, address):
        if isinstance(address, tuple) and address[0] in {"127.0.0.1", "::1"}:
            return original(sock, address)
        raise AssertionError("External network is disabled in backend unit tests")

    monkeypatch.setattr(socket.socket, "connect", connect)
