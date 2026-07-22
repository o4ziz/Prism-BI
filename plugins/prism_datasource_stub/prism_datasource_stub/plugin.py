"""Stub datasource plugin for Milestone 1 (no real file IO)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pyarrow as pa

from prism_bi_sdk import (
    ContributionKind,
    ContributionRegistration,
    PluginManifest,
    PluginRegistry,
)
from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.datasources import DataSourceCapability
from prism_bi_sdk.dto.materialize import MaterializePlan
from prism_bi_sdk.dto.preview import PreviewResult
from prism_bi_sdk.dto.schema import ColumnDescriptor, EntityHandle, LogicalType


class _EmptyBatchSource:
    def iter_batches(self, *, batch_size: int) -> Iterator[pa.RecordBatch]:
        _ = batch_size
        schema = pa.schema([("value", pa.int64())])
        yield pa.RecordBatch.from_pydict({"value": []}, schema=schema)


class StubDataSourcePlugin:
    """Minimal batch_import datasource used to prove plugin discovery."""

    def __init__(self) -> None:
        self._manifest = PluginManifest(
            id="prism.datasource.stub",
            name="Stub Data Source",
            version="1.0.0",
            api_version=1,
            entry_module="prism_datasource_stub.plugin",
            entry_class="StubDataSourcePlugin",
            description="Milestone 1 stub datasource.",
        )
        self._context: PluginContext | None = None

    @property
    def manifest(self) -> PluginManifest:
        return self._manifest

    @property
    def capabilities(self) -> DataSourceCapability:
        return DataSourceCapability.BATCH_IMPORT

    def register(self, registry: PluginRegistry) -> None:
        registry.add(
            ContributionRegistration(
                kind=ContributionKind.DATA_SOURCES,
                contribution_id="prism.datasource.stub",
                factory=self,
                display_name="Stub Data Source",
                metadata={"capabilities": ["batch_import"]},
            )
        )

    def activate(self, context: PluginContext) -> None:
        self._context = context
        context.log("info", "Stub datasource activated")

    def deactivate(self) -> None:
        self._context = None

    def discover(self, connection_or_path: str) -> list[EntityHandle]:
        return [
            EntityHandle(
                id="stub.entity",
                display_name=f"Stub ({connection_or_path})",
                kind="table",
                metadata={},
            )
        ]

    def preview(self, entity: EntityHandle, options: dict[str, Any] | None = None) -> PreviewResult:
        _ = options
        columns = (ColumnDescriptor(name="value", logical_type=LogicalType.INTEGER, nullable=True),)
        batch = pa.RecordBatch.from_pydict({"value": [1, 2, 3]})
        return PreviewResult(columns=columns, batch=batch, row_count_estimate=3)

    def materialize(
        self, entity: EntityHandle, options: dict[str, Any] | None = None
    ) -> MaterializePlan:
        _ = options
        columns = (ColumnDescriptor(name="value", logical_type=LogicalType.INTEGER, nullable=True),)
        return MaterializePlan(
            columns=columns,
            source=_EmptyBatchSource(),
            suggested_alias=entity.display_name,
            provenance={"plugin_id": self._manifest.id, "entity_id": entity.id},
        )
