from __future__ import annotations

import logging
import os

from jarvis_atomic_nodes import load_node_types

from .registry import NodeRegistry
from .utils import auth_settings_from_env_or_dev_insecure

logger = logging.getLogger(__name__)


def create_app():
    registry_db_url = os.environ.get("JARVIS_NODE_REGISTRY_DB_URL") or "sqlite:///./runs/jarvis_node_registry.sqlite"
    registry = NodeRegistry(db_url=registry_db_url)
    try:
        node_types = load_node_types()
        seeded = registry.seed_node_types(node_types)
        if seeded:
            logger.info("Seeded %s node types from installed node packs.", seeded)
    except Exception:
        logger.exception("Failed to seed node types from installed node packs.")

    app = registry.create_app(
        title="JARVIS Node Registry",
        auth_settings=auth_settings_from_env_or_dev_insecure(),
    )
    return app


app = create_app()
