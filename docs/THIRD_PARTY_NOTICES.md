# Third-Party Notices

Prism BI is proprietary software. It redistributes or dynamically links the following
open-source and third-party components. License texts are available in each package's
distribution metadata (and under `.venv` when developing from source).

| Component | Typical use | License family |
|-----------|-------------|----------------|
| Python | Runtime | PSF |
| PySide6 / Qt for Python | Desktop UI, charts, PDF | LGPL / Qt commercial terms as applicable to your redistribution |
| DuckDB | Embedded analytics warehouse | MIT |
| Apache Arrow (pyarrow) | Tabular interchange | Apache-2.0 |
| openpyxl | Excel export | MIT |
| python-calamine | Excel import | MIT |
| keyring | Secret storage backend | MIT |

**Important:** Redistributing Prism BI with Qt/PySide6 may require compliance with
LGPL obligations or a Qt commercial license. Confirm your distribution model before
shipping GA installers.

Prism BI product code remains Proprietary — see [LICENSE](../LICENSE).
