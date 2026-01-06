@echo off
title Lunite Builder Batch Script

echo Lunite Builder Batch Script
echo --------------------------
echo.
echo This will remove and remake the 'build' and 'lunitebin' folders.
echo Make sure that pip is installed.
echo If you do not wish to continue, press CTRL+C now.
echo Press any key to continue...
pause >nul

echo.
echo [ Removing old directories ]
if exist build rd /s /q build
if exist dist rd /s /q dist
if exist lunitebin rd /s /q lunitebin

echo.
echo [ Installing PyInstaller using pip ]
pip install pyinstaller

echo.
echo [ Building Lunite executable ]
pyinstaller --onefile lunite.py --icon icon.png --distpath lunitebin --name lunite

echo.
echo [ Cleaning up ]
if exist lunite.spec del /q lunite.spec
if exist build rd /s /q build

echo.
echo Done, binary created in 'lunitebin' directory.