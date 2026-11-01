"""
WinSlide - a borderless, always-on-top desktop slideshow widget for Windows.

- Shows images from a chosen folder (optionally including subfolders) in random order
- Changes image every 30 seconds by default, cycling through every image before reshuffling
- Crossfade transitions
- Hover for back / pause / next controls
- Drag to move, drag the bottom-right corner to resize
- Right-click (or the tray icon) for all settings
"""

import os
import random
import sys

from PySide6.QtCore import (
    QDir, QEasingCurve, QLockFile, QPoint, QPointF, QRect, QRectF, QSettings, QSize, Qt, QTimer,
    QUrl, QVariantAnimation, Signal,
)
from PySide6.QtGui import (
    QAction, QActionGroup, QColor, QCursor, QDesktopServices, QFont, QGuiApplication,
    QIcon, QImageReader, QPainter, QPainterPath, QPen, QPixmap, QPolygonF,
)
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QGraphicsOpacityEffect, QHBoxLayout, QInputDialog,
    QMenu, QSystemTrayIcon, QWidget,
)

APP_NAME = "WinSlide"
__version__ = "1.0.4"
APP_ID = "WinSlide"
LEGACY_IDS = ("Gooner", "PhotoShuffle")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tif", ".tiff"}
CORNER_RADIUS = 14
RESIZE_GRIP = 18
MIN_SIZE = QSize(160, 120)
FADE_MS = 900
HISTORY_LIMIT = 50

INTERVAL_PRESETS = [(10, "10 seconds"), (30, "30 seconds"), (60, "1 minute"),
                    (300, "5 minutes"), (900, "15 minutes")]
SIZE_PRESETS = [("Small", QSize(320, 220)), ("Medium", QSize(480, 320)),
                ("Large", QSize(720, 480))]
OPACITY_PRESETS = [100, 85, 70, 50]


# --------------------------------------------------------------------------- #
# Start with Windows (HKCU Run key)
# --------------------------------------------------------------------------- #
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _launch_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    exe = sys.executable
    pythonw = os.path.join(os.path.dirname(exe), "pythonw.exe")
    if os.path.exists(pythonw):
        exe = pythonw
    return f'"{exe}" "{os.path.abspath(__file__)}"'


def startup_supported():
    return sys.platform == "win32"


def migrate_legacy():
    """Carry settings over from earlier names of this app and replace their startup entries."""
    new = QSettings(APP_ID, APP_ID)
    for legacy in LEGACY_IDS:
        old = QSettings(legacy, legacy)
        if not new.allKeys() and old.allKeys():
            for k in old.allKeys():
                new.setValue(k, old.value(k))
        if startup_supported():
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                                    winreg.KEY_QUERY_VALUE | winreg.KEY_SET_VALUE) as key:
                    winreg.QueryValueEx(key, legacy)
                    winreg.DeleteValue(key, legacy)
                    winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, _launch_command())
            except OSError:
                pass


def refresh_startup_path():
    """If start-with-Windows points at an old copy of the app, point it at this one."""
    if not startup_enabled():
        return
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            cur = winreg.QueryValueEx(k, APP_ID)[0]
        if cur != _launch_command():
            set_startup(True)
    except OSError:
        pass


def startup_enabled():
    if not startup_supported():
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_ID)
            return True
    except OSError:
        return False


def set_startup(enabled):
    if not startup_supported():
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(key, APP_ID)
            except OSError:
                pass


