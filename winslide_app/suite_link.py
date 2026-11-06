"""NOSTROMO.SUITE link: lets a widget run under the suite launcher.

Vendored unchanged into every suite widget package; the suite build checks the
copies match. Pure helpers (argument parsing, message encoding) need no Qt so
they can be unit-tested anywhere. The Qt part is imported only in suite mode,
so standalone builds that exclude QtNetwork keep working.

Protocol: newline-delimited JSON over a local named pipe (QLocalSocket).
  widget -> launcher: hello {id, pid}, ready, readout {text}, bye
  launcher -> widget: theme {name}, show, menu, quit
Local only: no network sockets, nothing leaves the PC.
"""
from __future__ import annotations

import json
import os

PROTOCOL = 1
SUITE_THEMES = ("amber", "phosphor", "red", "mono")
MAX_LINE = 4096
READOUT_MAX = 48


class SuiteArgs:
    __slots__ = ("pipe", "theme")

    def __init__(self, pipe: str, theme: str):
        self.pipe = pipe
        self.theme = theme if theme in SUITE_THEMES else "amber"

    def __repr__(self):
        return f"SuiteArgs(pipe={self.pipe!r}, theme={self.theme!r})"


def from_argv(argv) -> SuiteArgs | None:
    """Return SuiteArgs when launched by the suite (--suite-pipe NAME), else None."""
    pipe, theme = None, "amber"
    args = list(argv)
    for i, a in enumerate(args):
        if a == "--suite-pipe" and i + 1 < len(args):
            pipe = args[i + 1]
        elif a.startswith("--suite-pipe="):
            pipe = a.split("=", 1)[1]
        elif a == "--suite-theme" and i + 1 < len(args):
            theme = args[i + 1]
        elif a.startswith("--suite-theme="):
            theme = a.split("=", 1)[1]
    if not pipe or not all(c.isalnum() or c in "-_." for c in pipe):
        return None
    return SuiteArgs(pipe, theme)


def encode(kind: str, **fields) -> bytes:
    msg = {"v": PROTOCOL, "t": kind}
    msg.update(fields)
    data = json.dumps(msg, separators=(",", ":"), ensure_ascii=True)
    return (data + "\n").encode("ascii")


def decode(line) -> dict | None:
    """Parse one line; anything malformed or oversized is ignored (returns None)."""
    if isinstance(line, (bytes, bytearray)):
        if len(line) > MAX_LINE:
            return None
        try:
            line = bytes(line).decode("ascii")
        except UnicodeDecodeError:
            return None
    line = line.strip()
    if not line or len(line) > MAX_LINE:
        return None
    try:
        msg = json.loads(line)
    except ValueError:
        return None
    if not isinstance(msg, dict) or not isinstance(msg.get("t"), str):
        return None
    return msg


def clip_readout(text) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= READOUT_MAX else text[:READOUT_MAX - 1] + "…"


def adapt_menu(menu):
    """Suite-mode tweaks to a widget's own right-click menu.

    Theme, startup and updates belong to the suite, and "Quit" only closes this widget
    (the launcher keeps running), so it reads "Close".
    """
    for action in menu.actions():
        text = action.text().replace("&", "")
        if action.menu() is not None and text in ("Theme", "Terminal theme"):
            action.setText("Theme · set in NOSTROMO.SUITE")
            action.setEnabled(False)
        elif text.startswith("Run updater") or text == "Start with Windows":
            action.setVisible(False)
        elif text == "Quit":
            action.setText("Close")
    return menu


def make_link(widget_id, args: SuiteArgs, readout=None, interval_ms=2000):
    """Create the Qt link object. Call after QApplication exists."""
    from PySide6.QtCore import QObject, QTimer, Signal
    from PySide6.QtNetwork import QLocalSocket

    class SuiteLink(QObject):
        theme_changed = Signal(str)
        show_requested = Signal()
        menu_requested = Signal()
        quit_requested = Signal()

        def __init__(self):
            super().__init__()
            self.widget_id = widget_id
            self.theme = args.theme
            self._readout = readout
            self._buf = bytearray()
            self._closing = False
            self.lost = False
            self.sock = QLocalSocket(self)
            self.sock.readyRead.connect(self._read)
            self.sock.disconnected.connect(self._lost)
            self.sock.errorOccurred.connect(lambda _e: self._lost())
            self.sock.connectToServer(args.pipe)
            if self.sock.waitForConnected(2000):
                self._send("hello", id=widget_id, pid=os.getpid())
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.push_readout)
            if readout is not None:
                self.timer.start(interval_ms)

        @property
        def connected(self):
            return self.sock.state() == QLocalSocket.ConnectedState

        def _send(self, kind, **fields):
            if self.connected:
                self.sock.write(encode(kind, **fields))
                self.sock.flush()

        def ready(self):
            self._send("ready")
            self.push_readout()

        def push_readout(self):
            if self._readout is None:
                return
            try:
                text = clip_readout(self._readout())
            except Exception:
                return
            self._send("readout", text=text)

        def bye(self):
            self._closing = True
            self._send("bye")
            if self.connected:
                self.sock.waitForBytesWritten(500)

        def _read(self):
            self._buf += bytes(self.sock.readAll())
            if len(self._buf) > MAX_LINE * 8:
                self._buf.clear()
            while b"\n" in self._buf:
                line, _, rest = bytes(self._buf).partition(b"\n")
                self._buf = bytearray(rest)
                msg = decode(line)
                if msg is None:
                    continue
                kind = msg["t"]
                if kind == "theme" and msg.get("name") in SUITE_THEMES:
                    self.theme = msg["name"]
                    self.theme_changed.emit(self.theme)
                elif kind == "show":
                    self.show_requested.emit()
                elif kind == "menu":
                    self.menu_requested.emit()
                elif kind == "quit":
                    self.quit_requested.emit()

        def _lost(self):
            # Launcher gone: a suite widget has no tray of its own, so close cleanly.
            # `lost` stays set so a widget that wires its signals late can still check it.
            self.lost = True
            if not self._closing:
                self._closing = True
                self.quit_requested.emit()

    return SuiteLink()
