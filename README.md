# WinSlide

A borderless, always-on-top desktop slideshow widget for Windows. Point it at a folder and it shows your images in random order, changing every 30 seconds with a crossfade.

![WinSlide widget with hover controls](docs/widget.png)

## Features

- **True shuffle**: every image is shown once before the deck reshuffles, and never the same image twice in a row
- **Subfolders**: optionally includes images in nested folders; the folder is rescanned each cycle, so new photos appear without restarting
- **Crossfade transitions** and phone-photo rotation (EXIF) handled automatically
- **Hover controls**: back, pause/play and next
- **Drag to move**, drag the bottom-right corner to resize; position and size are remembered
- **Right-click menu** (also on the tray icon): change folder, interval (10 s to 15 min or custom), fill or fit, size presets, opacity, lock position, open or reveal the current image, start with Windows
- Supports JPG, PNG, BMP, GIF, WebP and TIFF

## Privacy

WinSlide runs entirely offline. It contains no networking code, telemetry or update checks. It reads the folder you choose and saves its settings to `HKEY_CURRENT_USER\Software\WinSlide`.

## Build

Requires Python 3.10+ on Windows.

1. Put `winslide.py` and `build.bat` in the same folder.
2. Double-click `build.bat`. It builds in `%LOCALAPPDATA%\WinSlide-build` and copies `WinSlide.exe` back next to the script.
3. Move `WinSlide.exe` somewhere permanent (outside Documents is best), then run it.

If Windows Security's Controlled Folder Access blocks the final copy, the script prints where the finished `.exe` is; move it with File Explorer.

To run from source instead: `pip install -r requirements.txt` then `pythonw winslide.py`.
