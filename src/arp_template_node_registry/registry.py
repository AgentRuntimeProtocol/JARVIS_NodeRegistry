from __future__ import annotations

from collections import defaultdict
import re
from typing import Any

from arp_standard_model import (
    Health,
    NodeKind,
    NodeRegistryGetNodeTypeRequest,
    NodeRegistryHealthRequest,
    NodeRegistryListNodeTypesRequest,
    NodeRegistryPublishNodeTypeRequest,
    NodeRegistryVersionRequest,
    NodeType,
    Status,
    VersionInfo,
)
from arp_standard_server import ArpServerError
from arp_standard_server.node_registry import BaseNodeRegistryServer

from . import __version__
from .utils import now


class NodeRegistry(BaseNodeRegistryServer):
    """Minimal in-memory Node Registry implementation."""

    # Core method - API surface and main extension points
    def __init__(
        self,
        *,
        service_name: str = "arp-template-node-registry",
        service_version: str = __version__,
    ) -> None:
        """
        Not part of ARP spec; required to construct the registry.

        Args:
          - service_name: Name exposed by /v1/version.
          - service_version: Version exposed by /v1/version.

        Potential modifications:
          - Replace in-memory storage with a real database or index.
          - Add cache layers for hot NodeTypes.
        """
        self._service_name = service_name
        self._service_version = service_version
        self._store: dict[tuple[str, str], NodeType] = {}
        self._versions: dict[str, list[str]] = defaultdict(list)

    # Core methods - Node Registry API implementations
    async def health(self, request: NodeRegistryHealthRequest) -> Health:
        """
        Mandatory: Required by the ARP Node Registry API.

        Args:
          - request: NodeRegistryHealthRequest (unused).
        """
        _ = request
        return Health(status=Status.ok, time=now())

    async def version(self, request: NodeRegistryVersionRequest) -> VersionInfo:
        """
        Mandatory: Required by the ARP Node Registry API.

        Args:
          - request: NodeRegistryVersionRequest (unused).
        """
        _ = request
        return VersionInfo(
            service_name=self._service_name,
            service_version=self._service_version,
            supported_api_versions=["v1"],
        )

    async def publish_node_type(self, request: NodeRegistryPublishNodeTypeRequest) -> NodeType:
        """
        Mandatory: Required by the ARP Node Registry API.

        Args:
          - request: NodeRegistryPublishNodeTypeRequest with NodeType payload.

        Potential modifications:
          - Enforce versioning rules (semver, channels).
          - Validate schemas or metadata before publishing.
        """
        node_type = request.body.node_type
        key = (node_type.node_type_id, node_type.version)
        if key in self._store:
            raise ArpServerError(
                code="node_type_already_exists",
                message=f"NodeType '{node_type.node_type_id}@{node_type.version}' already exists",
                status_code=409,
            )
        self._store[key] = node_type
        self._versions[node_type.node_type_id].append(node_type.version)
        return node_type

    async def get_node_type(self, request: NodeRegistryGetNodeTypeRequest) -> NodeType:
        """
        Mandatory: Required by the ARP Node Registry API.

        Args:
          - request: NodeRegistryGetNodeTypeRequest with node_type_id (+ optional version).

        Potential modifications:
          - Implement semantic version resolution instead of string sort.
          - Add access controls per node_type_id.
        """
        node_type_id = request.params.node_type_id
        version = request.params.version
        if version is None:
            versions = self._versions.get(node_type_id) or []
            if not versions:
                raise ArpServerError(code="node_type_not_found", message=f"NodeType '{node_type_id}' not found", status_code=404)
            semver_versions = [(v, _semver_key(v)) for v in versions]
            semver_versions = [(v, key) for v, key in semver_versions if key is not None]
            if semver_versions:
                version = max(semver_versions, key=lambda item: item[1])[0]
            else:
                version = sorted(versions)[-1]
        key = (node_type_id, version)
        node_type = self._store.get(key)
        if node_type is None:
            raise ArpServerError(code="node_type_not_found", message=f"NodeType '{node_type_id}@{version}' not found", status_code=404)
        return node_type

    async def list_node_types(self, request: NodeRegistryListNodeTypesRequest) -> list[NodeType]:
        """
        Mandatory: Required by the ARP Node Registry API.

        Args:
          - request: NodeRegistryListNodeTypesRequest with optional filters.

        Potential modifications:
          - Implement full-text search or tag filtering.
          - Add pagination and sorting.
        """
        q = (request.params.q or "").strip().lower()
        kind: NodeKind | None = request.params.kind
        out: list[NodeType] = []
        for node_type in self._store.values():
            if q and q not in node_type.node_type_id.lower():
                continue
            if kind is not None and node_type.kind != kind:
                continue
            out.append(node_type)
        out.sort(key=lambda nt: (nt.node_type_id, nt.version))
        return out


_SEMVER_RE = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z.-]+))?"
    r"(?:\+[0-9A-Za-z.-]+)?$"
)


def _semver_key(version: str) -> tuple[int, int, int, int, tuple[tuple[int, Any], ...]] | None:
    match = _SEMVER_RE.match(version)
    if not match:
        return None
    major, minor, patch = (int(match.group(i)) for i in range(1, 4))
    prerelease = match.group(4)
    if prerelease is None:
        return (major, minor, patch, 1, ())
    parts: list[tuple[int, Any]] = []
    for part in prerelease.split("."):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return (major, minor, patch, 0, tuple(parts))
