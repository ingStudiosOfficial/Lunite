#!/usr/bin/env bash

echo "Lunite Builder Bash Script"
echo "--------------------------"
echo ""
echo "This will remove and remake the 'build' and 'lunitebin' folders."
echo "Make sure that pip3 is installed."
echo "If you do not wish to continue, press CTRL+C now."
echo "Press ENTER to continue..."
read -p ""

echo ""
echo "[ Removing old directories ]"
rm -rfv build
rm -rfv dist
rm -rfv lunitebin

echo ""
echo "[ Installing PyInstaller using pip3 ]"
pip3 install pyinstaller

echo ""
echo "[ Building Lunite executable ]"
pyinstaller --onefile lunite.py --icon icon.png --distpath lunitebin --name lunite

echo ""
echo "[ Cleaning up ]"
rm -fv lunite.spec
rm -rfv build

echo ""
echo "Done, binary created in 'lunitebin' directory."