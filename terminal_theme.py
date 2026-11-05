"""Shared NOSTROMO.SYS Terminal design tokens (Qt-independent).

Keep these values synchronized across the desktop widget repositories.
The original Retrowave and Colony palettes are intentionally untouched.
"""
from __future__ import annotations

BASE = {
    "BG": "#080e0c",
    "PANEL": "#0f1915",
    "PANEL2": "#15211b",
    "LINE": "#324037",
    "INK": "#c7c9ad",
}
ACCENTS = {
    "terminal_amber": {
        "label": "Nostromo / Amber",
        "accent": "#f0b04b", "bright": "#ffd587",
        "low": "#9a7142", "alt": "#88d8bd",
    },
    "terminal_phosphor": {
        "label": "Nostromo / Phosphor",
        "accent": "#a8db87", "bright": "#d9fcb9",
        "low": "#668962", "alt": "#88d8bd",
    },
    "terminal_red": {
        "label": "Nostromo / Emergency Red",
        "accent": "#ff7a65", "bright": "#ffc1a7",
        "low": "#a9584d", "alt": "#8dcfd1",
    },
}
TERMINAL_NAMES = frozenset(ACCENTS)


def terminal_palette(name: str) -> dict[str, str]:
    """Complete visual tokens. Unknown keys fail early rather than silently styling wrongly."""
    if name not in ACCENTS:
        raise ValueError(f"Unknown Nostromo theme: {name}")
    return {**BASE, **ACCENTS[name]}


def legacy_roles(name: str, *, quota: bool = False, cassette: bool = False) -> dict[str, str]:
    """Adapt Nostromo tokens to the existing SENTRY/QUOTA/CASSETTE paint contracts."""
    t = terminal_palette(name)
    roles = {
        "label": t["label"],
        "BG": t["BG"], "BG2": t["PANEL"],
        "MAG": t["accent"], "CYAN": t["bright"],
        "YEL": t["alt"], "MUTE": t["low"],
        "WARN": "#f0b04b", "CRIT": "#ff7a65",
        "DIM": t["LINE"],
    }
    if quota:
        roles["OK"] = t["alt"]
    if cassette:
        roles.update(SUN=t["bright"], GRID=t["accent"])
    return roles


def menu_stylesheet(name: str) -> str:
    """High-contrast flat menus, matching the native NOSTROMO control surfaces."""
    t = terminal_palette(name)
    return (
        "QMenu { background:" + t["PANEL2"] + "; color:" + t["bright"] +
        "; border:1px solid " + t["LINE"] +
        "; font-family:Consolas,monospace; font-size:12px; }"
        "QMenu::item { padding:7px 24px; }"
        "QMenu::item:selected { background:" + t["accent"] +
        "; color:" + t["BG"] + "; }"
        "QMenu::item:disabled { color:" + t["low"] + "; }"
        "QMenu::separator { height:1px; background:" + t["LINE"] +
        "; margin:5px 9px; }"
        "QMenu::indicator:checked { background:" + t["accent"] +
        "; border:1px solid " + t["accent"] + "; }"
    )
