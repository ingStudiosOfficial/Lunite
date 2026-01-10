@echo off
setlocal
title Lunite Builder Batch Script

:: Lunite Builder Batch Script
:: For Windows
:: v2

echo Lunite Builder Batch Script
echo -----------------------------

if exist "venv\Scripts\python.exe" (
    set "PY_BIN=venv\Scripts\python.exe"
    echo [!] Virtual Environment Detected: venv
) else if exist ".venv\Scripts\python.exe" (
    set "PY_BIN=.venv\Scripts\python.exe"
    echo [!] Virtual Environment Detected: .venv
) else if exist "env\Scripts\python.exe" (
    set "PY_BIN=env\Scripts\python.exe"
    echo [!] Virtual Environment Detected: env
) else (
    set "PY_BIN=python"
    echo [i]  No Venv found. Using system python.
)

echo.
echo This will remove and remake the 'build' and 'lunitebin' folders.
echo If you do not wish to continue, press CTRL+C now.
echo Press any key to continue...
pause >nul

:: 2. Pre-flight Checks
if not exist "lunite.py" (
    echo [x] Error: 'lunite.py' not found in current directory.
    goto :End
)

echo.
echo [i] [ Removing old directories ]
if exist build rd /s /q build
if exist dist rd /s /q dist
if exist lunitebin rd /s /q lunitebin

echo.
echo [i] [ Installing Dependencies ]
"%PY_BIN%" -m pip install --upgrade pip
"%PY_BIN%" -m pip install pyinstaller colorama

echo.
echo [i] [ Building Lunite Executable ]
"%PY_BIN%" -m PyInstaller --onefile lunite.py --icon icon.png --distpath lunitebin --name lunite --clean

echo.
echo [i] [ Cleaning up build artifacts ]
if exist lunite.spec del /q lunite.spec
if exist build rd /s /q build

echo.
if exist "lunitebin\lunite.exe" (
    echo [i] Success! Binary created in 'lunitebin\lunite.exe'
) else (
    echo [x] Build failed. Please check the logs above.
)

:End
pause
endlocal