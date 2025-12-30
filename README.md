# JARVIS Node Registry

First-party OSS reference implementation of the **ARP Node Registry** service.

This reference implementation uses only the SDK packages:
`arp-standard-server`, `arp-standard-model`, and `arp-standard-client`.

It is intentionally small and readable so you can swap in your preferred storage/index while keeping the same API surface.

Implements: ARP Standard `spec/v1` Node Registry API (contract: `ARP_Standard/spec/v1/openapi/node-registry.openapi.yaml`).

## Requirements

- Python >= 3.11

## Install

```bash
python3 -m pip install -e .
```

## Local configuration (optional)

For local dev convenience, copy the example env file:

```bash
cp .env.example .env.local
```

`src/scripts/dev_server.sh` auto-loads `.env.local` (or `.env`).

## Run

- Node Registry listens on `http://127.0.0.1:8084` by default.

```bash
python3 -m pip install -e .
python3 -m jarvis_node_registry
```

> [!TIP]
> Use `bash src/scripts/dev_server.sh --host ... --port ... --reload` for dev convenience.

## Using this repo

To build your own registry, fork this repository and replace the SQLite store with your storage/index while preserving request/response semantics.

If all you need is to change storage behavior, edit:
- `src/jarvis_node_registry/registry.py`

### Default behavior

- NodeTypes are stored in SQLite keyed by `(node_type_id, version)`.
- `publish_node_type` stores and returns the NodeType (conflict returns 409).
- `get_node_type` returns exact version if provided; otherwise returns the latest semver when parseable.
- `list_node_types` supports a minimal `q` and `kind` filter.
- On startup, the registry auto-loads installed **node packs** via the `jarvis.nodepacks` entry point group
  (from `arp-jarvis-atomic-nodes[metadata]`) and seeds their NodeTypes; duplicates are ignored.
- On startup, the registry also seeds a small set of **built-in system NodeTypes** (metadata-only),
  including composite planner variants such as `jarvis.composite.planner.general`.
- Set `JARVIS_NODE_REGISTRY_SEED=false` to disable startup seeding (recommended for multi-replica deployments).
- SQLite is read-mostly in steady state; production should prefer a single replica when using file-backed SQLite.

> [!NOTE]
> The “latest version” selection prefers semver ordering and falls back to string sort when needed.

### Extensions

NodeTypes include an `extensions` field for non-normative metadata. In the JARVIS stack:

- First-party atomic node packs (e.g. `arp-jarvis-atomic-nodes`) populate `NodeType.extensions.jarvis.*` metadata such as:
  - `jarvis.pack_id`, `jarvis.pack_version`, `jarvis.node_name`
  - `jarvis.side_effect`, `jarvis.egress_policy`, `jarvis.tags`, `jarvis.trust_tier`
- Node Registry built-ins (seeded on startup) add planner metadata such as:
  - `jarvis.role=planner`
  - `jarvis.planner_variant=general`

This registry stores and returns these extension fields verbatim; Selection Service may use a subset to improve candidate ranking.

Full cross-stack list: `https://github.com/AgentRuntimeProtocol/BusinessDocs/blob/main/Business_Docs/JARVIS/Extensions.md`.

## Quick health check

```bash
curl http://127.0.0.1:8084/v1/health
```

## Configuration

CLI flags:
- `--host` (default `127.0.0.1`)
- `--port` (default `8084`)
- `--reload` (dev only)

## Validate conformance (`arp-conformance`)

```bash
python3 -m pip install arp-conformance
arp-conformance check node-registry --url http://127.0.0.1:8084 --tier smoke
arp-conformance check node-registry --url http://127.0.0.1:8084 --tier surface
```

## Helper scripts

- `src/scripts/dev_server.sh`: run the server (flags: `--host`, `--port`, `--reload`).
- `src/scripts/send_request.py`: publish a NodeType from a JSON file and fetch it back.

  ```bash
  python3 src/scripts/send_request.py --request src/scripts/request.json
  ```

## Authentication

Auth is enabled by default (JWT). To disable for local dev, set `ARP_AUTH_PROFILE=dev-insecure`.

To enable local Keycloak defaults, set:
- `ARP_AUTH_PROFILE=dev-secure-keycloak`
- `ARP_AUTH_AUDIENCE=arp-node-registry`
- `ARP_AUTH_ISSUER=http://localhost:8080/realms/arp-dev`

## Upgrading

When upgrading to a new ARP Standard SDK release, bump pinned versions in `pyproject.toml` (`arp-standard-*==...`) and re-run conformance.
