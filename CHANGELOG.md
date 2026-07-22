# Changelog

All notable changes to Prism BI are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-07-22

General Availability release of Prism BI.

### Added

- Sample project `samples/SalesDemo.prism` and rebuild script
- Help → Getting Started walkthrough
- GA documentation set (release notes, checklist, production readiness report)
- Benchmark documentation (`benchmarks/README.md`)

### Changed

- Version identity set to `1.0.0` across host, SDK, first-party plugins, and packaging
- Development Status classifier set to Production/Stable
- Task Center dock naming aligned; packaging docs describe code-signing process
- Screenshots recaptured with Sales Demo on a real Windows Qt platform
- Project migration cleaned (additive v1 defaults; pre-v1 formats rejected)

### Removed

- Unused domain helpers (`CorrelationId`, `DataQualityError`, empty `domain.services`)
- Unused `log_extra` logging helper

### Included from Milestone 5 (hardening)

- Background jobs for import / profile / export with progress + cancel
- DuckDB `memory_limit` / threads from `memory_budget_mb`
- Deferred plugin activation; user-plugin trust gate (`plugins.trusted_ids`)
- Path validation; corrupt settings `.bak` recovery + toast
- Chart truncation banner; empty states; focus / accessible-name polish
- Benchmark harness (`benchmarks/run_bench.py`, `just bench`)
- Security checklist (`docs/architecture/security-checklist-m5.md`)

## [1.0.0rc1] — 2026-07-22

Release Candidate for Prism BI v1.0.0.

### Added

- Full V1 analyst workstation path: import → profile → clean → explore → visualize →
  dashboard → report/export
- Plugin-based datasources (CSV, Excel, JSON, SQLite), QtCharts engine, and exporters
  (CSV, XLSX, JSON, PNG, PDF)
- Template-based lightweight reports (not a full report designer)
- Command palette index for datasets, columns, dashboards, charts, and reports
- Windows packaging scripts (PyInstaller + optional Inno Setup)
- Professional product documentation, release notes, and screenshot pack
- Graceful recovery when user `settings.toml` is corrupt

### Changed

- Version identity set to `1.0.0rc1` across host and SDK packages
- Application stylesheet applied at startup; Home first-run guidance improved
- Development status classifier set to Beta for the RC

### Fixed

- User settings parse failures no longer block application startup

## Historical milestones (pre-1.0)

### Milestone 4 — Export & lightweight reporting

- `ExportArtifact` + `IExporterPlugin` contract ([ADR-003](docs/architecture/ADR-003-export-contract.md))
- Tabular / image / PDF exporter plugins
- Report templates persisted on the project

### Milestone 3 — Visualization

- Chart/dashboard specs, QtCharts plugin, Visualize & Dashboard UI
- ([ADR-002](docs/architecture/ADR-002-visualization-abstraction.md))

### Milestone 2 — Core data engine

- `.prism` project store, DuckDB analytics store, profiling & cleaning
- ([ADR-001](docs/architecture/ADR-001-duckdb-access.md))

### Milestone 1 — Foundation

- SDK shell, plugin host, PySide6 chrome, jobs, config, logging

[1.0.0]: https://github.com/prism-bi/prism-bi/releases/tag/v1.0.0
[1.0.0rc1]: https://github.com/prism-bi/prism-bi/releases/tag/v1.0.0rc1
