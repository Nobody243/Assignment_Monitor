; Inno Setup script for Assignment Monitor.
; Built by build.py:  ISCC installer.iss /DAppVersion=1.0.0 /DSourceDir=dist\AssignmentMonitor
; Installs per user (no administrator rights needed) into %LOCALAPPDATA%\Programs.

#define MyAppName "Assignment Monitor"
#define MyAppExe "AssignmentMonitor.exe"
#define MyPublisher "Nobody243"
#define MyURL "https://github.com/Nobody243/Assignment_Monitor"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#ifndef SourceDir
  #define SourceDir "dist\AssignmentMonitor"
#endif

[Setup]
AppId={{7E1C2B6A-5D4F-4C0A-9B3E-2F6A1D9C4B57}
AppName={#MyAppName}
AppVersion={#AppVersion}
AppVerName={#MyAppName} {#AppVersion}
AppPublisher={#MyPublisher}
AppPublisherURL={#MyURL}
AppSupportURL={#MyURL}/issues
AppUpdatesURL={#MyURL}/releases/latest
DefaultDirName={userpf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=AssignmentMonitor-Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
UninstallDisplayName={#MyAppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Shortcuts:"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
; silent in-app update: relaunch automatically (the updater passes /RELAUNCH=1)
Filename: "{app}\{#MyAppExe}"; Flags: nowait; Check: ShouldRelaunch

[UninstallRun]
Filename: "{app}\{#MyAppExe}"; Parameters: "--quit"; Flags: runhidden; RunOnceId: "QuitApp"
Filename: "{app}\{#MyAppExe}"; Parameters: "--disable-automation"; Flags: runhidden; RunOnceId: "DisableAutomation"

[UninstallDelete]
; the browser profile and downloaded engine are large and fully rebuildable; settings and data are kept
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}\chrome_profile"
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}\browsers"

[Code]
function ShouldRelaunch: Boolean;
begin
  Result := ExpandConstant('{param:RELAUNCH|0}') = '1';
end;

// A running instance may be hidden in the tray with no window, so ask it to quit before files are replaced.
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Exe: String;
  ResultCode: Integer;
  Ok: Boolean;
begin
  Exe := ExpandConstant('{app}\{#MyAppExe}');
  if FileExists(Exe) then
  begin
    // polite request first (new builds), then force-close anything left (older builds)
    Ok := Exec(Exe, '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Log(Format('PrepareToInstall: --quit exec=%d code=%d', [Integer(Ok), ResultCode]));
    Sleep(2000);
    Ok := Exec(ExpandConstant('{cmd}'), '/C taskkill /IM {#MyAppExe} /F /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Log(Format('PrepareToInstall: taskkill exec=%d code=%d', [Integer(Ok), ResultCode]));
    Sleep(1500);
  end;
  Result := '';
end;
