@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Marktsammler v1.2.7. Statusseite: http://127.0.0.1:8770/  Beenden: Fenster schliessen oder Strg+C.
set "PYEXE=python"
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PYEXE=py -3"
start "" http://127.0.0.1:8770/
:schleife
%PYEXE% sammler.py
echo Sammler beendet (Ursache steht in sammler.log), Neustart in 30 Sekunden ...
timeout /t 30 >nul
goto schleife
