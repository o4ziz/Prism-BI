; Prism BI — Inno Setup script (GA 1.0.0)
; Requires Inno Setup 6. Compile after PyInstaller portable build exists.
; Code signing: see packaging/windows/README.md (SignTool after compile).

#define MyAppName "Prism BI"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Prism BI"
#define MyAppExeName "PrismBI.exe"

[Setup]
AppId={{8F3C2E1A-9B4D-4F70-A2C1-7E91B4D6A8C3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\dist
OutputBaseFilename=PrismBI-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\..\dist\PrismBI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
