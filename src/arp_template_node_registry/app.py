from __future__ import annotations

from .registry import NodeRegistry
from .utils import auth_settings_from_env_or_dev_insecure


def create_app():
    return NodeRegistry().create_app(
        title="ARP Template Node Registry",
        auth_settings=auth_settings_from_env_or_dev_insecure(),
    )


app = create_app()