# --------------------------------------------------------------------------- #
# Shuffle deck: random order, no repeats until every image has been shown
# --------------------------------------------------------------------------- #
class ShuffleDeck:
    def __init__(self):
        self.folder = ""
        self.recursive = True
        self._deck = []

    def configure(self, folder, recursive):
        self.folder = folder
        self.recursive = recursive
        self._deck = []

    def scan(self):
        files = []
        if not self.folder or not os.path.isdir(self.folder):
            return files
        if self.recursive:
            for root, _dirs, names in os.walk(self.folder):
                for n in names:
                    if os.path.splitext(n)[1].lower() in IMAGE_EXTS:
                        files.append(os.path.join(root, n))
        else:
            for n in os.listdir(self.folder):
                p = os.path.join(self.folder, n)
                if os.path.isfile(p) and os.path.splitext(n)[1].lower() in IMAGE_EXTS:
                    files.append(p)
        return files

    def next(self, avoid=None):
        """Return the next image path, or None if the folder has no images."""
        if not self._deck:
            # Rescan each cycle so new or deleted files are picked up
            self._deck = self.scan()
            random.shuffle(self._deck)
            # Don't show the same image twice in a row across a reshuffle
            if avoid and len(self._deck) > 1 and self._deck[-1] == avoid:
                self._deck[0], self._deck[-1] = self._deck[-1], self._deck[0]
        while self._deck:
            path = self._deck.pop()
            if os.path.isfile(path):
                return path
        return None


# --------------------------------------------------------------------------- #
# Drawn icons (crisp at any DPI, no font dependence)
# --------------------------------------------------------------------------- #
SMALL_ICON_MAX = 48  # at or below this size, draw the simplified peach


