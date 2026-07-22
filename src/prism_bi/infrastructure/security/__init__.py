"""OS keyring facade for secrets."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

import keyring
from keyring.errors import KeyringError

_LOGGER = logging.getLogger("prism_bi.security")
_SERVICE = "prism-bi"


@runtime_checkable
class SecretStore(Protocol):
    """Secret storage port."""

    def get(self, key: str) -> str | None:
        """Return a secret or ``None``."""

    def set(self, key: str, value: str) -> None:
        """Persist a secret."""

    def delete(self, key: str) -> None:
        """Remove a secret if present."""


class KeyringSecretStore:
    """Secret store backed by the operating system keyring."""

    def __init__(self, service_name: str = _SERVICE) -> None:
        self._service = service_name

    def get(self, key: str) -> str | None:
        try:
            return keyring.get_password(self._service, key)
        except KeyringError as exc:
            _LOGGER.warning("keyring get failed for %s: %s", key, exc)
            return None

    def set(self, key: str, value: str) -> None:
        try:
            keyring.set_password(self._service, key, value)
        except KeyringError as exc:
            _LOGGER.error("keyring set failed for %s: %s", key, exc)
            raise

    def delete(self, key: str) -> None:
        try:
            keyring.delete_password(self._service, key)
        except KeyringError:
            return


class InMemorySecretStore:
    """Test double for SecretStore."""

    def __init__(self) -> None:
        self._data: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)
