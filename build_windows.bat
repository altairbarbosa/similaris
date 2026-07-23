@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 (
  echo Could not access the project folder: %~dp0
  pause
  exit /b 1
)

set "TOOLS_DIR=.build-tools"
set "FFMPEG_DIR=%TOOLS_DIR%\ffmpeg"
set "FFMPEG_ZIP=%TOOLS_DIR%\ffmpeg-release-essentials.zip"
set "FFMPEG_SHA=%TOOLS_DIR%\ffmpeg-release-essentials.zip.sha256"
set "FFMPEG_URL=https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
set "REALESRGAN_ZIP=%TOOLS_DIR%\realesrgan-ncnn-vulkan-20211212-windows.zip"
set "REALESRGAN_DIR=%TOOLS_DIR%\realesrgan-full"
set "REALESRGAN_URL=https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.3.0/realesrgan-ncnn-vulkan-20211212-windows.zip"
set "REALESRGAN_SHA256=caf96d62999e741194a28b514eb6202c09a39edcd9ced730e3f784c424cc0653"
set "REALESRGAN_LICENSE_URL=https://raw.githubusercontent.com/xinntao/Real-ESRGAN-ncnn-vulkan/37026f49824c5cf84062e7c6a5dd71445dcf610f/LICENSE"

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
for /r "%FFMPEG_DIR%" %%F in (ffmpeg.exe) do if exist "%%F" set "FFMPEG_EXE=%%F"
if not defined FFMPEG_EXE goto :ffmpeg_error

if not exist "%REALESRGAN_ZIP%" (
  echo Downloading the portable Real-ESRGAN engine...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%REALESRGAN_URL%' -OutFile '%REALESRGAN_ZIP%'"
  if errorlevel 1 goto :enhancement_error
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$actual=(Get-FileHash '%REALESRGAN_ZIP%' -Algorithm SHA256).Hash.ToLower(); if ($actual -ne '%REALESRGAN_SHA256%') { Write-Error 'Real-ESRGAN SHA-256 mismatch'; exit 1 }; Expand-Archive -Path '%REALESRGAN_ZIP%' -DestinationPath '%REALESRGAN_DIR%' -Force"
if errorlevel 1 goto :enhancement_error
set "REALESRGAN_EXE="
set "REALESRGAN_LICENSE="
set "REALESRGAN_MODELS="
set "VCOMP_DLL="
for /r "%REALESRGAN_DIR%" %%F in (realesrgan-ncnn-vulkan.exe) do if exist "%%F" set "REALESRGAN_EXE=%%F"
for /d /r "%REALESRGAN_DIR%" %%D in (models) do if exist "%%D\realesrgan-x4plus.bin" set "REALESRGAN_MODELS=%%D"
for /r "%REALESRGAN_DIR%" %%F in (vcomp140.dll) do if exist "%%F" set "VCOMP_DLL=%%F"
if not defined REALESRGAN_EXE goto :enhancement_error
if not defined REALESRGAN_MODELS goto :enhancement_error
if not defined VCOMP_DLL goto :enhancement_error
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%REALESRGAN_LICENSE_URL%' -OutFile '%TOOLS_DIR%\REALESRGAN-LICENSE.txt'; if ((Get-FileHash '%TOOLS_DIR%\REALESRGAN-LICENSE.txt' -Algorithm SHA256).Hash.ToLower() -ne '5abb941454de437b0e90d78dcb72e3688f74e14bcd4e24393273cb5cd0e9c937') { exit 1 }"
if errorlevel 1 goto :enhancement_error

if not exist "%TOOLS_DIR%\GPL-3.0.txt" (
  echo Downloading the FFmpeg license...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.gnu.org/licenses/gpl-3.0.txt' -OutFile '%TOOLS_DIR%\GPL-3.0.txt'"
  if errorlevel 1 goto :ffmpeg_error
)

echo Creating virtual environment...
python -m venv .venv-windows
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
  --add-binary "%REALESRGAN_EXE%;." ^
  --add-binary "%VCOMP_DLL%;." ^
  --add-data "%REALESRGAN_MODELS%;models" ^
  --add-data "%TOOLS_DIR%\GPL-3.0.txt;." ^
  --add-data "%TOOLS_DIR%\REALESRGAN-LICENSE.txt;." ^
  --add-data "THIRD_PARTY_NOTICES.txt;." ^
  --add-data "LICENSE;." ^
  --add-data "assets;assets" ^
  app.py
if errorlevel 1 goto :build_error

echo.
echo Done: dist\Similaris.exe
echo This portable file includes Python, libraries, and FFmpeg.
echo Copy only the EXE to any 64-bit Windows 10/11 computer.
if defined CI exit /b 0
pause
exit /b 0

:ffmpeg_error
echo.
echo Could not download or locate FFmpeg.
echo Check your internet connection. If needed, delete the folder
echo .build-tools and try again.
if defined CI exit /b 1
pause
exit /b 1

:build_error
echo.
echo Could not build the executable. Check the messages above.
if defined CI exit /b 1
pause
exit /b 1

:enhancement_error
echo.
echo Could not download, verify, or locate Real-ESRGAN.
if defined CI exit /b 1
pause
exit /b 1
