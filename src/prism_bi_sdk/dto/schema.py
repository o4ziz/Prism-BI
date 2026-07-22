"""Schema descriptors shared by host and plugins."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class LogicalType(StrEnum):
    """Inferred or overridden logical column types."""

    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    CATEGORICAL = "categorical"
    TEXT = "text"
    BINARY = "binary"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ColumnDescriptor:
    """Column metadata without assuming source-specific names."""

    name: str
    logical_type: LogicalType
    nullable: bool = True
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class EntityHandle:
    """Opaque handle to a discoverable source entity (sheet, table, resource)."""

    id: str
    display_name: str
    kind: str
    metadata: dict[str, Any] | None = None
