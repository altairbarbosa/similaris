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
  echo Baixando FFmpeg portable recomendado pelo projeto FFmpeg...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FFMPEG_URL%' -OutFile '%FFMPEG_ZIP%'"
  if errorlevel 1 goto :erro_ffmpeg
)

echo Validando a integridade do FFmpeg...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri '%FFMPEG_URL%.sha256' -OutFile '%FFMPEG_SHA%'; $esperado=((Get-Content '%FFMPEG_SHA%' -Raw).Trim() -split '\s+')[0].ToLower(); $obtido=(Get-FileHash '%FFMPEG_ZIP%' -Algorithm SHA256).Hash.ToLower(); if ($esperado -ne $obtido) { Write-Error 'SHA-256 do FFmpeg nao confere'; exit 1 }"
if errorlevel 1 goto :erro_ffmpeg

echo Extraindo os componentes para a construcao...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Expand-Archive -Path '%FFMPEG_ZIP%' -DestinationPath '%FFMPEG_DIR%' -Force"
if errorlevel 1 goto :erro_ffmpeg

set "FFMPEG_EXE="
for /r "%FFMPEG_DIR%" %%F in (ffmpeg.exe) do set "FFMPEG_EXE=%%F"
if not defined FFMPEG_EXE goto :erro_ffmpeg

if not exist "%TOOLS_DIR%\GPL-3.0.txt" (
  echo Baixando a licenca do FFmpeg...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Uri 'https://www.gnu.org/licenses/gpl-3.0.txt' -OutFile '%TOOLS_DIR%\GPL-3.0.txt'"
  if errorlevel 1 goto :erro_ffmpeg
)

echo Criando ambiente virtual...
py -m venv .venv-windows
if errorlevel 1 goto :erro

echo Instalando dependencias...
call .venv-windows\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :erro
call .venv-windows\Scripts\python.exe -m pip install -r requirements-windows.txt
if errorlevel 1 goto :erro

echo Gerando OrganizadorFotos.exe...
call .venv-windows\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed ^
  --name OrganizadorFotos ^
  --add-binary "%FFMPEG_EXE%;." ^
  --add-data "%TOOLS_DIR%\GPL-3.0.txt;." ^
  --add-data "AVISOS_DE_TERCEIROS.txt;." ^
  interface_windows.py
if errorlevel 1 goto :erro

echo.
echo Pronto: dist\OrganizadorFotos.exe
echo Este arquivo e portable e ja inclui Python, bibliotecas e FFmpeg.
echo Copie somente o EXE para qualquer computador Windows 10/11 de 64 bits.
pause
exit /b 0

:erro_ffmpeg
echo.
echo Nao foi possivel baixar ou localizar o FFmpeg.
echo Verifique a conexao com a internet. Se necessario, apague a pasta
echo .build-tools e tente novamente.
pause
exit /b 1

:erro
echo.
echo Nao foi possivel criar o executavel. Verifique as mensagens acima.
pause
exit /b 1
