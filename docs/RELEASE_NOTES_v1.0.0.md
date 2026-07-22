# Prism BI 1.0.0 — Release Notes

**Release date:** 2026-07-22  
**Channel:** General Availability (GA)  
**Product:** Prism BI desktop Business Intelligence workstation

## Highlights

Prism BI **1.0.0** is the first production release. Analysts can import heterogeneous
files, profile and clean data, explore large tables, build charts and dashboards,
and export CSV, Excel, JSON, PNG, and PDF — without hardcoding schemas.

## What's in 1.0.0

- **Modules:** Home, Data, Prepare, Visualize, Dashboard, Reports
- **Datasources:** CSV, Excel, JSON, SQLite (plugin-based)
- **Warehouse:** DuckDB-backed `.prism` projects with revisioned datasets
- **Charts:** bar, line, area, pie, scatter, histogram, table (QtCharts plugin)
- **Export:** CSV, XLSX, JSON, PNG, PDF via exporter plugins
- **Jobs:** background import / profile / export with progress and cancel (Task Center)
- **Reliability:** plugin soft-fail, user-plugin trust list, settings recovery, path checks
- **Sample:** `samples/SalesDemo.prism` — open via File → Open Project
- **Help:** Help → Getting Started walkthrough; Ctrl+K command palette

## Install

| Method | How |
|--------|-----|
| Portable | Build with `.\scripts\build_windows.ps1`, run `dist\PrismBI\PrismBI.exe` |
| Installer | Optional Inno Setup: `.\scripts\build_windows.ps1 -InnoSetup` |
| From source | `uv sync` then `uv run prism-bi` |

Public distribution should apply Authenticode signing (see `packaging/windows/README.md`).

## Upgrade notes

- Existing Milestone 3/4 `.prism` projects remain `format_version` **1**
- Missing `charts` / `dashboards` / `reports` keys are filled on load
- Corrupt `settings.toml` is renamed to `settings.toml.bak`; defaults apply

## Verification

- Architecture ADRs 001–003 in force; import-linter contracts kept
- Ruff, MyPy, Pytest, Import-linter passed for the GA cut
- Milestone 5 hardening (performance / security) included
- Production readiness report: `docs/PRODUCTION_READINESS_REPORT_v1.0.0.md`

## Known limitations

See [KNOWN_ISSUES.md](KNOWN_ISSUES.md) (performance hardware dependence, simple PDF
layout, Excel export memory cap, stub AI plugin visibility, optional installer/signing,
chart screen-reader depth).

## Not included (intentional)

- AI insights / natural-language assist (post-V1)
- Authentication / SSO / cloud sync / collaboration
- Full paginated report designer (planned V1.1)
- Live PostgreSQL / SQL Server / MySQL connectors
- Process-level plugin sandboxing

## Support

When reporting issues, include: Windows build, version from **Help → About**, and the
relevant excerpt from `%USERPROFILE%\.prism-bi\logs\prism-bi.log`.
