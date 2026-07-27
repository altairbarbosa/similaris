# WinUI 3 Migration

Similaris is moving to a WinUI 3 shell while keeping the image, video, and
enhancement engine in Python.

## Architecture

- `src/Similaris.WinUI` contains the Windows App SDK / WinUI 3 interface.
- `photo_organizer.py` remains the Python core and the source of processing
  behavior.
- `PythonCoreRunner` starts the Python core as a child process, streams stdout
  and stderr into the WinUI log, and extracts progress percentages where the
  existing CLI output provides them.
- During development, the WinUI app looks for `.venv-windows\Scripts\python.exe`
  and runs `photo_organizer.py` directly.
- For Store/package builds, `build_python_core.bat` creates
  `dist\python-core\SimilarisCore\SimilarisCore.exe`; the WinUI project copies
  that folder into the app output under `Python\`.

## Requirements

- Visual Studio 2022 or newer with Windows App SDK / WinUI development tools.
- .NET SDK compatible with `net10.0-windows10.0.26100.0`.
- Windows 10 2004 or newer for the runtime target.
- Python 3 for building the bundled core.

## Development Run

From the repository root:

```powershell
python -m venv .venv-windows
.\.venv-windows\Scripts\python.exe -m pip install -r requirements.txt
dotnet run --project .\src\Similaris.WinUI\Similaris.WinUI.csproj
```

This runs the WinUI app and uses the local Python source core.

## Package-Oriented Build

```powershell
.\build_winui3.ps1 -Configuration Release -Package
```

The script first builds `SimilarisCore.exe` with PyInstaller, then publishes the
WinUI project for `win-x64`. The first run downloads FFmpeg and Real-ESRGAN into
the local `.build-tools` cache.

## Current Migration Slice

This first slice establishes the native WinUI shell, navigation, operation
controls, folder pickers, async execution, cancellation, progress display, and
log streaming. The next slice should deepen app parity: file-level source
selection, settings persistence, license view, donation link, and Store identity
integration.
