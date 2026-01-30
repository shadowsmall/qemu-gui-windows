[Setup]
AppName=qemugui Pro
AppVersion=1.0
DefaultDirName={autopf}\qemugui
DefaultGroupName=qemugui
OutputDir=.
OutputBaseFilename=qemugui_Full_Setup
SetupIconFile=qemugui.ico
Compression=lzma
SolidCompression=yes

[Files]
; Ton application
Source: "dist\qemugui.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "qemugui.ico"; DestDir: "{app}"; Flags: ignoreversion

; L'installeur de QEMU (à inclure dans le package)
Source: "qemu-setup-x86_64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autoprograms}\qemugui"; Filename: "{app}\qemugui.exe"
Name: "{autodesktop}\qemugui"; Filename: "{app}\qemugui.exe"; IconFilename: "{app}\qemugui.ico"

[Run]
; 1. Installation de QEMU en mode silencieux (/S)
; On l'installe AVANT de lancer l'app pour que les dépendances soient là
Filename: "{tmp}\qemu-setup-x86_64.exe"; Parameters: "/S"; StatusMsg: "Installation de QEMU (dépendance requise)..."; Flags: runascurrentuser

; 2. Lancement de ton application à la fin
Filename: "{app}\qemugui.exe"; Description: "Lancer qemugui"; Flags: nowait postinstall skipifsilent