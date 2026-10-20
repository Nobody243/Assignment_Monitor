; Inno Setup script for Assignment Monitor.
; Built by build.py:  ISCC installer.iss /DAppVersion=1.1.0 /DSourceDir=dist\AssignmentMonitor
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

[UninstallDelete]
; everything the app created outside the install folder that is safe to drop without asking:
; the browser profile and downloaded engine (large, rebuildable) and any files written inside the install folder
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}\chrome_profile"
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}\browsers"
Type: filesandordirs; Name: "{app}\_internal"
; the saved sign-in, settings and cached assignments are removed in [Code] after asking the user

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

// ---------------------------------------------------------------- uninstall: leave nothing behind
// Order matters: stop every running copy first (tray window, a background --check or --remind task), then
// unregister the scheduled tasks and the Startup-folder script, then let Inno remove the files. The app's own
// --disable-automation does the unregistering; the direct schtasks calls below are a safety net in case the
// executable cannot run (corrupted install, missing DLL).
procedure KillRunningCopies;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{app}\{#MyAppExe}'), '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1500);
  Exec(ExpandConstant('{cmd}'), '/C taskkill /IM {#MyAppExe} /F /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(800);
end;

procedure RemoveAutomation;
var
  ResultCode: Integer;
  Names: array[0..6] of String;
  I: Integer;
begin
  Exec(ExpandConstant('{app}\{#MyAppExe}'), '--disable-automation', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Names[0] := 'AssignmentMonitor_DailyCheck';
  Names[1] := 'AssignmentMonitor_HourlyReminder';
  Names[2] := 'AssignmentMonitor_LogonCheck';
  Names[3] := 'BahriaLMS_DailyCheck';
  Names[4] := 'BahriaLMS_HourlyReminder';
  Names[5] := 'BahriaLMS_LogonCheck';
  Names[6] := 'BahriaLMS_HourlyUrgentReminder';
  for I := 0 to 6 do
    Exec(ExpandConstant('{cmd}'), '/C schtasks /Delete /F /TN ' + Names[I], '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  DeleteFile(ExpandConstant('{userstartup}\AssignmentMonitor_Startup.vbs'));
  DeleteFile(ExpandConstant('{userstartup}\BahriaLMS_Startup.vbs'));
  DeleteFile(ExpandConstant('{userstartup}\{#MyAppName}.lnk'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    KillRunningCopies;
    RemoveAutomation;
  end;
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{localappdata}\{#MyAppName}');
    if DirExists(DataDir) then
    begin
      // interactive uninstall (Windows Settings, Start Menu): ask; silent uninstall keeps the data
      if UninstallSilent or
         (MsgBox('Also delete your saved sign-in, settings and cached assignments?' + #13#10 + #13#10 +
                 'Choose No if you plan to reinstall and want to keep your account signed in.',
                 mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES) then
      begin
        if not UninstallSilent then
          DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
