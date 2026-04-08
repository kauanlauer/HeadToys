from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from headtoys.constants import APP_NAME, APP_VERSION, COMPANY_NAME, HELPER_EXE_NAME, INSTALLER_EXE_NAME, LAUNCHER_EXE_NAME

BUILD_DIR = Path(os.environ.get("HEADTOYS_BUILD_DIR", ROOT_DIR / "build"))
PACKAGE_DIR = Path(os.environ.get("HEADTOYS_PACKAGE_DIR", ROOT_DIR / "package"))
RELEASE_DIR = Path(os.environ.get("HEADTOYS_RELEASE_DIR", ROOT_DIR / "release"))
INNO_DIR = Path(os.environ.get("HEADTOYS_INNO_DIR", ROOT_DIR / "inno_build"))
ASSETS_DIR = ROOT_DIR / "installer_assets"


def add_data(source: Path, target: str) -> str:
    return f"{source}{os.pathsep}{target}"


def clean_directories() -> None:
    for process_name in (LAUNCHER_EXE_NAME, HELPER_EXE_NAME, INSTALLER_EXE_NAME):
        subprocess.run(["taskkill", "/IM", process_name, "/F"], capture_output=True, text=True)
    for directory in (BUILD_DIR, PACKAGE_DIR, RELEASE_DIR, INNO_DIR):
        if directory.exists():
            for _attempt in range(3):
                try:
                    shutil.rmtree(directory)
                    break
                except PermissionError:
                    time.sleep(1)
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    INNO_DIR.mkdir(parents=True, exist_ok=True)


def run_pyinstaller(arguments: list[str]) -> None:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(PACKAGE_DIR),
        "--workpath",
        str(BUILD_DIR),
        "--specpath",
        str(BUILD_DIR),
        *arguments,
    ]
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def build_launcher() -> None:
    run_pyinstaller(
        [
            "--onefile",
            "--windowed",
            "--name",
            LAUNCHER_EXE_NAME.removesuffix(".exe"),
            "--icon",
            str(ROOT_DIR / "logo_buscador.ico"),
            "--paths",
            str(SRC_DIR),
            "--hidden-import",
            "pystray._win32",
            "--hidden-import",
            "keyboard",
            "--hidden-import",
            "keyboard._winkeyboard",
            "--hidden-import",
            "darkdetect",
            "--hidden-import",
            "pythoncom",
            "--hidden-import",
            "pywintypes",
            "--hidden-import",
            "win32timezone",
            "--add-data",
            add_data(ROOT_DIR / "logo_buscador.png", "."),
            "--add-data",
            add_data(ROOT_DIR / "logo_buscador.ico", "."),
            str(ROOT_DIR / "src" / "headtoys_app.py"),
        ]
    )


def build_helper() -> None:
    run_pyinstaller(
        [
            "--onefile",
            "--console",
            "--name",
            HELPER_EXE_NAME.removesuffix(".exe"),
            "--icon",
            str(ROOT_DIR / "logo_buscador.ico"),
            "--paths",
            str(SRC_DIR),
            "--hidden-import",
            "pythoncom",
            "--hidden-import",
            "pywintypes",
            "--hidden-import",
            "win32timezone",
            "--hidden-import",
            "win32com",
            "--hidden-import",
            "win32com.client",
            "--hidden-import",
            "keyboard",
            "--hidden-import",
            "keyboard._winkeyboard",
            str(ROOT_DIR / "src" / "headtoys_helper.py"),
        ]
    )


def copy_release_files() -> None:
    for file_name in (LAUNCHER_EXE_NAME, HELPER_EXE_NAME):
        shutil.copy2(PACKAGE_DIR / file_name, RELEASE_DIR / file_name)


def find_iscc() -> Path:
    candidates: list[Path] = []
    custom_path = os.environ.get("INNO_ISCC", "").strip()
    if custom_path:
        candidates.append(Path(custom_path))
    candidates.extend(
        [
            Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
        ]
    )
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise FileNotFoundError("ISCC.exe não encontrado. Instale o Inno Setup 6.")


def escape_inno(value: Path | str) -> str:
    return str(value).replace('"', '""')


