"""Regression checks for the NOSTROMO.VID appearance contract.

These deliberately avoid PySide6, codecs, network services and desktop state.
"""
import unittest

from terminal_theme import COLORWAYS, THEME_CHOICES, menu_stylesheet, palette


class TerminalThemeTests(unittest.TestCase):
    def test_vid_colorways_match_reference(self):
        self.assertEqual(COLORWAYS["Amber"]["accent"], "#e8b65e")
        self.assertEqual(COLORWAYS["Phosphor"]["dark"], "#07120c")
        self.assertEqual(COLORWAYS["Monochrome"]["hi"], "#f2f5eb")

    def test_original_mode_is_noninvasive(self):
        self.assertIsNone(palette("Original"))
        self.assertEqual(menu_stylesheet("Original"), "")

    def test_every_theme_has_complete_tokens(self):
        required = {"accent", "hi", "muted", "edge", "dark", "panel", "button"}
        for name in THEME_CHOICES:
            if name == "Original":
                continue
            with self.subTest(theme=name):
                tokens = palette(name)
                self.assertEqual(set(tokens), required)
                self.assertTrue(all(v.startswith("#") and len(v) == 7 for v in tokens.values()))
                self.assertIn(tokens["accent"], menu_stylesheet(name))

    def test_palette_returns_defensive_copy(self):
        changed = palette("Amber")
        changed["accent"] = "#000000"
        self.assertEqual(palette("Amber")["accent"], "#e8b65e")

    def test_invalid_palette_is_not_silently_accepted(self):
        with self.assertRaises(ValueError):
            palette("does-not-exist")


if __name__ == "__main__":
    unittest.main()
