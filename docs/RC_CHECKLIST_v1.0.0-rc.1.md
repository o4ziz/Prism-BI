# Release Candidate checklist — Prism BI 1.0.0-rc.1

## Identity

- [x] Host version `1.0.0rc1`
- [x] SDK version `1.0.0rc1`
- [x] `pyproject.toml` version / classifiers updated (Beta)
- [x] About dialog shows version + license notice

## Documentation

- [x] Professional README
- [x] CHANGELOG
- [x] Release notes (`docs/RELEASE_NOTES_v1.0.0-rc.1.md`)
- [x] Known issues
- [x] Third-party notices
- [x] Plugin SDK guide refreshed
- [x] Project structure doc
- [x] Architecture ADR index
- [x] Screenshots under `docs/screenshots/`

## Licensing

- [x] Root `LICENSE` (Proprietary)
- [x] Third-party redistribution notes documented

## Packaging

- [x] PyInstaller spec + `scripts/build_windows.ps1`
- [x] Portable bundle `dist/PrismBI/` produced
- [x] Inno Setup script prepared (`packaging/windows/prism_bi.iss`)
- [ ] Inno `.exe` installer (requires local Inno Setup 6)
- [ ] Code signing (deferred to GA)

## Runtime readiness

- [x] Stylesheet applied at startup
- [x] First-run Home guidance
- [x] Corrupt `settings.toml` does not block launch
- [x] Frozen install discovers `plugins/` next to the executable
- [x] Logging to rotating file under `~/.prism-bi/logs`
- [x] Plugin soft-fail remains default

## Quality gates (RC cut)

- [x] Ruff
- [x] MyPy
- [x] Import-linter
- [x] Pytest (43)

## Intentionally deferred

- Milestone 5 performance / a11y hardening
- Milestone 6 GA signing, sample projects, help content polish
- Post-V1 AI / auth / cloud / collaboration
