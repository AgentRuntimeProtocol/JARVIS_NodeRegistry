import asyncio

import pytest
from arp_standard_model import (
    NodeKind,
    NodeRegistryGetNodeTypeParams,
    NodeRegistryGetNodeTypeRequest,
    NodeRegistryHealthRequest,
    NodeRegistryListNodeTypesParams,
    NodeRegistryListNodeTypesRequest,
    NodeRegistryPublishNodeTypeRequest,
    NodeRegistryVersionRequest,
    NodeType,
    NodeTypePublishRequest,
    Status,
)
from arp_standard_server import ArpServerError

from jarvis_node_registry.builtin_node_types import builtin_node_types
from jarvis_node_registry.registry import NodeRegistry, _semver_key
from jarvis_node_registry.store import NodeTypeStore


def _publish(registry: NodeRegistry, node_type: NodeType) -> NodeType:
    request = NodeRegistryPublishNodeTypeRequest(
        body=NodeTypePublishRequest(node_type=node_type)
    )
    return asyncio.run(registry.publish_node_type(request))


def test_health_and_version(tmp_path) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")
    health = asyncio.run(registry.health(NodeRegistryHealthRequest()))
    version = asyncio.run(registry.version(NodeRegistryVersionRequest()))

    assert health.status == Status.ok
    assert version.service_name == "arp-jarvis-node-registry"


def test_publish_get_and_list_node_types(tmp_path) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")
    node = NodeType(
        node_type_id="jarvis.core.echo",
        version="0.1.0",
        kind=NodeKind.atomic,
    )
    _publish(registry, node)

    get_request = NodeRegistryGetNodeTypeRequest(
        params=NodeRegistryGetNodeTypeParams(
            node_type_id="jarvis.core.echo",
            version="0.1.0",
        )
    )
    fetched = asyncio.run(registry.get_node_type(get_request))
    assert fetched.node_type_id == "jarvis.core.echo"

    list_request = NodeRegistryListNodeTypesRequest(
        params=NodeRegistryListNodeTypesParams(q="jarvis.core", kind=NodeKind.atomic)
    )
    results = asyncio.run(registry.list_node_types(list_request))
    assert len(results) == 1


def test_publish_conflict_raises(tmp_path) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")
    node = NodeType(
        node_type_id="jarvis.core.echo",
        version="0.1.0",
        kind=NodeKind.atomic,
    )
    _publish(registry, node)

    with pytest.raises(ArpServerError) as excinfo:
        _publish(registry, node)

    assert excinfo.value.status_code == 409
    assert excinfo.value.code == "node_type_already_exists"


def test_registry_uses_env_db_url(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(
        "JARVIS_NODE_REGISTRY_DB_URL", f"sqlite:///{tmp_path}/node_registry.sqlite"
    )
    registry = NodeRegistry(db_url=None)
    node = NodeType(
        node_type_id="jarvis.core.echo",
        version="0.1.0",
        kind=NodeKind.atomic,
    )
    _publish(registry, node)
    assert registry._store.get("jarvis.core.echo", "0.1.0") is not None


def test_get_missing_node_type_raises(tmp_path) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")
    request = NodeRegistryGetNodeTypeRequest(
        params=NodeRegistryGetNodeTypeParams(node_type_id="missing", version="0.1.0")
    )

    with pytest.raises(ArpServerError) as excinfo:
        asyncio.run(registry.get_node_type(request))

    assert excinfo.value.status_code == 404


def test_get_latest_version_falls_back_to_sort(tmp_path) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")
    for version in ["beta", "alpha"]:
        _publish(
            registry,
            NodeType(
                node_type_id="jarvis.core.echo",
                version=version,
                kind=NodeKind.atomic,
            ),
        )

    request = NodeRegistryGetNodeTypeRequest(
        params=NodeRegistryGetNodeTypeParams(node_type_id="jarvis.core.echo", version=None)
    )
    node_type = asyncio.run(registry.get_node_type(request))
    assert node_type.version == "beta"


def test_get_missing_node_type_without_versions(tmp_path) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")
    request = NodeRegistryGetNodeTypeRequest(
        params=NodeRegistryGetNodeTypeParams(node_type_id="missing", version=None)
    )
    with pytest.raises(ArpServerError) as excinfo:
        asyncio.run(registry.get_node_type(request))

    assert excinfo.value.status_code == 404


def test_seed_node_types_skips_duplicates(tmp_path) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")
    node = NodeType(
        node_type_id="jarvis.core.echo",
        version="0.1.0",
        kind=NodeKind.atomic,
    )

    inserted = registry.seed_node_types([node, node])
    assert inserted == 1


def test_seed_node_types_raises_on_unexpected_error(tmp_path, monkeypatch) -> None:
    registry = NodeRegistry(db_url=f"sqlite:///{tmp_path}/node_registry.sqlite")

    def fail_publish(_self, _node_type):
        raise RuntimeError("boom")

    monkeypatch.setattr(NodeTypeStore, "publish", fail_publish)

    with pytest.raises(RuntimeError):
        registry.seed_node_types(
            [
                NodeType(
                    node_type_id="jarvis.core.echo",
                    version="0.1.0",
                    kind=NodeKind.atomic,
                )
            ]
        )


def test_builtin_node_types() -> None:
    node_types = builtin_node_types(version="0.3.7")
    assert node_types
    node_type = node_types[0]
    assert node_type.node_type_id == "jarvis.composite.planner.general"
    assert node_type.kind == NodeKind.composite
    schema = node_type.input_schema or {}
    assert schema.get("type") == "object"
    assert schema.get("additionalProperties") is False
    properties = schema.get("properties") or {}
    required = schema.get("required") or []
    assert isinstance(properties, dict)
    assert set(required) == set(properties.keys())


def test_semver_key_parsing() -> None:
    assert _semver_key("not-a-semver") is None
    assert _semver_key("1.2.3-alpha.1") == (1, 2, 3, 0, ((1, "alpha"), (0, 1)))
