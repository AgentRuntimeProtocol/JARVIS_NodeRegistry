import asyncio

from arp_standard_model import (
    NodeKind,
    NodeRegistryGetNodeTypeParams,
    NodeRegistryGetNodeTypeRequest,
    NodeRegistryPublishNodeTypeRequest,
    NodeType,
    NodeTypePublishRequest,
)
from jarvis_node_registry.registry import NodeRegistry


def test_semver_latest_version(tmp_path) -> None:
    db_url = f"sqlite:///{tmp_path}/node_registry.sqlite"
    registry = NodeRegistry(db_url=db_url)
    for version in ["0.2.0", "0.10.0"]:
        node_type = NodeType(
            node_type_id="jarvis.core.echo",
            version=version,
            kind=NodeKind.atomic,
        )
        request = NodeRegistryPublishNodeTypeRequest(
            body=NodeTypePublishRequest(node_type=node_type)
        )
        asyncio.run(registry.publish_node_type(request))

    get_request = NodeRegistryGetNodeTypeRequest(
        params=NodeRegistryGetNodeTypeParams(node_type_id="jarvis.core.echo", version=None)
    )
    node_type = asyncio.run(registry.get_node_type(get_request))

    assert node_type.version == "0.10.0"
