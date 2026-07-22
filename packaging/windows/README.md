# Windows packaging — Prism BI 1.0.0 (GA)

This folder contains Windows packaging for the general-availability release.

## Outputs

| Artifact | Description |
|----------|-------------|
| `dist/PrismBI/` | Portable folder produced by PyInstaller |
| `dist/PrismBI-Setup-1.0.0.exe` | Optional Inno Setup installer (if Inno is installed) |

## Prerequisites

- Windows 10/11
- [uv](https://github.com/astral-sh/uv)
- Optional: [Inno Setup 6](https://jrsoftware.org/isinfo.php) for `.exe` installer
- Optional: Authenticode certificate + Windows SDK `signtool.exe` for signing

## Build portable app

From the repository root:

```powershell
.\scripts\build_windows.ps1
```

This will:

1. `uv sync --extra packaging --extra dev`
2. Run PyInstaller with `packaging/windows/prism_bi.spec`
3. Copy first-party `plugins/` next to the executable
4. Copy `LICENSE`, `README.md`, release notes, and third-party notices into the bundle
5. Copy `samples/` into the bundle (demo project)

Run the portable build:

```powershell
.\dist\PrismBI\PrismBI.exe
```

## Build installer (optional)

```powershell
.\scripts\build_windows.ps1 -InnoSetup
```

Requires `ISCC.exe` on `PATH` or the default Inno install location.

## Code signing (organizational)

Signing is **not** automated in-repo (certificates are org-owned). After building:

```powershell
# Sign the portable executable
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /a dist\PrismBI\PrismBI.exe

# After Inno compile, sign the installer
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 `
  /a dist\PrismBI-Setup-1.0.0.exe
```

Replace `/a` with `/f your.pfx /p ...` or a CSP/token flag as required by your CA.
Verify with `signtool verify /pa dist\PrismBI\PrismBI.exe`.

Unsigned builds remain functionally valid for internal distribution; public
distribution should use a signed installer.

## Smoke checklist after build

1. Launch `PrismBI.exe`
2. Help → About shows `1.0.0`
3. File → Open Project → `samples/SalesDemo.prism` (inside the bundle or repo)
4. Visualize shows the seeded chart; Data grid loads
5. Import a small CSV; confirm Task Center progress
6. Confirm logs under `%USERPROFILE%\.prism-bi\logs`
