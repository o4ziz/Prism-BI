# Release Checklist — Prism BI v1.0.0 (GA)

Use this list to cut and ship the GA build. Check items as they are verified.

## A. Identity freeze

- [x] `prism_bi.__version__` == `1.0.0`
- [x] `prism_bi_sdk.__version__` == `1.0.0`
- [x] `pyproject.toml` version `1.0.0`
- [x] Classifier `Development Status :: 5 - Production/Stable`
- [x] Inno `MyAppVersion` == `1.0.0`
- [x] First-party plugin.toml / manifests == `1.0.0`
- [x] Help → About shows `1.0.0`

## B. Architecture & quality

- [x] ADR-001 / ADR-002 / ADR-003 still valid
- [x] Import-linter contracts kept (3/3)
- [x] Ruff check + format
- [x] MyPy
- [x] Pytest (full suite)
- [x] Benchmark harness documented (`benchmarks/README.md`)

## C. Product surface (no new features)

- [x] Plugin discovery (source + frozen next to EXE)
- [x] Soft-fail plugins + user trust gate
- [x] Project format_version 1 + additive migration
- [x] Settings.toml recovery (`.bak` + toast)
- [x] Rotating logs under `~/.prism-bi/logs`
- [x] Startup stylesheet + deferred plugin activate
- [x] First-run Home + Help → Getting Started
- [x] Sample `samples/SalesDemo.prism`
- [x] Task Center progress / cancel (M5)

## D. Packaging

- [x] `.\scripts\build_windows.ps1` produces `dist/PrismBI/PrismBI.exe`
- [x] Bundle includes `plugins/`, `samples/`, LICENSE, RELEASE_NOTES, THIRD_PARTY_NOTICES
- [ ] Optional: `.\scripts\build_windows.ps1 -InnoSetup` → `dist/PrismBI-Setup-1.0.0.exe`
- [ ] Optional: Sign EXE + installer with org Authenticode (see `packaging/windows/README.md`)
- [x] Smoke: launch portable EXE; About = 1.0.0; open Sales Demo

## E. Documentation & legal

- [x] README (GA)
- [x] CHANGELOG `[1.0.0]`
- [x] Release notes `docs/RELEASE_NOTES_v1.0.0.md`
- [x] Known issues
- [x] Screenshots refreshed (readable, with sample project)
- [x] LICENSE (Proprietary)
- [x] THIRD_PARTY_NOTICES
- [x] Plugin SDK guide
- [x] Production Readiness Report

## F. Sign-off

- [x] No blocking issues remaining
- [x] **Prism BI v1.0.0 is Release Ready.**

**Signed:** Engineering GA cut — 2026-07-22
