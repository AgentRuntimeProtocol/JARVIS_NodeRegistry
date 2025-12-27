# ARP Template Node Registry

Use this repo as a starting point for building an **ARP compliant Node Registry** service.

This minimal template implements the Node Registry API using only the SDK packages:
`arp-standard-server`, `arp-standard-model`, and `arp-standard-client`.

It is intentionally small and readable so you can swap in your preferred storage/index while keeping the same API surface.

Implements: ARP Standard `spec/v1` Node Registry API (contract: `ARP_Standard/spec/v1/openapi/node-registry.openapi.yaml`).

## Requirements

- Python >= 3.10

## Install

```bash
python3 -m pip install -e .
```

## Local configuration (optional)

For local dev convenience, copy the template env file:

```bash
cp .env.example .env.local
```

`src/scripts/dev_server.sh` auto-loads `.env.local` (or `.env`).

## Run

- Node Registry listens on `http://127.0.0.1:8084` by default.

```bash
python3 -m pip install -e '.[run]'
python3 -m arp_template_node_registry
```

> [!TIP]
> Use `bash src/scripts/dev_server.sh --host ... --port ... --reload` for dev convenience.

## Using this repo

To build your own registry, fork this repository and replace the in-memory store with your storage/index while preserving request/response semantics.

If all you need is to change storage behavior, edit:
- `src/arp_template_node_registry/registry.py`

### Default behavior

- NodeTypes are stored in memory keyed by `(node_type_id, version)`.
- `publish_node_type` stores and returns the NodeType (conflict returns 409).
- `get_node_type` returns exact version if provided; otherwise returns the latest version by string sort.
- `list_node_types` supports a minimal `q` and `kind` filter.

> [!NOTE]
> The “latest version” selection is a simple string sort for template simplicity; real registries should use semver-aware ordering.

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

For out-of-the-box usability, this template defaults to auth-disabled unless you set `ARP_AUTH_MODE` or `ARP_AUTH_PROFILE`.

To enable JWT auth, set either:
- `ARP_AUTH_PROFILE=dev-secure-keycloak` + `ARP_AUTH_SERVICE_ID=<audience>`
- or `ARP_AUTH_MODE=required` with `ARP_AUTH_ISSUER` and `ARP_AUTH_AUDIENCE`

## Upgrading

When upgrading to a new ARP Standard SDK release, bump pinned versions in `pyproject.toml` (`arp-standard-*==...`) and re-run conformance.
