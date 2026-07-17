; Inno Setup script for the OpenLP Noir standalone installer.
; Build the PyInstaller bundle first (see OpenLP.spec), then compile with:
;   ISCC.exe packaging\installer.iss
; The setup executable is written to dist\installer\.

#define MyAppName "OpenLP Noir"
; Overridden by build.ps1 via /DMyAppVersion=<openlp/.version>; 3.1.3 is the fallback
#ifndef MyAppVersion
  #define MyAppVersion "3.1.3"
#endif
#define MyAppPublisher "OpenLP Developers"
#define MyAppURL "https://openlp.org/"
#define MyAppExeName "OpenLP.exe"

[Setup]
; Unique to this fork so it never clobbers an official OpenLP installation
AppId={{7A2E7E31-4C1F-4C7B-9A48-1E62D8B5B9D3}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=OpenLP-Noir-{#MyAppVersion}-setup
SetupIconFile=..\resources\images\OpenLP.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\OpenLP\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
