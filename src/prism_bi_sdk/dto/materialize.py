"""Materialize plan — plugins describe data; application writes the warehouse."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import pyarrow as pa

from prism_bi_sdk.dto.schema import ColumnDescriptor


@runtime_checkable
class TabularBatchSource(Protocol):
    """Readable stream of Arrow record batches produced by a plugin."""

    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        """Yield Arrow batches; must not open the project warehouse."""


@dataclass(frozen=True, slots=True)
class MaterializePlan:
    """Plan executed by the application via ``IAnalyticsStore`` (Milestone 2)."""

    columns: tuple[ColumnDescriptor, ...]
    source: TabularBatchSource
    suggested_alias: str
    provenance: dict[str, str]