def write_inno_script() -> Path:
    script_path = INNO_DIR / "HeadToys.iss"
    script = f"""
[Setup]
AppId=HeadSoft.HeadToys
AppName={APP_NAME}
AppVersion={APP_VERSION}
AppPublisher={COMPANY_NAME}
DefaultDirName={{autopf32}}\\{COMPANY_NAME}\\HeadToys
DefaultGroupName={COMPANY_NAME}\\HeadToys
DisableProgramGroupPage=yes
LicenseFile="{escape_inno(ASSETS_DIR / 'license.txt')}"
OutputDir="{escape_inno(RELEASE_DIR)}"
OutputBaseFilename={INSTALLER_EXE_NAME.removesuffix('.exe')}
SetupIconFile="{escape_inno(ROOT_DIR / 'logo_buscador.ico')}"
UninstallDisplayIcon={{app}}\\logo_buscador.ico
Compression=lzma2/max
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter={LAUNCHER_EXE_NAME}
ChangesAssociations=no
VersionInfoVersion={APP_VERSION}.0
VersionInfoCompany={COMPANY_NAME}
VersionInfoDescription=Instalador do {APP_NAME}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Files]
Source: "{escape_inno(PACKAGE_DIR / LAUNCHER_EXE_NAME)}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{escape_inno(PACKAGE_DIR / HELPER_EXE_NAME)}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{escape_inno(ROOT_DIR / 'logo_buscador.ico')}"; DestDir: "{{app}}"; Flags: ignoreversion
Source: "{escape_inno(ROOT_DIR / 'logo_buscador.png')}"; DestDir: "{{app}}"; Flags: ignoreversion
[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{LAUNCHER_EXE_NAME}"; IconFilename: "{{app}}\\logo_buscador.ico"
Name: "{{autodesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{LAUNCHER_EXE_NAME}"; IconFilename: "{{app}}\\logo_buscador.ico"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{LAUNCHER_EXE_NAME}"; Description: "Executar HeadToys agora"; Flags: nowait skipifsilent; Check: IsLauncherChecked

[UninstallRun]
Filename: "{{app}}\\{HELPER_EXE_NAME}"; Parameters: "cleanup"; RunOnceId: "HeadToysCleanup"; Flags: runhidden waituntilterminated

[Code]
var
  ClientsRootPage: TInputDirWizardPage;
  OptionsPage: TInputOptionWizardPage;
  LaunchNowPage: TInputOptionWizardPage;
  ProgressPage: TOutputProgressWizardPage;

function GetAutoStart(Param: String): String;
forward;

function GetStartMinimized(Param: String): String;
forward;

function TakeField(var S: String): String;
var
  P: Integer;
begin
  P := Pos('|', S);
  if P = 0 then
  begin
    Result := S;
    S := '';
  end
  else
  begin
    Result := Copy(S, 1, P - 1);
    Delete(S, 1, P);
  end;
end;

procedure HandleHelperLog(const S: String; const Error, FirstLine: Boolean);
var
  Line: String;
  Kind: String;
  Current: Integer;
  Total: Integer;
  CategoryName: String;
  EntryName: String;
begin
  if Error then
    Exit;

  Line := Trim(S);
  if Line = '' then
    Exit;

  Kind := TakeField(Line);

  if Kind = 'STATUS' then
  begin
    ProgressPage.SetText(Line, '');
    Exit;
  end;

  if Kind = 'CATEGORY' then
  begin
    Current := StrToIntDef(TakeField(Line), 0);
    Total := StrToIntDef(TakeField(Line), 0);
    CategoryName := Line;
    ProgressPage.SetText('Detectando categorias de acesso...', Format('%d/%d  %s', [Current, Total, CategoryName]));
    if Total > 0 then
      ProgressPage.SetProgress(Current, Total)
    else
      ProgressPage.SetProgress(0, 1);
    Exit;
  end;

  if Kind = 'ENTRY' then
  begin
    Current := StrToIntDef(TakeField(Line), 0);
    Total := StrToIntDef(TakeField(Line), 0);
    CategoryName := TakeField(Line);
    EntryName := Line;
    ProgressPage.SetText('Criando atalhos na pasta Login Clientes...', Format('%d/%d  %s  -  %s', [Current, Total, CategoryName, EntryName]));
    if Total > 0 then
      ProgressPage.SetProgress(Current, Total)
    else
      ProgressPage.SetProgress(0, 1);
    Exit;
  end;

  if Kind = 'DONE' then
  begin
    Total := StrToIntDef(Line, 0);
    ProgressPage.SetText('Configuração concluída.', Format('%d cliente(s) disponível(is).', [Total]));
    if Total > 0 then
      ProgressPage.SetProgress(Total, Total)
    else
      ProgressPage.SetProgress(1, 1);
  end;
end;

procedure RunConfigurationStep;
var
  ResultCode: Integer;
  Params: String;
begin
  Params :=
    'configure --clients-root "' + ClientsRootPage.Values[0] +
    '" --install-dir "' + ExpandConstant('{{app}}') +
    '" --auto-start ' + GetAutoStart('') +
    ' --start-minimized ' + GetStartMinimized('');

  ProgressPage.SetText('Configurando HeadToys...', 'Preparando integração com a pasta dos clientes.');
  ProgressPage.SetProgress(0, 1);
  ProgressPage.Show;
  try
    ExecAndLogOutput(ExpandConstant('{{app}}\\{HELPER_EXE_NAME}'), Params, ExpandConstant('{{app}}'),
      SW_HIDE, ewWaitUntilTerminated, ResultCode, @HandleHelperLog);
    if ResultCode <> 0 then
      RaiseException('A configuração do HeadToys não foi concluída corretamente.');
  finally
    ProgressPage.Hide;
  end;
end;

procedure InitializeWizard;
begin
  ClientsRootPage := CreateInputDirPage(wpSelectDir,
    'Pasta dos clientes',
    'Selecione a raiz dos acessos',
    'Informe a pasta que contém categorias como Acessos Clientes, Homologação, Internos e outras.',
    False,
    '');
  ClientsRootPage.Add('');
  ClientsRootPage.Values[0] := ExpandConstant('{{userdocs}}');

  OptionsPage := CreateInputOptionPage(ClientsRootPage.ID,
    'Preferências iniciais',
    'Escolha o comportamento inicial do HeadToys',
    'Essas opções podem ser alteradas depois dentro do programa.',
    False,
    False);
  OptionsPage.Add('Abrir com o Windows');
  OptionsPage.Add('Iniciar minimizado na bandeja');
  OptionsPage.Values[0] := True;
  OptionsPage.Values[1] := True;

  LaunchNowPage := CreateInputOptionPage(OptionsPage.ID,
    'Finalização',
    'Inicialização após a instalação',
    'Escolha se o HeadToys deve abrir automaticamente ao concluir o setup.',
    False,
    False);
  LaunchNowPage.Add('Executar HeadToys ao concluir');
  LaunchNowPage.Values[0] := True;

  ProgressPage := CreateOutputProgressPage(
    'Configurando HeadToys',
    'Lendo os acessos, montando o índice e criando a pasta Login Clientes.'
  );
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ClientsRootPage.ID then
  begin
    if Trim(ClientsRootPage.Values[0]) = '' then
    begin
      MsgBox('Selecione a pasta principal dos clientes.', mbError, MB_OK);
      Result := False;
    end
    else if not DirExists(ClientsRootPage.Values[0]) then
    begin
      MsgBox('A pasta informada não existe.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    RunConfigurationStep;
end;

function GetClientsRoot(Param: String): String;
begin
  Result := ClientsRootPage.Values[0];
end;

function GetAutoStart(Param: String): String;
begin
  if OptionsPage.Values[0] then
    Result := '1'
  else
    Result := '0';
end;

function GetStartMinimized(Param: String): String;
begin
  if OptionsPage.Values[1] then
    Result := '1'
  else
    Result := '0';
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := '';
  S := S + MemoDirInfo + NewLine + Space + ExpandConstant('{{app}}') + NewLine + NewLine;
  S := S + 'Pasta principal dos clientes:' + NewLine + Space + ClientsRootPage.Values[0] + NewLine + NewLine;
  S := S + 'Preferências iniciais:' + NewLine;
  if OptionsPage.Values[0] then
    S := S + Space + 'Abrir com o Windows' + NewLine
  else
    S := S + Space + 'Não abrir com o Windows' + NewLine;
  if OptionsPage.Values[1] then
    S := S + Space + 'Iniciar minimizado na bandeja' + NewLine
  else
    S := S + Space + 'Iniciar com janela visível' + NewLine;
  if LaunchNowPage.Values[0] then
    S := S + Space + 'Executar o HeadToys ao concluir' + NewLine;
  Result := S;
end;

function IsLauncherChecked(): Boolean;
begin
  Result := LaunchNowPage.Values[0];
end;
"""
    script_path.write_text(script.strip() + "\n", encoding="utf-8")
    return script_path


def build_installer() -> Path:
    script_path = write_inno_script()
    iscc_path = find_iscc()
    subprocess.run([str(iscc_path), str(script_path)], cwd=ROOT_DIR, check=True)
    return RELEASE_DIR / INSTALLER_EXE_NAME


def main() -> None:
    clean_directories()
    build_launcher()
    build_helper()
    copy_release_files()
    installer_path = build_installer()
    print(installer_path)
    print(RELEASE_DIR / LAUNCHER_EXE_NAME)
    print(RELEASE_DIR / HELPER_EXE_NAME)


if __name__ == "__main__":
    main()
