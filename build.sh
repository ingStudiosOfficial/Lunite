#!/usr/bin/env bash

# Lunite Builder Bash Script
# For Linux or MacOS
# v2

echo "Lunite Builder Bash Script"
echo "--------------------------"

if [ -f "./venv/bin/python" ]; then
    PY_BIN="./venv/bin/python"
    echo "[!] Virtual Environment Detected: ./venv"
elif [ -f "./.venv/bin/python" ]; then
    PY_BIN="./.venv/bin/python"
    echo "[!] Virtual Environment Detected: ./.venv"
elif [ -f "./env/bin/python" ]; then
    PY_BIN="./env/bin/python"
    echo "[!] Virtual Environment Detected: ./env"
else
    if command -v python3 &>/dev/null; then
        PY_BIN="python3"
    else
        PY_BIN="python"
    fi
    echo "[i]  No Venv found. Using system python: $PY_BIN"
fi

echo ""
echo "This will remove and remake the 'build' and 'lunitebin' folders."
echo "If you do not wish to continue, press CTRL+C now."
echo "Press ENTER to continue..."
read -p ""

if [ ! -f "lunite.py" ]; then
    echo "[x] Error: 'lunite.py' not found in current directory."
    exit 1
fi

echo ""
echo "[i] [ Removing old directories ]"
rm -rfv build dist lunitebin

echo ""
echo "[i] [ Installing Dependencies ]"
"$PY_BIN" -m pip install --upgrade pip
"$PY_BIN" -m pip install pyinstaller colorama

echo ""
echo "[i] [ Building Lunite Executable ]"
"$PY_BIN" -m PyInstaller --onefile lunite.py --icon icon.png --distpath lunitebin --name lunite --clean

echo ""
echo "[i] [ Cleaning up build artifacts ]"
rm -fv lunite.spec
rm -rfv build

echo ""
if [ -f "lunitebin/lunite" ]; then
    echo "[i] Success! Binary created in 'lunitebin/lunite'"
else
    echo "[x] Build failed. Please check the logs above."
fi