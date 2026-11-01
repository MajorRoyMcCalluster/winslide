@echo off
setlocal EnableExtensions
rem ======================================================================
rem  WinSlide installer / updater
rem  First run installs; every later run updates in place. Settings are
rem  kept (they live in the registry). Only this script goes online - to
rem  pull the latest code from GitHub. The app itself has no network code.
rem  Add  /force  to rebuild even when already up to date.
rem ======================================================================
set "APPNAME=WinSlide"
set "TITLE=WinSlide"
set "SRC=winslide.py"
set "REPO=https://github.com/MajorRoyMcCalluster/winslide.git"
set "PKGS=PySide6-Essentials pyinstaller"
title %TITLE% updater
set "HERE=%~dp0"
set "WORK=%LOCALAPPDATA%\%APPNAME%-build"
set "INSTALL=%LOCALAPPDATA%\Programs\%APPNAME%"
set "FORCE="
if /i "%~1"=="/force" set "FORCE=1"
if not exist "%WORK%" mkdir "%WORK%"

echo.
echo  %TITLE% // install + update
echo  ------------------------------------------------
echo.

rem ---------- 1. latest source ----------
set "SRCDIR="
where git >nul 2>nul
if errorlevel 1 goto :nogit
if exist "%WORK%\src\.git" goto :fetch
echo  Downloading %TITLE% from GitHub...
echo  First time only: a GitHub sign-in window may open.
git clone --quiet "%REPO%" "%WORK%\src" 2>nul
if errorlevel 1 goto :gitfail
goto :checksrc
:fetch
echo  Checking GitHub for updates...
git -C "%WORK%\src" fetch --quiet origin
if errorlevel 1 goto :gitfail
rem The local copy is only a cache, so always match GitHub exactly.
git -C "%WORK%\src" checkout --quiet -B main origin/main 2>nul
:checksrc
if not exist "%WORK%\src\%SRC%" goto :emptyrepo
set "SRCDIR=%WORK%\src\"
goto :havesrc

:emptyrepo
echo  The GitHub repo has no code yet - building from the files next to this script.
goto :localsrc

:nogit
echo  Git isn't installed, so updates can't be fetched from GitHub.
echo  Install it once with:  winget install Git.Git   then run this again.
echo  For now, building from the files next to this script.
goto :localsrc
:gitfail
echo  Couldn't reach GitHub - building from the files next to this script.
:localsrc
if not exist "%HERE%%SRC%" goto :nosource
set "SRCDIR=%HERE%"
:havesrc

rem ---------- 2. versions ----------
set "NEWVER=unknown"
for /f "tokens=2 delims==" %%v in ('findstr /b /c:"__version__" "%SRCDIR%%SRC%"') do set "NEWVER=%%v"
set "NEWVER=%NEWVER: =%"
set NEWVER=%NEWVER:"=%
set "OLDVER=none"
if exist "%INSTALL%\version.txt" set /p OLDVER=<"%INSTALL%\version.txt"
echo  Installed: %OLDVER%    Latest: %NEWVER%
echo.
if defined FORCE goto :build
if not exist "%INSTALL%\%APPNAME%.exe" goto :build
if /i not "%OLDVER%"=="%NEWVER%" goto :build
echo  %TITLE% is already up to date.
call :shortcuts
call :launch
goto :done

rem ---------- 3. build ----------
:build
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :nopython
%PY% -c "import sys" >nul 2>nul || goto :nopython

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
"%VPY%" -m pip install --quiet --disable-pip-version-check --upgrade %USERFLAG% %PKGS% || goto :fail

echo  Building %TITLE% %NEWVER%...
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --windowed --log-level WARN ^
    --name %APPNAME% ^
    --workpath "%WORK%\build" --distpath "%WORK%\dist" --specpath "%WORK%" ^
    --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtQml ^
    --exclude-module PySide6.QtQuick --exclude-module PySide6.QtSql ^
    --exclude-module PySide6.QtTest --exclude-module tkinter ^
    "%SRCDIR%%SRC%" || goto :fail
if not exist "%WORK%\dist\%APPNAME%.exe" goto :fail

rem ---------- 4. swap in place ----------
tasklist /fi "imagename eq %APPNAME%.exe" 2>nul | find /i "%APPNAME%.exe" >nul
if errorlevel 1 goto :notrunning
echo  Closing the running %TITLE%...
taskkill /im %APPNAME%.exe >nul 2>nul
timeout /t 2 /nobreak >nul
taskkill /im %APPNAME%.exe /f >nul 2>nul
timeout /t 1 /nobreak >nul
:notrunning
if not exist "%INSTALL%" mkdir "%INSTALL%"
copy /y "%WORK%\dist\%APPNAME%.exe" "%INSTALL%\%APPNAME%.exe" >nul || goto :fail
>"%INSTALL%\version.txt" echo %NEWVER%
rem Stage the newest copy of this updater; it replaces itself on the last line.
if exist "%SRCDIR%update.bat" copy /y "%SRCDIR%update.bat" "%INSTALL%\update.new.bat" >nul
rmdir /s /q "%WORK%\build" 2>nul
rmdir /s /q "%WORK%\dist" 2>nul
call :shortcuts
echo.
if "%OLDVER%"=="none" (echo  Installed %TITLE% %NEWVER%.) else (echo  Updated %TITLE% %OLDVER% to %NEWVER%.)
echo  Location: %INSTALL%
echo  Start Menu: "%TITLE%" and "Update %TITLE%"
call :launch
goto :done

rem ---------- helpers ----------
:shortcuts
set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%INSTALL%\update.bat" if not exist "%INSTALL%\update.new.bat" copy /y "%~f0" "%INSTALL%\update.new.bat" >nul 2>nul
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=New-Object -ComObject WScript.Shell; $a=$s.CreateShortcut('%SM%\%TITLE%.lnk'); $a.TargetPath='%INSTALL%\%APPNAME%.exe'; $a.WorkingDirectory='%INSTALL%'; $a.Save(); $b=$s.CreateShortcut('%SM%\Update %TITLE%.lnk'); $b.TargetPath='%INSTALL%\update.bat'; $b.WorkingDirectory='%INSTALL%'; $b.IconLocation='%INSTALL%\%APPNAME%.exe,0'; $b.Save()" >nul 2>nul
exit /b 0

:launch
tasklist /fi "imagename eq %APPNAME%.exe" 2>nul | find /i "%APPNAME%.exe" >nul
if errorlevel 1 start "" "%INSTALL%\%APPNAME%.exe"
exit /b 0

:nopython
echo  Python isn't installed - it's needed to build %TITLE%.
echo  Install it from https://www.python.org/downloads/  - tick "Add python.exe to PATH"
echo  or run:  winget install Python.Python.3.12
echo  then run this again.
goto :done

:nosource
echo  Couldn't find %SRC% - put this script next to it, or install Git so it can download it.
goto :done

:fail
echo.
echo  Something went wrong - scroll up for the error.
if exist "%WORK%\venv.log" type "%WORK%\venv.log"
goto :done

:done
echo.
pause
if exist "%INSTALL%\update.new.bat" (move /y "%INSTALL%\update.new.bat" "%INSTALL%\update.bat" >nul & exit /b 0)
