"""NOSTROMO.VID design system for the WinSlide and ReelDeck desktop widgets.

Values are copied from NOSTROMO.VID/widget.py COLORWAYS; no theme is coupled
to any playback, file scanning, networking or media state.
"""
from __future__ import annotations

COLORWAYS = {
    "Amber": {
        "accent": "#e8b65e", "hi": "#ffe1a2", "muted": "#947954",
        "edge": "#66522e", "dark": "#09100e", "panel": "#111a16",
        "button": "#1d261e",
    },
    "Phosphor": {
        "accent": "#a5d98b", "hi": "#d1f6b0", "muted": "#6f986a",
        "edge": "#3f6844", "dark": "#07120c", "panel": "#0e1b12",
        "button": "#1a2a1e",
    },
    "Emergency Red": {
        "accent": "#e8806e", "hi": "#ffc2b0", "muted": "#9c5a50",
        "edge": "#6a3b33", "dark": "#100b0a", "panel": "#1a1211",
        "button": "#2a1b19",
    },
    "Monochrome": {
        "accent": "#c0cec7", "hi": "#f2f5eb", "muted": "#8c9e96",
        "edge": "#5c7067", "dark": "#0b1112", "panel": "#161e20",
        "button": "#202b2c",
    },
}
THEME_CHOICES = ("Original", *COLORWAYS)


def palette(name):
    """Returns a defensive copy of the selected colourway, or None for Original."""
    if name == "Original":
        return None
    if name not in COLORWAYS:
        raise ValueError(f"Unknown Terminal theme: {name}")
    return COLORWAYS[name].copy()


def menu_stylesheet(name):
    """Apply NOSTROMO.VID-style menu chrome to every existing action."""
    c = palette(name)
    if c is None:
        return ""
    return (
        f"QMenu {{background:{c['dark']};color:{c['hi']};"
        f"border:1px solid {c['edge']};font:11px Consolas;padding:5px;}}"
        "QMenu::item {padding:7px 22px;}"
        f"QMenu::item:selected {{background:{c['accent']};color:{c['dark']};}}"
        f"QMenu::item:disabled {{color:{c['muted']};}}"
        f"QMenu::separator {{height:1px;background:{c['edge']};margin:4px 7px;}}"
        f"QMenu::indicator:checked {{background:{c['accent']};border:1px solid {c['accent']};}}"
    )


def paint_terminal_chrome(painter, width, height, name, title, status, subtitle):
    """Draw Nostromo video terminal header/footer above an existing media view.

    This does not alter mouse targets, viewport geometry or media pipelines.
    Imported Qt objects live here to keep the palette independently testable.
    """
    c = palette(name)
    if c is None or width < 140 or height < 100:
        return
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QFont, QPen

    p = painter
    p.save()
    dark, panel, edge = QColor(c["dark"]), QColor(c["panel"]), QColor(c["edge"])
    bright, accent, muted = QColor(c["hi"]), QColor(c["accent"]), QColor(c["muted"])
    p.setPen(Qt.NoPen)
    p.fillRect(QRectF(0, 0, width, 35), panel)
    p.fillRect(QRectF(0, height - 24, width, 24), dark)
    p.setPen(QPen(edge, 1))
    # Outline only: callers may leave a brush set (ReelDeck's hover controls do),
    # which would otherwise flood-fill the whole media viewport.
    p.setBrush(Qt.NoBrush)
    p.drawRect(QRectF(0.5, 0.5, width - 1, height - 1))
    p.drawLine(1, 35, width - 1, 35)
    p.drawLine(1, height - 24, width - 1, height - 24)
    p.setFont(QFont("Consolas", 10, QFont.Bold))
    p.setPen(bright)
    p.drawText(QRectF(12, 2, max(0, width - 130), 30), Qt.AlignVCenter | Qt.AlignLeft, "◆ " + title)
    p.setFont(QFont("Consolas", 8))
    p.setPen(accent)
    p.drawText(QRectF(max(0, width - 120), 2, 110, 30),
               Qt.AlignRight | Qt.AlignVCenter, "● " + status)
    p.setPen(muted)
    p.drawText(QRectF(11, height - 24, max(0, width - 28), 23),
               Qt.AlignLeft | Qt.AlignVCenter, subtitle)
    p.restore()
