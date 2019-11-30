#!/bin/bash
#TODO:
rm -rf dist
../../ENV_client/bin/pyinstaller startup.py --hidden-import='PIL._tkinter_finder'
cp -R fonts dist/startup/
cp default.json dist/startup/config.json
cp readme.txt dist/startup/
cp default.png dist/startup/
cp xbindkeysrc dist/startup/
cp ztranslate.sh dist/startup/
mkdir dist/startup/tessdata
mkdir dist/startup/packages
rm -rf ../ztrans_client_linux
mkdir ../ztrans_client_linux
cp -R dist/startup/* ../ztrans_client_linux/
rm -rf dist
cd ..
rm ./ztrans_client_linux.tar
tar -czvf ztrans_client_linux.tar ./ztrans_client_linux
rm -rf ztrans_client_linux
cd ztrans_client
