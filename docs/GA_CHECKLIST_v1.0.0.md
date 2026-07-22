# GA checklist — Prism BI 1.0.0

## Identity

- [x] Host version `1.0.0`
- [x] SDK version `1.0.0`
- [x] `pyproject.toml` version / classifiers (`Production/Stable`)
- [x] About dialog shows version + license notice
- [x] Inno `MyAppVersion` = `1.0.0`

## Documentation

- [x] Professional README (GA branding)
- [x] CHANGELOG frozen for 1.0.0
- [x] Release notes (`docs/RELEASE_NOTES_v1.0.0.md`)
- [x] Known issues (post-GA)
- [x] Third-party notices
- [x] Plugin SDK guide refreshed
- [x] Project structure includes `samples/`
- [x] Architecture ADR index
- [x] Screenshots under `docs/screenshots/`
- [x] Help → Getting Started

## Sample & onboarding

- [x] `samples/data/sales_demo.csv`
- [x] `samples/SalesDemo.prism` (rebuild via `scripts/build_sample_project.py`)
- [x] `samples/README.md`

## Licensing

- [x] Root `LICENSE` (Proprietary)
- [x] Third-party redistribution notes documented

## Packaging

- [x] PyInstaller spec + `scripts/build_windows.ps1`
- [x] Portable bundle `dist/PrismBI/` produced for GA cut
- [x] Inno Setup script prepared (`packaging/windows/prism_bi.iss`)
- [ ] Inno `.exe` installer (requires local Inno Setup 6 — optional artifact)
- [x] Code-signing **process** documented (certificate is org-owned; not automated here)

## Runtime readiness

- [x] Stylesheet applied at startup
- [x] First-run Home guidance + Getting Started
- [x] Corrupt `settings.toml` does not block launch
- [x] Frozen install discovers `plugins/` next to the executable
- [x] Logging to rotating file under `~/.prism-bi/logs`
- [x] Plugin soft-fail remains default; user plugins require trust
- [x] Import/profile/export jobs with progress + cancel

## Quality gates (GA cut)

- [x] Ruff
- [x] MyPy
- [x] Import-linter
- [x] Pytest
- [x] Benchmark harness (`just bench`) available

## Intentionally deferred (post-V1 / V1.1)

- AI / auth / cloud / collaboration
- Full report designer
- Live DB connectors
- Process sandbox for plugins
