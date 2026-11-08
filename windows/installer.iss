; Script de Instalação Inno Setup para DJ Downloader
; Otimizado para Windows 11 e Windows 10 (64-bit)

#define MyAppName "DJ Downloader"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Raphael Minas"
#define MyAppExeName "DJ Downloader.exe"
#define MyAppAssocName MyAppName + " File"

[Setup]
; Identificador único da aplicação
AppId={{9F27C341-B834-4A82-9572-1DE9D3D8A291}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={userappdata}\..\Local\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Sem necessidade de privilégios de Administrador (instalação segura e limpa no perfil do usuário)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Estilo e compatibilidade Windows 11
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=..\dist-installer
OutputBaseFilename=DJ-Downloader-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes

; Metadados para Windows SmartScreen e Adicionar/Remover Programas
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription="DJ Downloader - Baixe playlists e faixas em alta qualidade com tags para DJs"

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Todos os arquivos compilados pelo PyInstaller
Source: "..\dist\DJ Downloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\assets\icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
