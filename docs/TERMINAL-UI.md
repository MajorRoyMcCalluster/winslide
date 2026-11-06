# NOSTROMO.VID Terminal appearance

The Terminal appearance follows the **NOSTROMO.VID** video widget's original `COLORWAYS` table.
Use **right click → Terminal theme** to switch between:

- **Original** (default): unchanged original UI, viewport and interaction targets
- **Amber**: NOSTROMO.VID amber, `#e8b65e`
- **Phosphor**: NOSTROMO.VID phosphor, `#a5d98b`
- **Monochrome**: NOSTROMO.VID monochrome, `#c0cec7`

Shared components are in `terminal_theme.py`. Video/slideshow rendering remains in the existing application.
Themes persist through the existing QSettings configuration and are independent of media data.

The Terminal layer adds square chrome, a 35px terminal header, a 24px status footer,
theme-aware toolbars and a matching right-click menu. Existing media behaviour is not
rewritten. Media imagery can remain letterboxed, cropped, paused, or transitioned
exactly as before. The project-specific player still owns those decisions.

## Verification

Run the deterministic tests (no Qt required):

```powershell
py -m unittest discover -s tests -p test_terminal_theme.py -v
```

Run offscreen Qt painting tests (requires PySide6-Essentials):

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
py -m unittest discover -s tests -p test_terminal_qt_smoke.py -v
```

These checks are also in `.github/workflows/terminal-regression.yml`.

**Still required:** Windows on-device interaction testing, multi-monitor DPI and Windows tray integration,
live image/video rendering, codec compatibility, animations under rapid resizing, and distribution builds.
Regression passes are not proof that all those behaviours work on the user's computer.

Future Vaporwave enhancements should be developed independently without replacing these saved themes.
