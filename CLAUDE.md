# CLAUDE.md — WinSlide

This repository is one of five Windows desktop widgets managed by the user's **Nostromo Widgets / Claude handoff** workspace.

## Quick orientation
- Owner: `MajorRoyMcCalluster`; entrypoint: `winslide.py`; installed binary name: `WinSlide.exe`.
- Source technology: Python / PySide6. Existing `update.bat` performs legacy first-install/update from `origin/main` and uses application version text to decide rebuilds.
- Core functionality: photo folder shuffling, resize, crossfade, hover controls and system tray.
- Terminal visual reference: **NOSTROMO.VID**. This branch adds the corresponding Nostromo theme family, while retaining existing themes and app functionality.
- Source checkout and Git-SHA-aware installation can be managed from the separately provided **Claude-Nostromo-Handoff** package: `Manage-Nostromo.ps1`, `projects.json`, and `README.md`.

## Installation / update policy
1. Use the handoff manager, not `update.bat`, when testing `feature/nostromo-terminal-ui`: the legacy updater resets its own build cache to `origin/main` and may skip recompilation when `__version__` is unchanged.
2. Run `Manage-Nostromo.ps1 -Action Install -Channel terminal-preview -Project WinSlide` to pull/build this branch. `-Action Update -Project WinSlide` preserves the last installed channel and skips unchanged SHAs.
3. Private repository access is via local `gh auth login` + `gh auth setup-git`, not copy-pasted personal access tokens.
4. Never discard local changes, force-push, or modify `main` without deliberate PR review.
5. Quit the app via tray before replacing its executable; preserve user QSettings, saved preferences and credential stores.

## Tests and rules
- Run Python syntax verification and `tests/test_terminal_theme.py`. For media widgets also run `tests/test_terminal_qt_smoke.py` in Windows offscreen Qt.
- Check GitHub Actions CI in `.github/workflows/terminal-regression.yml`.
- Verify real Windows behaviour before declaring success: Preserve image fit, EXIF rotation, shuffle history, and Original appearance.
- Windows executable builds, native events and video rendering are **not validated by isolated theme tests alone**.
- Keep Retrowave/Vaporwave changes separate from Terminal UI work. All saved theme selections should remain backward compatible.