def draw_small_peach(p, size):
    """Emoji-style peach filling the whole square, for tray/taskbar sizes."""
    p.save()
    p.scale(size / 16.0, size / 16.0)
    p.setPen(Qt.NoPen)
    body = QPainterPath(QPointF(8, 4.2))
    body.cubicTo(5.6, 2.4, 0.4, 3.4, 0.8, 8.6)
    body.cubicTo(1.1, 12.8, 4.6, 15.6, 8, 15.6)
    body.cubicTo(11.4, 15.6, 14.9, 12.8, 15.2, 8.6)
    body.cubicTo(15.6, 3.4, 10.4, 2.4, 8, 4.2)
    p.setBrush(QColor("#F5A06B"))
    p.drawPath(body)
    shade = QPainterPath(QPointF(8, 4.2))
    shade.cubicTo(10.4, 2.4, 15.6, 3.4, 15.2, 8.6)
    shade.cubicTo(14.9, 12.8, 11.4, 15.6, 8, 15.6)
    shade.cubicTo(9.8, 13, 10.6, 9.6, 9.9, 6.6)
    shade.cubicTo(9.6, 5.4, 8.9, 4.6, 8, 4.2)
    p.setBrush(QColor("#E8784F"))
    p.drawPath(shade)
    cleft = QPainterPath(QPointF(8, 4.8))
    cleft.cubicTo(6.9, 7.6, 6.9, 11.6, 8, 14.8)
    pen = QPen(QColor("#B4442C"), 1.3)
    pen.setCapStyle(Qt.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawPath(cleft)
    p.setPen(Qt.NoPen)
    for cx, cy, rx, ry, rot, col in ((5.4, 2.4, 3, 1.5, -25, "#639922"),
                                     (10.4, 2.2, 2.6, 1.3, 20, "#3B6D11")):
        p.save()
        p.translate(cx, cy)
        p.rotate(rot)
        p.setBrush(QColor(col))
        p.drawEllipse(QRectF(-rx, -ry, 2 * rx, 2 * ry))
        p.restore()
    p.restore()


def app_icon():
    """Multi-size icon so Windows picks a sharp, size-appropriate image (tray, taskbar, window)."""
    icon = QIcon()
    for n in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        icon.addPixmap(make_icon("app", n).pixmap(n, n))
    return icon


def make_icon(kind, size=40, color=QColor(255, 255, 255)):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(color)
    s = size
    if kind == "play":
        p.drawPolygon(QPolygonF([QPointF(s * .34, s * .24), QPointF(s * .34, s * .76),
                                 QPointF(s * .78, s * .5)]))
    elif kind == "pause":
        p.drawRoundedRect(QRectF(s * .28, s * .24, s * .15, s * .52), 2, 2)
        p.drawRoundedRect(QRectF(s * .57, s * .24, s * .15, s * .52), 2, 2)
    elif kind in ("next", "prev"):
        if kind == "prev":
            p.translate(s, 0)
            p.scale(-1, 1)
        p.drawPolygon(QPolygonF([QPointF(s * .26, s * .26), QPointF(s * .26, s * .74),
                                 QPointF(s * .62, s * .5)]))
        p.drawRoundedRect(QRectF(s * .64, s * .26, s * .1, s * .48), 2, 2)
    elif kind == "app" and size <= SMALL_ICON_MAX:
        draw_small_peach(p, size)
    elif kind == "app":  # peach photo stack (drawn on a 96-unit grid)
        k = s / 96.0
        p.scale(k, k)
        p.setBrush(QColor("#26215C"))
        p.drawRoundedRect(QRectF(0, 0, 96, 96), 18, 18)
        p.save()  # back card, tilted
        p.translate(49, 46)
        p.rotate(-10)
        p.setBrush(QColor("#7F77DD"))
        p.drawRoundedRect(QRectF(-27, -32, 54, 64), 5, 5)
        p.restore()
        p.setBrush(QColor("#FBEAF0"))  # front card
        p.drawRoundedRect(QRectF(20, 18, 56, 66), 5, 5)
        p.save()  # the peach
        p.translate(9, 6)
        p.scale(0.82, 0.82)
        body = QPainterPath(QPointF(48, 36))
        body.cubicTo(36, 27, 21, 37, 25, 53)
        body.cubicTo(28, 65, 39, 72, 48, 72)
        body.cubicTo(57, 72, 68, 65, 71, 53)
        body.cubicTo(75, 37, 60, 27, 48, 36)
        p.setBrush(QColor("#F5A06B"))
        p.drawPath(body)
        shade = QPainterPath(QPointF(48, 36))
        shade.cubicTo(60, 27, 75, 37, 71, 53)
        shade.cubicTo(68, 65, 57, 72, 48, 72)
        shade.cubicTo(54, 66, 58, 56, 56, 45)
        shade.cubicTo(55, 40, 52, 37, 48, 36)
        p.setBrush(QColor("#E8784F"))
        p.drawPath(shade)
        cleft = QPainterPath(QPointF(48, 38))
        cleft.cubicTo(44, 47, 44, 60, 48, 70)
        pen = QPen(QColor("#C4553A"), 2.5)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(cleft)
        p.setPen(Qt.NoPen)
        for cx, cy, rx, ry, rot, col in ((40, 31, 9, 4.5, -25, "#639922"),
                                         (55, 30, 8, 4, 20, "#3B6D11")):
            p.save()
            p.translate(cx, cy)
            p.rotate(rot)
            p.setBrush(QColor(col))
            p.drawEllipse(QRectF(-rx, -ry, 2 * rx, 2 * ry))
            p.restore()
        p.restore()
    p.end()
    return QIcon(pm)


class IconButton(QWidget):
    clicked = Signal()

    def __init__(self, kind, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.hover = False
        self.setFixedSize(34, 34)
        self.setCursor(Qt.PointingHandCursor)

    def set_kind(self, kind):
        self.kind = kind
        self.update()

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def mousePressEvent(self, e):
        e.accept()  # don't start a window drag from a button

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.hover:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(255, 255, 255, 40))
            p.drawEllipse(self.rect().adjusted(1, 1, -1, -1))
        make_icon(self.kind, 22).paint(p, QRect(6, 6, 22, 22))


class ControlBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 4, 8, 4)
        lay.setSpacing(6)
        self.prev_btn = IconButton("prev", self)
        self.play_btn = IconButton("pause", self)
        self.next_btn = IconButton("next", self)
        for b in (self.prev_btn, self.play_btn, self.next_btn):
            lay.addWidget(b)
        self.adjustSize()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, 150))
        r = QRectF(self.rect())
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)


