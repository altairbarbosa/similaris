#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

TOOLS_DIR=".build-tools-linux"
VENV_DIR=".venv-linux"
FFMPEG_ARCHIVE="$TOOLS_DIR/ffmpeg-release-static.tar.xz"
FFMPEG_MD5="$FFMPEG_ARCHIVE.md5"

case "$(uname -m)" in
  x86_64) FFMPEG_PLATFORM="amd64" ;;
  aarch64|arm64) FFMPEG_PLATFORM="arm64" ;;
  *)
    echo "Unsupported architecture: $(uname -m)" >&2
    exit 1
    ;;
esac

FFMPEG_URL="https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-${FFMPEG_PLATFORM}-static.tar.xz"

for command_name in python3 curl tar md5sum; do
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

echo "Verifying FFmpeg integrity..."
curl --fail --location --silent --show-error "$FFMPEG_URL.md5" --output "$FFMPEG_MD5"
(
  cd "$TOOLS_DIR"
  sed "s#  .*#  $(basename "$FFMPEG_ARCHIVE")#" "$(basename "$FFMPEG_MD5")" | md5sum --check --status
)

echo "Extracting build components..."
tar -xJf "$FFMPEG_ARCHIVE" -C "$TOOLS_DIR"
FFMPEG_BIN="$(find "$TOOLS_DIR" -mindepth 2 -maxdepth 2 -type f -name ffmpeg -print -quit)"
GPL_FILE="$(find "$TOOLS_DIR" -mindepth 2 -maxdepth 2 -type f -name GPLv3.txt -print -quit)"
if [[ -z "$FFMPEG_BIN" || -z "$GPL_FILE" ]]; then
  echo "Could not find the extracted FFmpeg." >&2
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
  --add-data "$GPL_FILE:." \
  --add-data "THIRD_PARTY_NOTICES.txt:." \
  --add-data "LICENSE:." \
  --add-data "assets/similaris-icon.png:assets" \
  app.py

chmod +x dist/Similaris
echo
echo "Done: dist/Similaris"
echo "Run with: ./dist/Similaris"
