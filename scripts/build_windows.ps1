#Requires -Version 5.1
<#
.SYNOPSIS
  Build Prism BI Windows portable app (and optional Inno Setup installer).

.PARAMETER InnoSetup
  If set, compile packaging/windows/prism_bi.iss after the portable build.
#>
param(
    [switch]$InnoSetup
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "==> Sync packaging dependencies"
uv sync --extra packaging --extra dev

Write-Host "==> Clean previous dist/build"
if (Test-Path "dist\PrismBI") { Remove-Item -Recurse -Force "dist\PrismBI" }
if (Test-Path "build\pyinstaller") { Remove-Item -Recurse -Force "build\pyinstaller" }

Write-Host "==> PyInstaller"
uv run pyinstaller `
  --noconfirm `
  --distpath dist `
  --workpath build\pyinstaller `
  packaging\windows\prism_bi.spec

$Bundle = Join-Path $Root "dist\PrismBI"
if (-not (Test-Path (Join-Path $Bundle "PrismBI.exe"))) {
    throw "PyInstaller did not produce dist\PrismBI\PrismBI.exe"
}

Write-Host "==> Copy plugins and docs into bundle"
Copy-Item -Recurse -Force "plugins" (Join-Path $Bundle "plugins")
Copy-Item -Force "LICENSE" (Join-Path $Bundle "LICENSE")
Copy-Item -Force "README.md" (Join-Path $Bundle "README.md")
Copy-Item -Force "docs\THIRD_PARTY_NOTICES.md" (Join-Path $Bundle "THIRD_PARTY_NOTICES.md")
Copy-Item -Force "docs\RELEASE_NOTES_v1.0.0.md" (Join-Path $Bundle "RELEASE_NOTES.md")
if (Test-Path "samples") {
    Copy-Item -Recurse -Force "samples" (Join-Path $Bundle "samples")
}

Write-Host "==> Portable build ready: $Bundle"

if ($InnoSetup) {
    $iscc = $null
    foreach ($candidate in @(
        "ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )) {
        if (Get-Command $candidate -ErrorAction SilentlyContinue) {
            $iscc = (Get-Command $candidate).Source
            break
        }
        if (Test-Path $candidate) {
            $iscc = $candidate
            break
        }
    }
    if (-not $iscc) {
        throw "Inno Setup compiler (ISCC.exe) not found. Install Inno Setup 6 or omit -InnoSetup."
    }
    Write-Host "==> Compiling installer with $iscc"
    & $iscc "packaging\windows\prism_bi.iss"
    Write-Host "==> Installer written under dist\"
}

Write-Host "Done."
