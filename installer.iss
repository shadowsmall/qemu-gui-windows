[Setup]
AppName=qemugui
AppVersion=1.0
DefaultDirName={autopf}\qemugui
DefaultGroupName=qemugui
OutputDir=.
OutputBaseFilename=qemugui_setup
SetupIconFile=qemugui.png
Compression=lzma
SolidCompression=yes

[Files]
; On prend l'exe généré par PyInstaller
Source: "dist\qemugui.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "qemugui.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\qemugui"; Filename: "{app}\qemugui.exe"
Name: "{autodesktop}\qemugui"; Filename: "{app}\qemugui.exe"; IconFilename: "{app}\qemugui.png"

[Run]
Filename: "{app}\qemugui.exe"; Description: "Lancer qemugui"; Flags: nowait postinstall skipifsilent
