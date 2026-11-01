# WinSlide

A borderless, always-on-top desktop slideshow widget for Windows. Point it at a folder and it shows your images in random order, changing every 30 seconds with a crossfade.

![WinSlide widget with hover controls](docs/widget.png)

## Features

- **True shuffle**: every image is shown once before the deck reshuffles, and never the same image twice in a row
- **Subfolders**: optionally includes images in nested folders; the folder is rescanned each cycle, so new photos appear without restarting
- **Crossfade transitions** and phone-photo rotation (EXIF) handled automatically
- **Hover controls**: back, pause/play and next
- **Drag to move**, drag the bottom-right corner to resize; position and size are remembered
- **Right-click menu** (also on the tray icon): change folder, interval (10 s to 15 min or custom), fill or fit, size presets, opacity, lock position, open or reveal the current image, start with Windows, run updater
- Supports JPG, PNG, BMP, GIF, WebP and TIFF

## Privacy

WinSlide runs entirely offline. It contains no networking code, telemetry or update checks. It reads the folder you choose and saves its settings to `HKEY_CURRENT_USER\Software\WinSlide`.

## Install and update

Requires Windows, [Python 3.10+](https://www.python.org/downloads/) and, for updates from GitHub, [Git](https://git-scm.com/download/win) (`winget install Git.Git`).

1. Download `update.bat` from this repo and double-click it.
2. The first time, it downloads the code (you may be asked to sign in to GitHub once), builds `WinSlide.exe`, installs it to `%LOCALAPPDATA%\Programs\WinSlide`, adds **WinSlide** and **Update WinSlide** to the Start Menu, and launches it.
3. To update later, use **Update WinSlide** in the Start Menu or **Run updater…** in the right-click menu. It pulls the latest version, rebuilds, closes the running app, swaps the `.exe` in place and relaunches. Settings are kept.

If it's already up to date it just says so; run `update.bat /force` to rebuild anyway. Without Git, it builds from the files next to the script.

Only the updater script goes online. The app itself never connects to anything.

To run from source instead: `pip install -r requirements.txt` then `pythonw winslide.py`.
