"""Shared DTO package for plugin ↔ host interchange."""

from __future__ import annotations

from prism_bi_sdk.dto.chart import ChartEncoding, ChartSpec, DashboardSpec, DashboardWidget
from prism_bi_sdk.dto.chart_data import ChartData
from prism_bi_sdk.dto.export_artifact import ExportArtifact, ExportSection
from prism_bi_sdk.dto.job import JobHandle, JobProgress, JobState
from prism_bi_sdk.dto.materialize import MaterializePlan, TabularBatchSource
from prism_bi_sdk.dto.preview import PreviewResult
from prism_bi_sdk.dto.report import ReportSectionSpec, ReportTemplate
from prism_bi_sdk.dto.schema import ColumnDescriptor, EntityHandle, LogicalType

__all__ = [
    "ChartData",
    "ChartEncoding",
    "ChartSpec",
    "ColumnDescriptor",
    "DashboardSpec",
    "DashboardWidget",
    "EntityHandle",
    "ExportArtifact",
    "ExportSection",
    "JobHandle",
    "JobProgress",
    "JobState",
    "LogicalType",
    "MaterializePlan",
    "PreviewResult",
    "ReportSectionSpec",
    "ReportTemplate",
    "TabularBatchSource",
]
