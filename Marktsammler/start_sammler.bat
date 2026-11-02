@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Marktsammler v1.2.7. Statusseite: http://127.0.0.1:8770/  Beenden: Fenster schliessen oder Strg+C.
start "" http://127.0.0.1:8770/
:schleife
python sammler.py
echo Sammler beendet (Ursache steht in sammler.log), Neustart in 30 Sekunden ...
timeout /t 30 >nul
goto schleife
