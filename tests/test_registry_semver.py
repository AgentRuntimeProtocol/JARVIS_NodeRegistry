import asyncio

from arp_standard_model import (
    NodeKind,
    NodeRegistryGetNodeTypeParams,
    NodeRegistryGetNodeTypeRequest,
    NodeRegistryPublishNodeTypeRequest,
    NodeType,
    NodeTypePublishRequest,
)
from arp_template_node_registry.registry import NodeRegistry


def test_semver_latest_version() -> None:
    registry = NodeRegistry()
    for version in ["0.2.0", "0.10.0"]:
        node_type = NodeType(
            node_type_id="atomic.echo",
            version=version,
            kind=NodeKind.atomic,
        )
        request = NodeRegistryPublishNodeTypeRequest(
            body=NodeTypePublishRequest(node_type=node_type)
        )
        asyncio.run(registry.publish_node_type(request))

    get_request = NodeRegistryGetNodeTypeRequest(
        params=NodeRegistryGetNodeTypeParams(node_type_id="atomic.echo", version=None)
    )
    node_type = asyncio.run(registry.get_node_type(get_request))

    assert node_type.version == "0.10.0"
