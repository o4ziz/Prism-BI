# Prism BI 1.0.0-rc.1 — Release Notes

**Release date:** 2026-07-22  
**Channel:** Release Candidate  
**Audience:** Internal QA, design partners, and packaging validation

## Purpose

This RC freezes the V1 feature surface for packaging and production-quality review.
It is **not** a general availability (GA) build. Expect installer and polish follow-ups
before `1.0.0`.

## What's included

- Desktop host with modules: Home, Data, Prepare, Visualize, Dashboard, Reports
- File datasources: CSV, Excel, JSON, SQLite
- DuckDB-backed `.prism` projects with revisioned datasets
- Charts: bar, line, area, pie, scatter, histogram, table (QtCharts plugin)
- Exports: CSV, Excel (XLSX), JSON, PNG, PDF
- Plugin soft-fail, rotating logs under `%USERPROFILE%\.prism-bi\logs`
- Ctrl+K command palette with workspace index

## Upgrade / install notes

- Fresh installs: use the Windows installer or portable build from `packaging/windows`.
- From source: `uv sync` then `uv run prism-bi`.
- Existing `.prism` projects from Milestone 3/4 remain format_version `1` (additive
  `reports` key is migrated automatically).

## Verification performed for this RC

- Ruff, MyPy, Pytest, Import-Linter quality gate
- Architecture ADRs 001–003 still in force
- Startup applies stylesheet; About dialog shows version and license notice
- Corrupt user settings do not prevent launch

## Not in this RC (intentional)

- AI insights / NL assist (post-V1)
- Authentication / SSO / cloud sync / collaboration
- Full paginated report designer (V1.1)
- Live PostgreSQL / SQL Server / MySQL connectors
- Code-signed installer (GA packaging track)
- Exhaustive performance hardening of 1M-row interactive benchmarks (M5)

## Feedback

Report RC defects with: OS build, Prism version from Help → About, and the relevant
excerpt from `.prism-bi\logs\prism-bi.log`.
