@echo off
setlocal enableDelayedExpansion

chcp 65001 >nul

set "thisDir=%~dp0"
set "app_name=Splatoon3RSDBEditor"
set "script_name=Splatoon3-RSDBEditor\main.py"
set "py_ver=3.12.10"
set "modules=PyQt6 requests zstandard byml darkdetect packaging"
set "tried=0"
set "venv_dir=!thisDir!.venv"
set "venv_py=!venv_dir!\Scripts\python.exe"

set "syspath=%SYSTEMROOT%\system32\"
set "pspath=%SYSTEMROOT%\system32\WindowsPowerShell\v1.0\powershell.exe"
set "curlpath=%SYSTEMROOT%\system32\curl.exe"

set "ADVANCED_LOGS=False"
set "CONFIG_FILE=!thisDir!Splatoon3-RSDBEditor\splatoon_RSDBeditor_config.json"
if exist "!CONFIG_FILE!" (
    "!pspath!" -NoProfile -Command "try{$j=Get-Content '!CONFIG_FILE!' -Raw|ConvertFrom-Json; if($j.advanced_logs -eq $true){exit 1}else{exit 0}}catch{exit 0}" >nul 2>&1
    if !ERRORLEVEL! EQU 1 set "ADVANCED_LOGS=True"
)

if "!ADVANCED_LOGS!"=="True" (
    echo [%DATE% %TIME%] ----- BOOTSTRAP START -----
)

set "arch=amd64"
if "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "arch=win32"

title Setup : !app_name!

set "OS_LOCALE="
for /f "tokens=3" %%a in ('reg query "HKCU\Control Panel\International" /v LocaleName 2^>nul') do set "OS_LOCALE=%%a"

if "!OS_LOCALE!"=="" (
    if "!ADVANCED_LOGS!"=="True" echo [%DATE% %TIME%] No language detected, defaulting to English.
    set "LANG_CODE=EN"
) else (
    set "LANG_CODE=EN"
    if /i "!OS_LOCALE:~0,2!"=="fr" set "LANG_CODE=FR"
)

if "!LANG_CODE!"=="FR" (
    set "MSG_FILE_MISSING=[ERREUR] Le fichier est introuvable :"
    set "MSG_ALREADY_RUNNING=[INFO] L'application est déjà en cours d'exécution."
    set "MSG_SHIFT_INFO=[INFO] Maintenez SHIFT enfoncé (3s) pour purger le cache et l'environnement."
    set "MSG_SHIFT_DETECTED=[!] Touche SHIFT détectée. Purge en cours..."
    set "MSG_PURGE_SUCCESS=[OK] Cache et environnement virtuel purgés avec succès."
    set "MSG_CHK_PY=[1/3] Vérification de l'installation de Python (3.11 ou 3.12)..."
    set "MSG_REQ_PY=[ERREUR] Python 3.11 ou 3.12 est requis pour garantir la compatibilité."
    set "MSG_INSTALL_TITLE=INSTALLATION DE PYTHON"
    set "MSG_INSTALL_DESC=Python 3.12 est strictement requis pour installer les librairies de l'éditeur."
    set "MSG_PROMPT_INSTALL=Voulez-vous l'installer maintenant ? [y/n]: "
    set "MSG_FIND_PY=[2/3] Préparation du téléchargement de Python 3.12..."
    set "MSG_PY_FOUND=[INFO] Version ciblée - Téléchargement en cours :"
    set "MSG_DL_FAIL=[ERREUR] Échec du téléchargement."
    set "MSG_INSTALLING=[INFO] Installation de Python en cours..."
    set "MSG_SETUP_MOD=[3/3] Configuration de l'environnement virtuel..."
    set "MSG_CLEAN_PIP=[INFO] Création de l'environnement virtuel isolé (.venv)..."
    set "MSG_UP_PIP=[INFO] Mise à jour de PIP..."
    set "MSG_INS_COMP=[INFO] Installation des dépendances requises..."
    set "MSG_ERR_MOD=[ATTENTION] Une erreur est survenue lors de l'installation des modules."
    set "MSG_ERR_DETAIL=--- DETAIL DE L'ERREUR ---"
    set "MSG_LAUNCH=[INFO] LANCEMENT :"
    set "MSG_PY_EXE=[INFO] Exécutable Python :"
    set "MSG_ERR_EXIT=[ERREUR] L'application s'est arrêtée suite à une erreur (Code :"
    set "MSG_STARTING=[INFO] Démarrage en cours..."
) else (
    set "MSG_FILE_MISSING=[ERROR] File not found :"
    set "MSG_ALREADY_RUNNING=[INFO] Application is already running."
    set "MSG_SHIFT_INFO=[INFO] Hold down SHIFT (3s) to clear the cache and environment."
    set "MSG_SHIFT_DETECTED=[!] SHIFT key detected. Purging..."
    set "MSG_PURGE_SUCCESS=[OK] Cache and virtual environment purged successfully."
    set "MSG_CHK_PY=[1/3] Checking for Python (3.11 or 3.12) installation..."
    set "MSG_REQ_PY=[ERROR] Python 3.11 or 3.12 is required for compatibility."
    set "MSG_INSTALL_TITLE=PYTHON SETUP"
    set "MSG_INSTALL_DESC=Python 3.12 is strictly required to install the editor libraries."
    set "MSG_PROMPT_INSTALL=Install now? [y/n]: "
    set "MSG_FIND_PY=[2/3] Preparing download for Python 3.12..."
    set "MSG_PY_FOUND=[INFO] Target version - Downloading :"
    set "MSG_DL_FAIL=[ERROR] Download failed."
    set "MSG_INSTALLING=[INFO] Installing Python..."
    set "MSG_SETUP_MOD=[3/3] Virtual environment setup..."
    set "MSG_CLEAN_PIP=[INFO] Creating isolated virtual environment (.venv)..."
    set "MSG_UP_PIP=[INFO] Updating PIP..."
    set "MSG_INS_COMP=[INFO] Installing required dependencies..."
    set "MSG_ERR_MOD=[WARNING] An error occurred while installing modules."
    set "MSG_ERR_DETAIL=--- ERROR DETAIL ---"
    set "MSG_LAUNCH=[INFO] LAUNCHING :"
    set "MSG_PY_EXE=[INFO] Python Executable :"
    set "MSG_ERR_EXIT=[ERROR] Application stopped due to an error (Code :"
    set "MSG_STARTING=[INFO] Starting application..."
)

