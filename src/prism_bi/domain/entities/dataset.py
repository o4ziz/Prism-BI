"""Dataset and revision entities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from prism_bi.domain.value_objects.column_schema import ColumnSchema


@dataclass(frozen=True, slots=True)
class DatasetRevision:
    """Immutable lineage node for import or cleaning commits."""

    id: UUID
    parent_id: UUID | None
    created_at: datetime
    label: str
    columns: tuple[ColumnSchema, ...] = ()


@dataclass
class Dataset:
    """Logical dataset with user-facing alias and revision lineage."""

    alias: str
    id: UUID = field(default_factory=uuid4)
    source_plugin_id: str = ""
    source_entity_id: str = ""
    revisions: list[DatasetRevision] = field(default_factory=list)
    current_revision_id: UUID | None = None

    def add_revision(self, revision: DatasetRevision, *, make_current: bool = True) -> None:
        """Append a revision and optionally point current at it."""
        self.revisions.append(revision)
        if make_current:
            self.current_revision_id = revision.id

    @staticmethod
    def new_import_revision(
        *,
        label: str = "import",
        columns: tuple[ColumnSchema, ...] = (),
    ) -> DatasetRevision:
        """Factory for an import revision with no parent."""
        return DatasetRevision(
            id=uuid4(),
            parent_id=None,
            created_at=datetime.now(UTC),
            label=label,
            columns=columns,
        )
