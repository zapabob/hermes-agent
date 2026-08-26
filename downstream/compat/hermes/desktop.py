"""Desktop backend entrypoint delegated to the official serve implementation."""

from typing import Any


def start_server(*args: Any, **kwargs: Any) -> Any:
    """Start the official Hermes web backend without a fork-owned server."""
    from hermes_cli.web_server import start_server as official_start_server

    return official_start_server(*args, **kwargs)


__all__ = ["start_server"]
