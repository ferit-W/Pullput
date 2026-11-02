@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================================
echo  Morgenroutine v6.18 - START   (Port 8765)
echo ================================================================
echo.

rem ---------------------------------------------------------------------------
rem  v6.0.2: Das automatische Aufraeumen alter Server wurde ENTFERNT.
rem  Die alte Fassung hat laufende Prozesse gesucht und beendet. Genau dieses
rem  Muster stufen Virenscanner als verdaechtig ein (Verhaltenserkennung), weil
rem  Schadsoftware es benutzt, um Schutzprogramme auszuschalten - die Datei
rem  landete dadurch in Quarantaene.
rem  Notwendig war es ohnehin nicht: Der Server erkennt einen belegten Port
rem  selbst und erklaert im Klartext, was zu tun ist.
rem  Diese Datei tut jetzt nur noch, was auf dem Etikett steht: Python suchen
rem  und das Serverskript starten.
rem ---------------------------------------------------------------------------

rem  Python-Erkennung: Es wird nicht geprueft OB etwas da ist, sondern ob es
rem  TATSAECHLICH laeuft. Windows 11 legt einen Platzhalter "python.exe" an,
rem  der nur auf den Microsoft Store verweist - der faellt hier durch.
set "PYEXE="

py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=py -3"
  goto gefunden
)

python -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=python"
  goto gefunden
)

python3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "PYEXE=python3"
  goto gefunden
)

echo ================================================================
echo  PYTHON IST NICHT INSTALLIERT
echo ================================================================
echo.
echo  Falls gerade eine Meldung zum Microsoft Store kam: das ist nur ein
echo  Platzhalter von Windows, kein echtes Python.
echo.
echo  SO GEHT ES:
echo    1) https://www.python.org/downloads/  im Browser oeffnen
echo    2) den grossen gelben Knopf "Download Python" anklicken
echo    3) Installer starten - WICHTIG: unten den Haken bei
echo       "Add python.exe to PATH" SETZEN, vor dem Klick auf "Install Now"
echo    4) danach diese Datei erneut doppelklicken
echo.
echo  Zusatzpakete werden NICHT gebraucht. Mindestens Python 3.8.
echo ================================================================
echo.
pause
exit /b 1

:gefunden
echo Python gefunden:
%PYEXE% -c "import sys;print('   '+sys.version.split()[0]+'   ('+sys.executable+')')"
echo.

%PYEXE% -c "import sys;sys.exit(0 if sys.version_info>=(3,8) else 1)"
if errorlevel 1 (
  echo  PYTHON IST ZU ALT - gebraucht wird mindestens 3.8
  echo  Bitte von https://www.python.org/downloads/ aktualisieren.
  echo.
  pause
  exit /b 1
)

if not exist "START_Morgenroutine_v6.py" (
  echo ================================================================
  echo  START_Morgenroutine_v6.py FEHLT in diesem Ordner:
  echo  %CD%
  echo.
  echo  Pruefe die Dateinamen buchstabengenau. Alle Programmdateien
  echo  gehoeren in DIESEN Ordner.
  echo ================================================================
  echo.
  pause
  exit /b 1
)

echo Starte Server. Dieses Fenster bitte OFFEN lassen (Beenden mit STRG + C).
echo.
echo Hinweis: Meldet der Server "Port belegt", laeuft noch ein aelteres
echo Konsolenfenster. Dieses schliessen (oder PC neu starten) und erneut starten.
echo.
%PYEXE% START_Morgenroutine_v6.py

echo.
echo Server beendet.
pause