if exist "!thisDir!!script_name!" goto skip_missing
echo !MSG_FILE_MISSING! !script_name!
pause
exit /b 1
:skip_missing

"!pspath!" -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter \"CommandLine LIKE '%%--id=!app_name!%%' AND Name LIKE '%%python%%'\" -ErrorAction SilentlyContinue; if ($p) { exit 1 } else { exit 0 }" >nul 2>&1
if !ERRORLEVEL! EQU 1 (
    echo !MSG_ALREADY_RUNNING!
    "!syspath!ping.exe" -n 3 127.0.0.1 >nul
    exit /b
)
:skip_running

echo !MSG_SHIFT_INFO!
"!pspath!" -NoProfile -Command "Add-Type -AssemblyName System.Windows.Forms; $end=(Get-Date).AddSeconds(3); while((Get-Date) -lt $end){ if([System.Windows.Forms.Control]::ModifierKeys -match 'Shift'){exit 1}; Start-Sleep -Milliseconds 100 }; exit 0"
if !ERRORLEVEL! NEQ 1 (
    cls
    goto read_env
)

echo.
echo !MSG_SHIFT_DETECTED!
if exist "!venv_dir!" rd /s /q "!venv_dir!" >nul 2>&1
for /d /r "%thisDir%" %%d in (__pycache__ cache) do if exist "%%d" rd /s /q "%%d" >nul 2>&1
echo !MSG_PURGE_SUCCESS!
"!syspath!ping.exe" -n 2 127.0.0.1 >nul
cls

:read_env
if exist "!venv_py!" (
    "!venv_py!" -c "import PyQt6, requests, zstandard, byml, darkdetect, packaging" >nul 2>&1
    if !ERRORLEVEL! EQU 0 goto runscript_fast
)

:checkpy
echo !MSG_CHK_PY!
set "pypath="
set "pydir="

set "target_local_py=%LocalAppData%\Programs\Python\Python312\python.exe"
if exist "!target_local_py!" (
    call :checkpyversion "!target_local_py!"
    if defined pypath goto checkdeps
)

set "local_root=%LocalAppData%\Programs\Python"
if exist "!local_root!" (
    for /f "delims=" %%d in ('dir /b /ad "!local_root!\Python3*" 2^>nul') do (
        if exist "!local_root!\%%d\python.exe" (
            call :checkpyversion "!local_root!\%%d\python.exe"
            if defined pypath goto checkdeps
        )
    )
)

for /f "tokens=*" %%x in ('"!syspath!where.exe" python 2^>nul') do (
    call :checkpyversion "%%x"
    if defined pypath goto checkdeps
)

