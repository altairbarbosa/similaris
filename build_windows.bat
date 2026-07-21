@echo off
setlocal
cd /d "%~dp0"

set "TOOLS_DIR=.build-tools"
set "FFMPEG_DIR=%TOOLS_DIR%\ffmpeg"
set "FFMPEG_ZIP=%TOOLS_DIR%\ffmpeg-release-essentials.zip"
set "FFMPEG_SHA=%TOOLS_DIR%\ffmpeg-release-essentials.zip.sha256"
set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

if not exist "%TOOLS_DIR%" mkdir "%TOOLS_DIR%"

if not exist "%FFMPEG_ZIP%" (
  echo Downloading the portable FFmpeg build...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%FFMPEG_ZIP%'"
  if errorlevel 1 goto :ffmpeg_error
)

echo Verifying FFmpeg integrity...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FFMPEG_URL%.sha256' -OutFile '%FFMPEG_SHA%'; $expected=((Get-Content '%FFMPEG_SHA%' -Raw).Trim() -split '\s+')[0].ToLower(); $actual=(Get-FileHash '%FFMPEG_ZIP%' -Algorithm SHA256).Hash.ToLower(); if ($expected -ne $actual) { Write-Error 'FFmpeg SHA-256 mismatch'; exit 1 }"
if errorlevel 1 goto :ffmpeg_error

echo Extracting build components...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%' -Force"
if errorlevel 1 goto :ffmpeg_error

set "FFMPEG_EXE="
for /r "%FFMPEG_DIR%" %%F in (ffmpeg.exe) do set "FFMPEG_EXE=%%F"
if not defined FFMPEG_EXE goto :ffmpeg_error

if not exist "%TOOLS_DIR%\GPL-3.0.txt" (
  echo Downloading the FFmpeg license...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.gnu.org/licenses/gpl-3.0.txt' -OutFile '%TOOLS_DIR%\GPL-3.0.txt'"
  if errorlevel 1 goto :ffmpeg_error
)

echo Creating virtual environment...
py -m venv .venv-windows
if errorlevel 1 goto :build_error

echo Installing dependencies...
call .venv-windows\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :build_error
call .venv-windows\Scripts\python.exe -m pip install -r requirements-windows.txt
if errorlevel 1 goto :build_error

echo Building Similaris.exe...
call .venv-windows\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed ^
  --name Similaris ^
  --icon "assets\similaris-icon.ico" ^
  --add-binary "%FFMPEG_EXE%;." ^
  --add-data "%TOOLS_DIR%\GPL-3.0.txt;." ^
  --add-data "THIRD_PARTY_NOTICES.txt;." ^
  --add-data "assets\similaris-icon.png;assets" ^
  app.py
if errorlevel 1 goto :build_error

echo.
echo Done: dist\Similaris.exe
echo This portable file includes Python, libraries, and FFmpeg.
echo Copy only the EXE to any 64-bit Windows 10/11 computer.
pause
exit /b 0

:ffmpeg_error
echo.
echo Could not download or locate FFmpeg.
echo Check your internet connection. If needed, delete the folder
echo .build-tools and try again.
pause
exit /b 1

:build_error
echo.
echo Could not build the executable. Check the messages above.
pause
exit /b 1
