"""Domain skeleton tests (Phase 1.2)."""

from __future__ import annotations

from prism_bi.domain.entities import Dataset, Project
from prism_bi.domain.errors import ValidationError
from prism_bi.domain.value_objects import ColumnSchema
from prism_bi_sdk.dto.schema import LogicalType


def test_project_dataset_lineage() -> None:
    project = Project(name="Demo")
    dataset = Dataset(alias="Sales")
    revision = Dataset.new_import_revision(
        columns=(ColumnSchema(name="amount", logical_type=LogicalType.FLOAT),)
    )
    dataset.add_revision(revision)
    project.add_dataset(dataset)
    assert project.get_dataset(dataset.id) is dataset
    assert dataset.current_revision_id == revision.id


def test_validation_error_has_code() -> None:
    err = ValidationError("bad")
    assert err.code == "validation_error"
