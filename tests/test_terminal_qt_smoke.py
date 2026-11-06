"""Offscreen Qt painting smoke tests for the NOSTROMO.VID terminal chrome."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication

from terminal_theme import THEME_CHOICES, palette, paint_terminal_chrome


class QtTerminalSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_chrome_renders_for_all_terminal_colorways(self):
        for theme in THEME_CHOICES:
            if theme == "Original":
                continue
            with self.subTest(theme=theme):
                image = QImage(480, 320, QImage.Format_ARGB32)
                image.fill(QColor("#112233"))
                painter = QPainter(image)
                paint_terminal_chrome(painter, 480, 320, theme,
                                      "TEST.SYS", "READY", "MU/TH/UR 6000 // TEST")
                painter.end()
                self.assertEqual(image.pixelColor(100, 10), QColor(palette(theme)["panel"]))
                self.assertEqual(image.pixelColor(100, 308), QColor(palette(theme)["dark"]))
                self.assertEqual(image.pixelColor(100, 150), QColor("#112233"))

    def test_chrome_does_not_paint_in_original_mode(self):
        image = QImage(480, 320, QImage.Format_ARGB32)
        image.fill(QColor("#112233"))
        painter = QPainter(image)
        paint_terminal_chrome(painter, 480, 320, "Original", "TEST.SYS", "READY", "TEST")
        painter.end()
        self.assertEqual(image.pixelColor(100, 10), QColor("#112233"))


if __name__ == "__main__":
    unittest.main()
