from __future__ import annotations

import logging
import re
import os
from collections.abc import Iterable
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
from .store import NodeTypeStore
from .utils import now

logger = logging.getLogger(__name__)


class NodeRegistry(BaseNodeRegistryServer):
    """SQLite-backed Node Registry implementation."""

    # Core method - API surface and main extension points
    def __init__(
        self,
        *,
        service_name: str = "arp-jarvis-node-registry",
        service_version: str = __version__,
        db_url: str | None = None,
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
        if db_url is None:
            db_url = os.environ.get("JARVIS_NODE_REGISTRY_DB_URL") or "sqlite:///./runs/jarvis_node_registry.sqlite"
        self._store = NodeTypeStore(db_url=db_url)
        logger.info("Node Registry store initialized (db_url=%s)", db_url)

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
        logger.info(
            "NodeType publish requested (node_type_id=%s, version=%s)",
            node_type.node_type_id,
            node_type.version,
        )
        try:
            stored = self._store.publish(node_type)
        except Exception as exc:
            if "UNIQUE constraint failed" in str(exc):
                logger.warning(
                    "NodeType already exists (node_type_id=%s, version=%s)",
                    node_type.node_type_id,
                    node_type.version,
                )
                raise ArpServerError(
                    code="node_type_already_exists",
                    message=f"NodeType '{node_type.node_type_id}@{node_type.version}' already exists",
                    status_code=409,
                ) from exc
            raise
        logger.info(
            "NodeType published (node_type_id=%s, version=%s)",
            stored.node_type_id,
            stored.version,
        )
        return stored

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
        logger.info(
            "NodeType lookup requested (node_type_id=%s, version=%s)",
            node_type_id,
            request.params.version,
        )
        if (version := request.params.version) is None:
            versions = list(self._store.list_versions(node_type_id))
            if not versions:
                raise ArpServerError(code="node_type_not_found", message=f"NodeType '{node_type_id}' not found", status_code=404)
            semver_versions = [(v, _semver_key(v)) for v in versions]
            semver_versions = [(v, key) for v, key in semver_versions if key is not None]
            if semver_versions:
                version = max(semver_versions, key=lambda item: item[1])[0]
            else:
                version = sorted(versions)[-1]
        if (node_type := self._store.get(node_type_id, version)) is None:
            raise ArpServerError(code="node_type_not_found", message=f"NodeType '{node_type_id}@{version}' not found", status_code=404)
        logger.info(
            "NodeType lookup resolved (node_type_id=%s, version=%s)",
            node_type.node_type_id,
            node_type.version,
        )
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
        results = self._store.list(q=q, kind=kind)
        logger.info(
            "NodeType list requested (q=%s, kind=%s, count=%s)",
            q or None,
            kind.value if hasattr(kind, "value") else kind,
            len(results),
        )
        return results

    def seed_node_types(self, node_types: Iterable[NodeType]) -> int:
        """
        JARVIS helper: seed NodeTypes on startup without failing on duplicates.

        Returns the count of newly inserted NodeTypes.
        """
        inserted = 0
        for node_type in node_types:
            try:
                self._store.publish(node_type)
            except Exception as exc:
                if "UNIQUE constraint failed" in str(exc):
                    continue
                raise
            else:
                inserted += 1
        if inserted:
            logger.info("NodeType seeding inserted %s records", inserted)
        return inserted


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
    if (prerelease := match.group(4)) is None:
        return (major, minor, patch, 1, ())
    parts: list[tuple[int, Any]] = []
    for part in prerelease.split("."):
        if part.isdigit():
            parts.append((0, int(part)))
        else:
            parts.append((1, part))
    return (major, minor, patch, 0, tuple(parts))
