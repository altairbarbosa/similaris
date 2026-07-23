#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

TOOLS_DIR=".build-tools-linux"
VENV_DIR=".venv-linux"
FFMPEG_ARCHIVE="$TOOLS_DIR/ffmpeg-release-static.tar.xz"
FFMPEG_MD5="$FFMPEG_ARCHIVE.md5"
REALESRGAN_ARCHIVE="$TOOLS_DIR/realesrgan-ncnn-vulkan-20211212-ubuntu.zip"
REALESRGAN_URL="https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.3.0/realesrgan-ncnn-vulkan-20211212-ubuntu.zip"
REALESRGAN_SHA256="9e4b78aa0d7796bbdab06ac50f7a424329920a4ea039655465aeed4cbff4a945"
REALESRGAN_LICENSE_URL="https://raw.githubusercontent.com/xinntao/Real-ESRGAN-ncnn-vulkan/37026f49824c5cf84062e7c6a5dd71445dcf610f/LICENSE"
REALESRGAN_LICENSE_SHA256="5abb941454de437b0e90d78dcb72e3688f74e14bcd4e24393273cb5cd0e9c937"

case "$(uname -m)" in
  x86_64) FFMPEG_PLATFORM="amd64" ;;
  *)
    echo "Unsupported architecture: $(uname -m). The bundled Real-ESRGAN engine requires x86_64." >&2
    exit 1
    ;;
esac

FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${FFMPEG_PLATFORM}-static.tar.xz"

for command_name in python3 curl tar md5sum sha256sum dpkg-deb; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "Required command not found: $command_name" >&2
    exit 1
  fi
done

if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
  echo "Tkinter is not installed. On Ubuntu/WSL, run:" >&2
  echo "  sudo apt update && sudo apt install -y python3-tk python3-venv" >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1 || ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
  echo "Python virtual environment support is not installed. Run:" >&2
  echo "  sudo apt update && sudo apt install -y python3-venv" >&2
  exit 1
fi

mkdir -p "$TOOLS_DIR"

if [[ ! -f "$FFMPEG_ARCHIVE" ]]; then
  echo "Downloading static FFmpeg for Linux..."
  curl --fail --location --progress-bar "$FFMPEG_URL" --output "$FFMPEG_ARCHIVE"
fi

if [[ ! -f "$REALESRGAN_ARCHIVE" ]]; then
  echo "Downloading the portable Real-ESRGAN engine..."
  curl --fail --location --progress-bar "$REALESRGAN_URL" --output "$REALESRGAN_ARCHIVE"
fi
echo "$REALESRGAN_SHA256  $REALESRGAN_ARCHIVE" | sha256sum --check --status

echo "Verifying FFmpeg integrity..."
curl --fail --location --silent --show-error "$FFMPEG_URL.md5" --output "$FFMPEG_MD5"
(
  cd "$TOOLS_DIR"
  sed "s#  .*#  $(basename "$FFMPEG_ARCHIVE")#" "$(basename "$FFMPEG_MD5")" | md5sum --check --status
)

echo "Extracting build components..."
tar -xJf "$FFMPEG_ARCHIVE" -C "$TOOLS_DIR"
python3 -m zipfile -e "$REALESRGAN_ARCHIVE" "$TOOLS_DIR/realesrgan-full"
FFMPEG_BIN="$(find "$TOOLS_DIR" -mindepth 2 -maxdepth 2 -type f -name ffmpeg -print -quit)"
GPL_FILE="$(find "$TOOLS_DIR" -mindepth 2 -maxdepth 2 -type f -name GPLv3.txt -print -quit)"
REALESRGAN_BIN="$(find "$TOOLS_DIR/realesrgan-full" -type f -name realesrgan-ncnn-vulkan -print -quit)"
REALESRGAN_MODELS="$(find "$TOOLS_DIR/realesrgan-full" -type d -name models -print -quit)"
if [[ -z "$FFMPEG_BIN" || -z "$GPL_FILE" ]]; then
  echo "Could not find the extracted FFmpeg." >&2
  exit 1
fi
if [[ -z "$REALESRGAN_BIN" || -z "$REALESRGAN_MODELS" ]]; then
  echo "Could not find the extracted Real-ESRGAN engine." >&2
  exit 1
fi
chmod +x "$REALESRGAN_BIN"
curl --fail --location --silent --show-error "$REALESRGAN_LICENSE_URL" --output "$TOOLS_DIR/REALESRGAN-LICENSE.txt"
echo "$REALESRGAN_LICENSE_SHA256  $TOOLS_DIR/REALESRGAN-LICENSE.txt" | sha256sum --check --status

LIBGOMP_BIN="$(find "$TOOLS_DIR/libgomp" -name 'libgomp.so.1' -print -quit 2>/dev/null || true)"
if [[ -z "$LIBGOMP_BIN" ]]; then
  echo "Downloading the Real-ESRGAN OpenMP runtime..."
  LIBGOMP_PACKAGE="$TOOLS_DIR/libgomp1_14.2.0-4ubuntu2_24.04.1_amd64.deb"
  LIBGOMP_URL="https://security.ubuntu.com/ubuntu/pool/main/g/gcc-14/libgomp1_14.2.0-4ubuntu2~24.04.1_amd64.deb"
  LIBGOMP_SHA256="e8a95ec58125b4933597f30ff56c2ae10edf90f287262e366d4b6edea3019144"
  curl --fail --location --progress-bar "$LIBGOMP_URL" --output "$LIBGOMP_PACKAGE"
  echo "$LIBGOMP_SHA256  $LIBGOMP_PACKAGE" | sha256sum --check --status
  dpkg-deb --extract "$LIBGOMP_PACKAGE" "$TOOLS_DIR/libgomp"
  LIBGOMP_BIN="$(find "$TOOLS_DIR/libgomp" -name 'libgomp.so.1' -print -quit)"
fi
if [[ -z "$LIBGOMP_BIN" ]]; then
  echo "Could not locate libgomp.so.1." >&2
  exit 1
fi

echo "Creating isolated environment..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r requirements-linux.txt

echo "Building dist/Similaris..."
"$VENV_DIR/bin/pyinstaller" --noconfirm --clean --onefile --windowed \
  --name Similaris \
  --icon "assets/similaris-icon.png" \
  --add-binary "$FFMPEG_BIN:." \
  --add-binary "$REALESRGAN_BIN:." \
  --add-binary "$LIBGOMP_BIN:." \
  --add-data "$REALESRGAN_MODELS:models" \
  --add-data "$GPL_FILE:." \
  --add-data "$TOOLS_DIR/REALESRGAN-LICENSE.txt:." \
  --add-data "THIRD_PARTY_NOTICES.txt:." \
  --add-data "LICENSE:." \
  --add-data "assets:assets" \
  app.py

chmod +x dist/Similaris
echo
echo "Done: dist/Similaris"
echo "Run with: ./dist/Similaris"
