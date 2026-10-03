#ifndef AppVersion
  #define AppVersion "2.1.0"
#endif
[Setup]
AppId={{3FDD6ECF-902E-4BA0-A1A9-17C5E6F693E1}
AppName=WAVEN Custom
AppVersion={#AppVersion}
AppPublisher=lReDragol
AppPublisherURL=https://github.com/lReDragol/waven-custom
DefaultDirName={localappdata}\Programs\Waven Custom
DefaultGroupName=WAVEN Custom
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\releases
OutputBaseFilename=WavenCustom-Setup-{#AppVersion}-x64
SetupIconFile=..\assets\waven-custom.ico
UninstallDisplayIcon={app}\Waven Custom.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
CloseApplications=yes
RestartApplications=no
DisableProgramGroupPage=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; Flags: unchecked
Name: "fileassoc"; Description: "Добавить WAVEN Custom в список аудиоплееров Windows"; GroupDescription: "Открытие музыки:"; Flags: checkedonce

[Files]
Source: "..\dist\Waven Custom.exe"; DestName: "waven-update-helper.exe"; Flags: dontcopy
Source: "..\dist\Waven Custom.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\WAVEN Custom"; Filename: "{app}\Waven Custom.exe"
Name: "{autodesktop}\WAVEN Custom"; Filename: "{app}\Waven Custom.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\WavenCustom.Audio\Application"; ValueType: string; ValueName: "ApplicationName"; ValueData: "WAVEN Custom"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\WavenCustom.Audio\Application"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Музыка, плейлисты и визуализации"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\WavenCustom.Audio\Application"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: """{app}\Waven Custom.exe"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "WAVEN Custom"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\Waven Custom.exe"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Waven Custom.exe"" ""%1"""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\App Paths\Waven Custom.exe"; ValueType: string; ValueName: ""; ValueData: "{app}\Waven Custom.exe"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".mp3"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".wav"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".flac"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".m4a"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".aac"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".ogg"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".opus"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".wma"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\Applications\Waven Custom.exe\SupportedTypes"; ValueType: string; ValueName: ".aiff"; ValueData: ""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\WavenCustom.Audio"; ValueType: string; ValueName: ""; ValueData: "Аудиофайл WAVEN Custom"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\WavenCustom.Audio\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: """{app}\Waven Custom.exe"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\WavenCustom.Audio\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Waven Custom.exe"" ""%1"""; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "WAVEN Custom"; Flags: uninsdeletekey; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Музыка, плейлисты и визуализации"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities"; ValueType: string; ValueName: "ApplicationIcon"; ValueData: """{app}\Waven Custom.exe"",0"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".mp3"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.mp3\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".wav"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.wav\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".flac"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.flac\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".m4a"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.m4a\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".aac"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.aac\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".ogg"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.ogg\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".opus"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.opus\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".wma"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.wma\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\WavenCustom\Capabilities\FileAssociations"; ValueType: string; ValueName: ".aiff"; ValueData: "WavenCustom.Audio"; Tasks: fileassoc
Root: HKCU; Subkey: "Software\Classes\.aiff\OpenWithProgids"; ValueType: string; ValueName: "WavenCustom.Audio"; ValueData: ""; Flags: uninsdeletevalue; Tasks: fileassoc
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "WAVEN Custom"; ValueData: "Software\WavenCustom\Capabilities"; Flags: uninsdeletevalue; Tasks: fileassoc

[Run]
Filename: "{app}\Waven Custom.exe"; Parameters: "--make-default"; Description: "Настроить открытие MP3 в WAVEN Custom (мастер с проверкой результата)"; Flags: postinstall nowait skipifsilent; Tasks: fileassoc
Filename: "{app}\Waven Custom.exe"; Description: "Запустить WAVEN Custom"; Flags: postinstall nowait skipifsilent unchecked

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
  PlayerPath: String;
begin
  Result := '';
  ExitCode := -1;
  PlayerPath := ExpandConstant('{app}\Waven Custom.exe');
  if not FileExists(PlayerPath) then exit;
  ExtractTemporaryFile('waven-update-helper.exe');
  Log('Graceful shutdown of the player being updated: ' + PlayerPath);
  if not Exec(ExpandConstant('{tmp}\waven-update-helper.exe'),
    '--prepare-update "' + PlayerPath + '"', '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
    Result := 'Не удалось запустить подготовку обновления. Закройте WAVEN Custom и повторите установку.'
  else if ExitCode <> 0 then
    Result := 'WAVEN Custom не завершил работу. Закройте его окна (включая мастер MP3) и повторите установку. Программа не будет закрыта принудительно.';
  Log('Update preparation result: ' + IntToStr(ExitCode));
end;

procedure InitializeWizard();
begin
  WizardForm.FinishedLabel.Caption := 'WAVEN Custom установлен.' + #13#10 + #13#10 +
    'Откройте мастер настройки MP3: он покажет текущий плеер, подскажет нужный пункт в Windows и проверит результат. ' +
    'Галочка запускает настройку, а не заменяет системное подтверждение.';
end;
