; Instalador de usuario para Windows x64 con Inno Setup 6.
; Se genera con: packaging\build_installer.bat

#define MyAppName "Prensa Marshall USB-4716"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Universidad de Cantabria"
#define MyAppExeName "PrensaMarshallUSB4716.exe"

[Setup]
AppId={{7B2098B6-27C1-4E25-92F1-A8E270159B20}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\Universidad de Cantabria\Prensa Marshall USB-4716
DefaultGroupName=Universidad de Cantabria\Prensa Marshall USB-4716
AllowNoIcons=no
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=Instalar_PrensaMarshallUSB4716
SetupIconFile=..\assets\prensa_marshall_uc.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "..\dist\PrensaMarshallUSB4716\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Prensa Marshall USB-4716"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\Prensa Marshall USB-4716"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar Prensa Marshall USB-4716"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir Prensa Marshall USB-4716"; Flags: nowait postinstall skipifsilent
