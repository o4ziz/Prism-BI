"""Prism BI Plugin SDK — stable public contracts for plugins.

Plugins must depend only on this package (plus optional PySide6 for UI).
They must never import ``prism_bi.infrastructure``, ``prism_bi.application``,
or ``prism_bi.bootstrap``.
"""

from __future__ import annotations

from prism_bi_sdk import dto
from prism_bi_sdk.ai import IAIProvider
from prism_bi_sdk.auth import IAuthProvider
from prism_bi_sdk.charts import IChartPlugin
from prism_bi_sdk.cleaning import ICleaningStepPlugin
from prism_bi_sdk.context import PluginContext
from prism_bi_sdk.contributions import (
    ContributionKind,
    ContributionRegistration,
    PluginRegistry,
)
from prism_bi_sdk.datasources import (
    DataSourceCapability,
    IDataSourcePlugin,
    IQueryableSource,
)
from prism_bi_sdk.exporters import IExporterPlugin
from prism_bi_sdk.license import ILicenseProvider
from prism_bi_sdk.plugin import IPlugin, PluginManifest
from prism_bi_sdk.themes import IThemeContribution

__all__ = [
    "ContributionKind",
    "ContributionRegistration",
    "DataSourceCapability",
    "IAIProvider",
    "IAuthProvider",
    "IChartPlugin",
    "ICleaningStepPlugin",
    "IDataSourcePlugin",
    "IExporterPlugin",
    "ILicenseProvider",
    "IPlugin",
    "IQueryableSource",
    "IThemeContribution",
    "PluginContext",
    "PluginManifest",
    "PluginRegistry",
    "__version__",
    "dto",
]

__version__ = "1.0.0"

# Plugin api_version major that hosts accept for this SDK release.
API_VERSION_MAJOR = 1