# --------------------------------------------------------------------------- #
# The widget
# --------------------------------------------------------------------------- #
class WinSlide(QWidget):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.setMinimumSize(MIN_SIZE)
        self.setMouseTracking(True)

        self.settings = QSettings(APP_ID, APP_ID)
        self.folder = self.settings.value("folder", "", str)
        self.interval = int(self.settings.value("interval", 30))
        self.recursive = self.settings.value("recursive", True, bool)
        self.fit_mode = self.settings.value("fit", "fill", str)  # fill | fit
        self.locked = self.settings.value("locked", False, bool)
        self.opacity_pct = int(self.settings.value("opacity", 100))
        self.paused = False

        self.deck = ShuffleDeck()
        self.deck.configure(self.folder, self.recursive)

        self.current_path = None
        self.cur_pix = None
        self.next_pix = None
        self.fade = 0.0
        self.history = []
        self.history_pos = -1

        self._drag_offset = None
        self._resizing = False
        self._resize_origin = None

        self.fade_anim = QVariantAnimation(self)
        self.fade_anim.setDuration(FADE_MS)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.InOutQuad)
        self.fade_anim.valueChanged.connect(self._on_fade)
        self.fade_anim.finished.connect(self._finish_fade)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.next_image)

        self.reload_timer = QTimer(self)  # reload at full res after a resize
        self.reload_timer.setSingleShot(True)
        self.reload_timer.timeout.connect(self._reload_current)

        self.controls = ControlBar(self)
        self.controls.prev_btn.clicked.connect(self.prev_image)
        self.controls.play_btn.clicked.connect(self.toggle_pause)
        self.controls.next_btn.clicked.connect(self.next_image)
        self.ctrl_effect = QGraphicsOpacityEffect(self.controls)
        self.ctrl_effect.setOpacity(0.0)
        self.controls.setGraphicsEffect(self.ctrl_effect)
        self.ctrl_anim = QVariantAnimation(self)
        self.ctrl_anim.setDuration(180)
        self.ctrl_anim.valueChanged.connect(self.ctrl_effect.setOpacity)

        self._restore_geometry()
        self.setWindowOpacity(self.opacity_pct / 100)
        self._build_tray()

    # ---------------- geometry ----------------
    def _restore_geometry(self):
        size = self.settings.value("size", QSize(480, 320))
        pos = self.settings.value("pos", None)
        self.resize(size)
        screens = QGuiApplication.screens()
        if pos is not None and any(s.availableGeometry().contains(pos) for s in screens):
            self.move(pos)
        else:
            ag = QGuiApplication.primaryScreen().availableGeometry()
            self.move(ag.right() - self.width() - 40, ag.top() + 40)

    def _save_geometry(self):
        self.settings.setValue("size", self.size())
        self.settings.setValue("pos", self.pos())

    # ---------------- startup ----------------
    def start(self):
        self.show()
        if not self.folder or not os.path.isdir(self.folder):
            QTimer.singleShot(200, self.choose_folder)
        else:
            self.next_image()
        self._restart_timer()

    def _restart_timer(self):
        self.timer.stop()
        if not self.paused:
            self.timer.start(self.interval * 1000)

    # ---------------- image loading ----------------
    def _load(self, path):
        reader = QImageReader(path)
        reader.setAutoTransform(True)  # respect phone EXIF rotation
        src = reader.size()
        dpr = self.devicePixelRatioF()
        target = max(self.width(), self.height()) * dpr
        if src.isValid() and min(src.width(), src.height()) > target:
            f = target / min(src.width(), src.height())
            reader.setScaledSize(QSize(max(1, int(src.width() * f)),
                                       max(1, int(src.height() * f))))
        img = reader.read()
        if img.isNull():
            return None
        return QPixmap.fromImage(img)

    def _show_path(self, path, animate=True):
        pix = self._load(path)
        if pix is None:
            return False
        if self.fade_anim.state() == QVariantAnimation.Running:
            self.fade_anim.stop()
            self._finish_fade()
        self.current_path = path
        if self.cur_pix is None or not animate:
            self.cur_pix = pix
            self.update()
        else:
            self.next_pix = pix
            self.fade = 0.0
            self.fade_anim.start()
        self.setToolTip(os.path.basename(path))
        return True

    def _on_fade(self, v):
        self.fade = float(v)
        self.update()

    def _finish_fade(self):
        if self.next_pix is not None:
            self.cur_pix = self.next_pix
            self.next_pix = None
        self.fade = 0.0
        self.update()

    def _reload_current(self):
        if self.current_path and self.fade_anim.state() != QVariantAnimation.Running:
            pix = self._load(self.current_path)
            if pix is not None:
                self.cur_pix = pix
                self.update()

    # ---------------- navigation ----------------
    def next_image(self):
        # Step forward through history first if we went back
        if self.history_pos < len(self.history) - 1:
            self.history_pos += 1
            self._show_path(self.history[self.history_pos])
            self._restart_timer()
            return
        for _ in range(20):  # skip unreadable files
            path = self.deck.next(avoid=self.current_path)
            if path is None:
                self.cur_pix = None
                self.current_path = None
                self.update()
                break
            if self._show_path(path):
                self.history.append(path)
                if len(self.history) > HISTORY_LIMIT:
                    self.history.pop(0)
                self.history_pos = len(self.history) - 1
                break
        self._restart_timer()

    def prev_image(self):
        if self.history_pos > 0:
            self.history_pos -= 1
            self._show_path(self.history[self.history_pos])
        self._restart_timer()

    def toggle_pause(self):
        self.paused = not self.paused
        self.controls.play_btn.set_kind("play" if self.paused else "pause")
        self._restart_timer()
        if hasattr(self, "pause_action"):
            self.pause_action.setChecked(self.paused)

    # ---------------- painting ----------------
    def _target_rect(self, pix):
        w, h = self.width(), self.height()
        pw, ph = pix.width() / pix.devicePixelRatio(), pix.height() / pix.devicePixelRatio()
        if pw <= 0 or ph <= 0:
            return QRectF(0, 0, w, h)
        if self.fit_mode == "fill":
            s = max(w / pw, h / ph)
        else:
            s = min(w / pw, h / ph)
        tw, th = pw * s, ph * s
        return QRectF((w - tw) / 2, (h - th) / 2, tw, th)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), CORNER_RADIUS, CORNER_RADIUS)
        p.setClipPath(path)
        p.fillPath(path, QColor(18, 18, 18))

        if self.cur_pix is not None:
            p.setOpacity(1.0)
            p.drawPixmap(self._target_rect(self.cur_pix), self.cur_pix, QRectF(self.cur_pix.rect()))
        if self.next_pix is not None:
            p.setOpacity(self.fade)
            p.drawPixmap(self._target_rect(self.next_pix), self.next_pix, QRectF(self.next_pix.rect()))
            p.setOpacity(1.0)

        if self.cur_pix is None and self.next_pix is None:
            p.setPen(QColor(200, 200, 200))
            f = QFont(self.font())
            f.setPointSize(10)
            p.setFont(f)
            msg = ("No images found in this folder.\nRight-click to choose another."
                   if self.folder else "Right-click to choose a folder")
            p.drawText(self.rect(), Qt.AlignCenter, msg)

        # Resize grip hint while hovered
        if self.underMouse() and not self.locked:
            p.setPen(QPen(QColor(255, 255, 255, 150), 1.6))
            r = self.rect()
            for i in (5, 10):
                p.drawLine(r.right() - i - 3, r.bottom() - 4, r.right() - 4, r.bottom() - i - 3)

    # ---------------- hover controls ----------------
    def _place_controls(self):
        self.controls.adjustSize()
        cw, ch = self.controls.width(), self.controls.height()
        self.controls.move((self.width() - cw) // 2, self.height() - ch - 12)

    def resizeEvent(self, e):
        self._place_controls()
        self.reload_timer.start(250)
        super().resizeEvent(e)

    def _fade_controls(self, to):
        self.ctrl_anim.stop()
        self.ctrl_anim.setStartValue(self.ctrl_effect.opacity())
        self.ctrl_anim.setEndValue(to)
        self.ctrl_anim.start()

    def enterEvent(self, e):
        self._fade_controls(1.0)
        self.update()

    def leaveEvent(self, e):
        self._fade_controls(0.0)
        self.setCursor(Qt.ArrowCursor)
        self.update()

    # ---------------- move / resize ----------------
    def _in_grip(self, pt):
        return (not self.locked and pt.x() >= self.width() - RESIZE_GRIP
                and pt.y() >= self.height() - RESIZE_GRIP)

    def mousePressEvent(self, e):
        if e.button() != Qt.LeftButton or self.locked:
            return
        pt = e.position().toPoint()
        if self._in_grip(pt):
            self._resizing = True
            self._resize_origin = (e.globalPosition().toPoint(), self.size())
        else:
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        gp = e.globalPosition().toPoint()
        if self._resizing and self._resize_origin:
            start, size = self._resize_origin
            d = gp - start
            self.resize(max(MIN_SIZE.width(), size.width() + d.x()),
                        max(MIN_SIZE.height(), size.height() + d.y()))
        elif self._drag_offset is not None:
            self.move(gp - self._drag_offset)
        else:
            self.setCursor(Qt.SizeFDiagCursor if self._in_grip(e.position().toPoint())
                           else Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        if self._drag_offset is not None or self._resizing:
            self._save_geometry()
        self._drag_offset = None
        self._resizing = False
        self.setCursor(Qt.ArrowCursor)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.open_current()

    # ---------------- menu ----------------
    def build_menu(self, parent=None):
        m = QMenu(parent or self)

        m.addAction("Next image", self.next_image)
        m.addAction("Previous image", self.prev_image)
        self.pause_action = QAction("Pause", m, checkable=True)
        self.pause_action.setChecked(self.paused)
        self.pause_action.triggered.connect(lambda _=False: self.toggle_pause())
        m.addAction(self.pause_action)
        m.addSeparator()

        m.addAction("Choose folder…", self.choose_folder)
        sub = QAction("Include subfolders", m, checkable=True)
        sub.setChecked(self.recursive)
        sub.triggered.connect(self.set_recursive)
        m.addAction(sub)

        im = m.addMenu("Change every")
        grp = QActionGroup(im)
        matched = False
        for secs, label in INTERVAL_PRESETS:
            a = QAction(label, im, checkable=True)
            a.setChecked(secs == self.interval)
            matched |= secs == self.interval
            a.triggered.connect(lambda _=False, s=secs: self.set_interval(s))
            grp.addAction(a)
            im.addAction(a)
        im.addSeparator()
        custom = QAction(f"Custom… ({self.interval}s)" if not matched else "Custom…",
                         im, checkable=True)
        custom.setChecked(not matched)
        custom.triggered.connect(self.custom_interval)
        grp.addAction(custom)
        im.addAction(custom)
        m.addSeparator()

        fm = m.addMenu("Image fit")
        fg = QActionGroup(fm)
        for key, label in (("fill", "Fill (crop to fit)"), ("fit", "Fit (show whole image)")):
            a = QAction(label, fm, checkable=True)
            a.setChecked(self.fit_mode == key)
            a.triggered.connect(lambda _=False, k=key: self.set_fit(k))
            fg.addAction(a)
            fm.addAction(a)

        sm = m.addMenu("Size")
        for label, size in SIZE_PRESETS:
            sm.addAction(f"{label} ({size.width()}×{size.height()})",
                         lambda s=size: self.set_size(s))

        om = m.addMenu("Opacity")
        og = QActionGroup(om)
        for pct in OPACITY_PRESETS:
            a = QAction(f"{pct}%", om, checkable=True)
            a.setChecked(pct == self.opacity_pct)
            a.triggered.connect(lambda _=False, v=pct: self.set_opacity(v))
            og.addAction(a)
            om.addAction(a)

        lock = QAction("Lock position and size", m, checkable=True)
        lock.setChecked(self.locked)
        lock.triggered.connect(self.set_locked)
        m.addAction(lock)
        m.addSeparator()

        cur = m.addAction("Open current image", self.open_current)
        loc = m.addAction("Show in File Explorer", self.reveal_current)
        cur.setEnabled(bool(self.current_path))
        loc.setEnabled(bool(self.current_path))
        m.addSeparator()

        if startup_supported():
            st = QAction("Start with Windows", m, checkable=True)
            st.setChecked(startup_enabled())
            st.triggered.connect(set_startup)
            m.addAction(st)

        vis = m.addAction("Hide widget" if self.isVisible() else "Show widget",
                          self.toggle_visible)
        m.addSeparator()
        m.addAction("Run updater…", self.run_updater)
        ver = m.addAction(f"{APP_NAME} v{__version__}")
        ver.setEnabled(False)
        m.addAction("Quit", self.quit)
        return m

    def contextMenuEvent(self, e):
        self.build_menu().exec(e.globalPos())

    # ---------------- tray ----------------
    def _build_tray(self):
        self.tray = None
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(app_icon(), self)
        self.tray.setToolTip(APP_NAME)
        self.tray_menu = QMenu()
        self.tray_menu.aboutToShow.connect(self._refresh_tray_menu)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(
            lambda r: self.toggle_visible() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _refresh_tray_menu(self):
        self.tray_menu.clear()
        old = getattr(self, "_tray_src", None)
        if old is not None:
            old.deleteLater()
        self._tray_src = self.build_menu(self.tray_menu)
        for a in self._tray_src.actions():
            self.tray_menu.addAction(a)

    # ---------------- setting handlers ----------------
    def choose_folder(self):
        start = self.folder or os.path.join(os.path.expanduser("~"), "Pictures")
        folder = QFileDialog.getExistingDirectory(None, "Choose a folder of images", start)
        if folder:
            self.folder = folder
            self.settings.setValue("folder", folder)
            self.deck.configure(self.folder, self.recursive)
            self.history.clear()
            self.history_pos = -1
            self.next_image()

    def set_recursive(self, on):
        self.recursive = bool(on)
        self.settings.setValue("recursive", self.recursive)
        self.deck.configure(self.folder, self.recursive)

    def set_interval(self, secs):
        self.interval = max(3, int(secs))
        self.settings.setValue("interval", self.interval)
        self._restart_timer()

    def custom_interval(self):
        secs, ok = QInputDialog.getInt(None, APP_NAME, "Seconds between images:",
                                       self.interval, 3, 86400, 1)
        if ok:
            self.set_interval(secs)

    def set_fit(self, mode):
        self.fit_mode = mode
        self.settings.setValue("fit", mode)
        self.update()

    def set_size(self, size):
        self.resize(size)
        self._save_geometry()

    def set_opacity(self, pct):
        self.opacity_pct = pct
        self.settings.setValue("opacity", pct)
        self.setWindowOpacity(pct / 100)

    def set_locked(self, on):
        self.locked = bool(on)
        self.settings.setValue("locked", self.locked)
        self.update()

    def open_current(self):
        if self.current_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_path))

    def reveal_current(self):
        if not self.current_path:
            return
        if sys.platform == "win32":
            import subprocess
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self.current_path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.current_path)))

    def run_updater(self):
        """Launch update.bat from the install folder. The script, not this app, talks to GitHub."""
        base = os.path.dirname(sys.executable if getattr(sys, "frozen", False)
                               else os.path.abspath(__file__))
        bat = os.path.join(base, "update.bat")
        if sys.platform == "win32" and os.path.exists(bat):
            os.startfile(bat)
        elif self.tray:
            self.tray.showMessage(APP_NAME, "update.bat not found next to the app. "
                                  "Run update.bat from your download folder once to install it.",
                                  QSystemTrayIcon.Information, 8000)

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def quit(self):
        self._save_geometry()
        if self.tray:
            self.tray.hide()
        QApplication.quit()


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    lock = QLockFile(QDir.temp().absoluteFilePath(f"{APP_ID}.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(200):
        return  # already running
    migrate_legacy()
    refresh_startup_path()
    w = WinSlide()
    w.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
