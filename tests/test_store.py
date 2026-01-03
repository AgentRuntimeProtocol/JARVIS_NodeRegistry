import os

import pytest
from arp_standard_model import NodeKind, NodeType
import importlib

from jarvis_node_registry.store import NodeTypeStore
from jarvis_node_registry.utils import (
    DEFAULT_DEV_KEYCLOAK_ISSUER,
    auth_settings_from_env_or_dev_insecure,
    env_flag,
)


def test_store_publish_get_list_versions(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path}/node_registry.sqlite"
    store = NodeTypeStore(db_url=db_url)
    node = NodeType(
        node_type_id="jarvis.core.echo",
        version="0.3.7",
        kind=NodeKind.atomic,
    )
    store.publish(node)

    fetched = store.get("jarvis.core.echo", "0.3.7")
    assert fetched is not None
    assert fetched.node_type_id == "jarvis.core.echo"

    assert list(store.list_versions("jarvis.core.echo")) == ["0.3.7"]
    assert store.list(q="jarvis.core", kind=NodeKind.atomic)
    assert store.list(q="missing", kind=NodeKind.atomic) == []


def test_env_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEST_FLAG", raising=False)
    assert env_flag("TEST_FLAG", default=True)
    monkeypatch.setenv("TEST_FLAG", "false")
    assert not env_flag("TEST_FLAG", default=True)
    monkeypatch.setenv("TEST_FLAG", "1")
    assert env_flag("TEST_FLAG", default=False)


def test_auth_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("ARP_AUTH_"):
            monkeypatch.delenv(key, raising=False)

    settings = auth_settings_from_env_or_dev_insecure()
    assert settings.mode == "required"
    assert settings.issuer == DEFAULT_DEV_KEYCLOAK_ISSUER

    monkeypatch.setenv("ARP_AUTH_PROFILE", "dev-insecure")
    settings = auth_settings_from_env_or_dev_insecure()
    assert settings.mode == "disabled"


def test_create_app_respects_seed_toggle(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JARVIS_NODE_REGISTRY_SEED", "false")
    monkeypatch.setenv("JARVIS_NODE_REGISTRY_DB_URL", f"sqlite:///{tmp_path}/node_registry.sqlite")
    monkeypatch.setenv("ARP_AUTH_PROFILE", "dev-insecure")

    def fail_load():
        raise AssertionError("load_node_types should not be called when seeding is disabled")

    import jarvis_node_registry.app as app_module

    monkeypatch.setattr(app_module, "load_node_types", fail_load)
    monkeypatch.setattr(app_module, "builtin_node_types", lambda version: [])

    app = app_module.create_app()
    assert app is not None


def _reload_app(monkeypatch: pytest.MonkeyPatch, tmp_path, *, seed: bool):
    monkeypatch.setenv("ARP_AUTH_PROFILE", "dev-insecure")
    monkeypatch.setenv("JARVIS_NODE_REGISTRY_DB_URL", f"sqlite:///{tmp_path}/node_registry.sqlite")
    monkeypatch.setenv("JARVIS_NODE_REGISTRY_SEED", "false")

    import jarvis_node_registry.app as app_module

    importlib.reload(app_module)
    monkeypatch.setenv("JARVIS_NODE_REGISTRY_SEED", "true" if seed else "false")
    return app_module


def test_create_app_seeds_when_enabled(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module = _reload_app(monkeypatch, tmp_path, seed=True)
    node_types = [
        NodeType(
            node_type_id="jarvis.core.echo",
            version="0.3.7",
            kind=NodeKind.atomic,
        )
    ]
    builtin_types = [
        NodeType(
            node_type_id="jarvis.composite.planner.general",
            version="0.3.7",
            kind=NodeKind.composite,
        )
    ]

    monkeypatch.setattr(app_module, "load_node_types", lambda: node_types)
    monkeypatch.setattr(app_module, "builtin_node_types", lambda version: builtin_types)

    app = app_module.create_app()
    assert app is not None


def test_create_app_handles_seed_failures(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    app_module = _reload_app(monkeypatch, tmp_path, seed=True)

    def fail_load():
        raise RuntimeError("boom")

    def fail_builtin(version: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(app_module, "load_node_types", fail_load)
    monkeypatch.setattr(app_module, "builtin_node_types", fail_builtin)

    app = app_module.create_app()
    assert app is not None


def test_store_in_memory_database() -> None:
    store = NodeTypeStore(db_url="sqlite://:memory:")
    node = NodeType(
        node_type_id="jarvis.core.echo",
        version="0.3.7",
        kind=NodeKind.atomic,
    )
    store.publish(node)
    assert store.get("jarvis.core.echo", "0.3.7") is not None
    if store._keepalive is not None:
        store._keepalive.close()


def test_store_accepts_raw_path(tmp_path) -> None:
    db_path = tmp_path / "node_registry.sqlite"
    store = NodeTypeStore(db_url=str(db_path))
    node = NodeType(
        node_type_id="jarvis.core.echo",
        version="0.3.7",
        kind=NodeKind.atomic,
    )
    store.publish(node)
    assert store.list(q="jarvis.core", kind=NodeKind.atomic)
