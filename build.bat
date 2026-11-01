@echo off
setlocal
set "APPNAME=WinSlide"
set "SRC=winslide.py"
title Build WinSlide
cd /d "%~dp0"
set "WORK=%LOCALAPPDATA%\%APPNAME%-build"

echo.
echo  Building WinSlide...
echo.

rem --- find Python ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :nopython
%PY% -c "import sys" >nul 2>nul || goto :nopython

echo  Using Python:
%PY% -c "import sys; print('   ', sys.executable, sys.version.split()[0])"
%PY% -c "import sys; sys.exit(0 if 'WindowsApps' in sys.executable else 1)" && echo    Microsoft Store Python detected - fine, using the fallback setup if needed.
echo.

rem --- build outside Documents, where Windows always lets Python write ---
if not exist "%WORK%" mkdir "%WORK%"
set "VPY=%WORK%\env\Scripts\python.exe"
set "USERFLAG="
if exist "%VPY%" goto :haveenv
echo  Creating build environment...
%PY% -m venv "%WORK%\env" >"%WORK%\venv.log" 2>&1
if exist "%VPY%" goto :haveenv
echo  Couldn't create a private environment, installing build tools for your user instead.
rmdir /s /q "%WORK%\env" 2>nul
for /f "delims=" %%i in ('%PY% -c "import sys; print(sys.executable)"') do set "VPY=%%i"
set "USERFLAG=--user"
:haveenv

echo  Installing build tools (first run takes a minute or two)...
"%VPY%" -m pip install --quiet --disable-pip-version-check %USERFLAG% PySide6-Essentials pyinstaller || goto :fail

echo  Packaging...
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name %APPNAME% ^
    --workpath "%WORK%\build" --distpath "%WORK%\dist" --specpath "%WORK%" ^
    --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtQml ^
    --exclude-module PySide6.QtQuick --exclude-module PySide6.QtSql ^
    --exclude-module PySide6.QtTest --exclude-module tkinter ^
    "%~dp0%SRC%" || goto :fail

if not exist "%WORK%\dist\%APPNAME%.exe" goto :fail
copy /y "%WORK%\dist\%APPNAME%.exe" "%~dp0%APPNAME%.exe" >nul
if errorlevel 1 goto :copyfail
rmdir /s /q "%WORK%\build" 2>nul
rmdir /s /q "%WORK%\dist" 2>nul
if exist "%~dp0.buildenv" rmdir /s /q "%~dp0.buildenv" 2>nul

echo.
echo  Done! %APPNAME%.exe is in this folder.
echo  Move it somewhere permanent before ticking Start with Windows, then double-click it to run.
echo.
pause
exit /b 0

:copyfail
echo.
echo  Built OK, but Windows wouldn't let it be copied here. Your .exe is at:
echo    %WORK%\dist\%APPNAME%.exe
echo  Copy it from there to wherever you want to keep it.
echo.
pause
exit /b 0

:nopython
echo  Python isn't installed.
echo  Install it from https://www.python.org/downloads/  - tick "Add python.exe to PATH"
echo  or run:  winget install Python.Python.3.12
echo  then double-click build.bat again.
pause
exit /b 1

:fail
echo.
echo  Something went wrong - scroll up for the error.
if exist "%WORK%\venv.log" type "%WORK%\venv.log"
pause
exit /b 1