if !tried! lss 1 goto askinstall

echo.
echo !MSG_REQ_PY!
pause
exit /b 1

:checkpyversion
set "v_raw="
for /f "tokens=2" %%a in ('"%~1" -V 2^>^&1') do set "v_raw=%%a"
if not defined v_raw goto :EOF

for /f "tokens=1,2 delims=." %%i in ("!v_raw!") do (
    set "major=%%i"
    set "minor=%%j"
)

if "!major!"=="3" (
    if "!minor!"=="12" (
        set "pypath=%~1"
        set "pydir=%~dp1"
    )
    if "!minor!"=="11" (
        set "pypath=%~1"
        set "pydir=%~dp1"
    )
)
goto :EOF

:askinstall
echo.
echo ============================================================
echo   !MSG_INSTALL_TITLE!
echo ============================================================
echo.
echo !MSG_INSTALL_DESC!
echo.

:prompt_loop
set "menu="
set /p "menu=!MSG_PROMPT_INSTALL!"
if /i "!menu!"=="y" goto installpy
if /i "!menu!"=="yes" goto installpy
if /i "!menu!"=="o" goto installpy
if /i "!menu!"=="oui" goto installpy
if /i "!menu!"=="n" exit /b 0
if /i "!menu!"=="no" exit /b 0
if /i "!menu!"=="non" exit /b 0
goto prompt_loop

:installpy
set /a tried+=1
echo.
echo !MSG_FIND_PY!
echo !MSG_PY_FOUND! !py_ver!

set "url=https://www.python.org/ftp/python/!py_ver!/python-!py_ver!-!arch!.exe"
set "py_exe=%TEMP%\pyinstall.exe"

if exist "!curlpath!" ( 
    "!curlpath!" -skL -o "!py_exe!" "!url!" 
) else ( 
    "!pspath!" -NoProfile -Command "[System.Net.ServicePointManager]::ServerCertificateValidationCallback={$true}; [Net.ServicePointManager]::SecurityProtocol=@('Tls12','Tls13'); (New-Object System.Net.WebClient).DownloadFile('!url!','!py_exe!')" 
)

if not exist "!py_exe!" ( 
    echo !MSG_DL_FAIL!
    pause
    goto checkpy 
)

echo.
echo !MSG_INSTALLING!
pushd "%TEMP%"
pyinstall.exe /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 Include_pip=1 Include_launcher=1
popd

del /f /q "!py_exe!" >nul 2>&1
"!syspath!ping.exe" -n 3 127.0.0.1 >nul
goto checkpy

:checkdeps
echo.
echo !MSG_SETUP_MOD!

echo.
echo !MSG_CLEAN_PIP!
if exist "!venv_dir!" rd /s /q "!venv_dir!" >nul 2>&1
"!pypath!" -m venv "!venv_dir!"
if not exist "!venv_py!" (
    echo !MSG_ERR_MOD!
    pause
    exit /b 1
)
echo OK.

echo.
echo !MSG_UP_PIP!
"!venv_py!" -m pip install --upgrade pip --no-warn-script-location > "%TEMP%\pip_err.log" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo !MSG_ERR_MOD!
    echo !MSG_ERR_DETAIL!
    type "%TEMP%\pip_err.log"
    echo ============================
) else (
    echo OK.
)

echo.
echo !MSG_INS_COMP!
"!venv_py!" -m pip install !modules! --no-warn-script-location > "%TEMP%\pip_err.log" 2>&1
if !ERRORLEVEL! NEQ 0 (
    echo !MSG_ERR_MOD!
    echo.
    echo !MSG_ERR_DETAIL!
    type "%TEMP%\pip_err.log"
    echo ============================
    pause
    goto runscript_fast
)
echo OK.

:runscript_fast
set PYTHONUNBUFFERED=1

if "!ADVANCED_LOGS!"=="True" (
    echo.
    echo ============================================================
    echo   !MSG_LAUNCH! !script_name!
    echo ============================================================
    echo.
    echo !MSG_PY_EXE! !venv_py!
    echo.
) else (
    echo.
    echo !MSG_STARTING!
    echo OK.
    echo.
)

"!venv_py!" "!thisDir!!script_name!" --id=!app_name!
set "PY_ERR=!ERRORLEVEL!"

if !PY_ERR! EQU 0 goto cleanup
echo.
echo !MSG_ERR_EXIT! !PY_ERR!)
pause
exit /b

:cleanup
exit /b