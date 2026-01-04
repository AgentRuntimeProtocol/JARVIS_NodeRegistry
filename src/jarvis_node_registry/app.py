from __future__ import annotations

import logging
import os

from jarvis_atomic_nodes import load_node_types

from . import __version__
from .builtin_node_types import builtin_node_types
from .registry import NodeRegistry
from .utils import auth_settings_from_env_or_dev_insecure, env_flag

logger = logging.getLogger(__name__)


def create_app():
    registry_db_url = os.environ.get("JARVIS_NODE_REGISTRY_DB_URL") or "sqlite:///./runs/jarvis_node_registry.sqlite"
    registry = NodeRegistry(db_url=registry_db_url)

    if env_flag("JARVIS_NODE_REGISTRY_SEED", default=True):
        overwrite = env_flag("JARVIS_NODE_REGISTRY_SEED_OVERWRITE", default=False)
        # Seed NodeTypes from installed node packs (first-party atomic packs by default).
        try:
            node_types = load_node_types()
            seeded = registry.seed_node_types(node_types, overwrite=overwrite)
            if seeded:
                logger.info("Seeded %s node types from installed node packs.", seeded)
        except Exception:
            logger.exception("Failed to seed node types from installed node packs.")

        # Seed built-in system NodeTypes (metadata only).
        try:
            seeded = registry.seed_node_types(builtin_node_types(version=__version__), overwrite=overwrite)
            if seeded:
                logger.info("Seeded %s built-in node types.", seeded)
        except Exception:
            logger.exception("Failed to seed built-in node types.")
    else:
        logger.info("Node Registry seeding is disabled (JARVIS_NODE_REGISTRY_SEED=false).")

    auth_settings = auth_settings_from_env_or_dev_insecure()
    logger.info(
        "Node Registry auth settings (mode=%s, issuer=%s)",
        getattr(auth_settings, "mode", None),
        getattr(auth_settings, "issuer", None),
    )
    app = registry.create_app(
        title="JARVIS Node Registry",
        auth_settings=auth_settings,
    )
    return app


app = create_app()
