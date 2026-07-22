# Project structure (v1.0.0)

```
Prism BI/
├── src/
│   ├── prism_bi/                 # Application host
│   │   ├── application/          # Use cases, ports, jobs, viz/export
│   │   ├── bootstrap/            # Composition root
│   │   ├── domain/               # Entities, cleaning, profiling, reporting
│   │   ├── infrastructure/       # DuckDB, project store, config, logging, plugins
│   │   └── presentation/         # PySide6 shell, views, widgets, resources
│   └── prism_bi_sdk/             # Public plugin SDK
├── plugins/                      # First-party plugins (discovered at runtime)
├── samples/                      # GA sample .prism project + demo CSV
├── tests/                        # Unit, integration, contract, UI
├── docs/                         # ADRs, release notes, screenshots, notices
├── packaging/windows/            # PyInstaller spec + Inno Setup
├── scripts/                      # Build, sample, and screenshot helpers
├── benchmarks/                   # NFR harness
├── pyproject.toml                # Package metadata & tool config
├── importlinter_contracts.ini    # Architecture fitness functions
├── justfile                      # Developer task runner
├── LICENSE                       # Proprietary license
├── CHANGELOG.md
└── README.md
```

## Runtime layout (per project)

```
MyProject.prism/
├── project.json
├── warehouse.duckdb
└── artifacts/
```

## User data

`%USERPROFILE%\.prism-bi\` — settings, logs, recent projects, optional user plugins.
