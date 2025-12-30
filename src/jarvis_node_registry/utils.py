from __future__ import annotations

import os
from datetime import datetime, timezone

from arp_standard_server import AuthSettings

DEFAULT_DEV_KEYCLOAK_ISSUER = "http://localhost:8080/realms/arp-dev"


def now() -> datetime:
    return datetime.now(timezone.utc)


def _has_auth_env() -> bool:
    return any(key.startswith("ARP_AUTH_") for key in os.environ)


def env_flag(name: str, *, default: bool) -> bool:
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def auth_settings_from_env_or_dev_insecure() -> AuthSettings:
    if _has_auth_env():
        return AuthSettings.from_env()
    return AuthSettings(mode="required", issuer=DEFAULT_DEV_KEYCLOAK_ISSUER)
