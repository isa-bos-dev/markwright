import socket

import pytest

import markwright.core.converter as converter


def test_tests_cannot_open_network_connections() -> None:
    with pytest.raises(RuntimeError, match="network access is not allowed"):
        socket.create_connection(("127.0.0.1", 9), timeout=1)


def test_the_converter_never_sees_the_developers_local_models_folder() -> None:
    # Looked up through the module: that is how the converter itself resolves it.
    assert converter.find_models_dir() is None
