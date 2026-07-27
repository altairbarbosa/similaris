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
  curl.exe --fail --location --retry 5 --retry-all-errors --output "%FFMPEG_ZIP%" "%FFMPEG_URL%"
  if errorlevel 1 goto :ffmpeg_error
)

echo Verifying FFmpeg integrity...
curl.exe --fail --location --retry 5 --retry-all-errors --output "%FFMPEG_SHA%" "%FFMPEG_URL%.sha256"
if errorlevel 1 goto :ffmpeg_error
python -c "import hashlib, os, sys; expected=open(os.environ['FFMPEG_SHA'], encoding='utf-8').read().strip().split()[0].lower(); actual=hashlib.sha256(open(os.environ['FFMPEG_ZIP'], 'rb').read()).hexdigest(); sys.exit(0 if expected == actual else 1)"
if errorlevel 1 goto :ffmpeg_error

echo Extracting build components...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%' -Force"
if errorlevel 1 goto :ffmpeg_error

set "FFMPEG_EXE="
set "FFMPEG_LICENSE="
for /r "%FFMPEG_DIR%" %%F in (ffmpeg.exe) do if exist "%%F" set "FFMPEG_EXE=%%F"
for /r "%FFMPEG_DIR%" %%F in (LICENSE) do if exist "%%F" set "FFMPEG_LICENSE=%%F"
if not defined FFMPEG_EXE goto :ffmpeg_error
if not defined FFMPEG_LICENSE goto :ffmpeg_error

copy /Y "%FFMPEG_LICENSE%" "%TOOLS_DIR%\GPL-3.0.txt" >nul
if errorlevel 1 goto :ffmpeg_error

if not exist "%REALESRGAN_ZIP%" (
  echo Downloading the portable Real-ESRGAN engine...
  curl.exe --fail --location --retry 5 --retry-all-errors --output "%REALESRGAN_ZIP%" "%REALESRGAN_URL%"
  if errorlevel 1 goto :enhancement_error
)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%REALESRGAN_ZIP%' -DestinationPath '%REALESRGAN_DIR%' -Force"
if errorlevel 1 goto :enhancement_error
python -c "import hashlib, os, sys; actual=hashlib.sha256(open(os.environ['REALESRGAN_ZIP'], 'rb').read()).hexdigest(); expected=os.environ['REALESRGAN_SHA256'].lower(); sys.exit(0 if actual == expected else 1)"
if errorlevel 1 goto :enhancement_error
set "REALESRGAN_EXE="
set "REALESRGAN_MODELS="
set "VCOMP_DLL="
for /r "%REALESRGAN_DIR%" %%F in (realesrgan-ncnn-vulkan.exe) do if exist "%%F" set "REALESRGAN_EXE=%%F"
for /d /r "%REALESRGAN_DIR%" %%D in (models) do if exist "%%D\realesrgan-x4plus.bin" set "REALESRGAN_MODELS=%%D"
for /r "%REALESRGAN_DIR%" %%F in (vcomp140.dll) do if exist "%%F" set "VCOMP_DLL=%%F"
if not defined REALESRGAN_EXE goto :enhancement_error
if not defined REALESRGAN_MODELS goto :enhancement_error
if not defined VCOMP_DLL goto :enhancement_error

curl.exe --fail --location --retry 5 --retry-all-errors --output "%TOOLS_DIR%\REALESRGAN-LICENSE.txt" "%REALESRGAN_LICENSE_URL%"
if errorlevel 1 goto :enhancement_error
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "if (-not (Test-Path '%TOOLS_DIR%\REALESRGAN-LICENSE.txt')) { exit 1 }"
if errorlevel 1 goto :enhancement_error
python -c "import hashlib, os, sys; path=os.path.join(os.environ['TOOLS_DIR'], 'REALESRGAN-LICENSE.txt'); actual=hashlib.sha256(open(path, 'rb').read()).hexdigest(); sys.exit(0 if actual == '5abb941454de437b0e90d78dcb72e3688f74e14bcd4e24393273cb5cd0e9c937' else 1)"
if errorlevel 1 goto :enhancement_error

echo Creating virtual environment...
python -m venv .venv-windows
if errorlevel 1 goto :build_error

echo Installing Python core dependencies...
call .venv-windows\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :build_error
call .venv-windows\Scripts\python.exe -m pip install -r requirements-windows.txt
if errorlevel 1 goto :build_error

echo Building SimilarisCore.exe...
call .venv-windows\Scripts\pyinstaller.exe --noconfirm --clean --onedir --console ^
  --name SimilarisCore ^
  --distpath "dist\python-core" ^
  --add-binary "%FFMPEG_EXE%;." ^
  --add-binary "%REALESRGAN_EXE%;." ^
  --add-binary "%VCOMP_DLL%;." ^
  --add-data "%REALESRGAN_MODELS%;models" ^
  --add-data "%TOOLS_DIR%\GPL-3.0.txt;." ^
  --add-data "%TOOLS_DIR%\REALESRGAN-LICENSE.txt;." ^
  --add-data "THIRD_PARTY_NOTICES.txt;." ^
  --add-data "LICENSE;." ^
  photo_organizer.py
if errorlevel 1 goto :build_error

echo.
echo Done: dist\python-core\SimilarisCore\SimilarisCore.exe
echo The WinUI project copies this folder into Python\ during build.
if defined CI exit /b 0
pause
exit /b 0

:ffmpeg_error
echo.
echo Could not download or locate FFmpeg.
if defined CI exit /b 1
pause
exit /b 1

:build_error
echo.
echo Could not build the Python core. Check the messages above.
if defined CI exit /b 1
pause
exit /b 1

:enhancement_error
echo.
echo Could not download, verify, or locate Real-ESRGAN.
if defined CI exit /b 1
pause
exit /b 1
