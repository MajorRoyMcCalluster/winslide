"""NOSTROMO.SUITE link contract tests (protocol parts need no Qt)."""
import pathlib
import unittest

from winslide_app import suite_link
from winslide_app.suite_link import SUITE_THEMES, clip_readout, decode, encode, from_argv

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SuiteArgsTests(unittest.TestCase):
    def test_standalone_has_no_suite(self):
        self.assertIsNone(from_argv(["winslide.py"]))
        self.assertIsNone(from_argv(["winslide.py", "--suite-theme", "red"]))

    def test_suite_flags(self):
        a = from_argv(["x", "--suite-pipe", "nostromo-suite-matt", "--suite-theme", "phosphor"])
        self.assertEqual((a.pipe, a.theme), ("nostromo-suite-matt", "phosphor"))
        b = from_argv(["x", "--suite-pipe=p1", "--suite-theme=mono"])
        self.assertEqual((b.pipe, b.theme), ("p1", "mono"))

    def test_unknown_theme_falls_back_and_bad_pipe_rejected(self):
        self.assertEqual(from_argv(["x", "--suite-pipe", "p", "--suite-theme", "retrowave"]).theme, "amber")
        self.assertIsNone(from_argv(["x", "--suite-pipe", "..\\..\\evil pipe"]))


class ProtocolTests(unittest.TestCase):
    def test_round_trip(self):
        raw = encode("readout", text="CPU 39° GPU 45°")
        self.assertTrue(raw.endswith(b"\n"))
        msg = decode(raw)
        self.assertEqual(msg["t"], "readout")
        self.assertEqual(msg["text"], "CPU 39° GPU 45°")
        self.assertEqual(msg["v"], suite_link.PROTOCOL)

    def test_garbage_is_ignored(self):
        for bad in (b"", b"{", b"[1,2]", b'{"x":1}', b"\xff\xfe", b"a" * (suite_link.MAX_LINE + 1)):
            self.assertIsNone(decode(bad))

    def test_readout_is_one_short_line(self):
        self.assertEqual(clip_readout("  CPU\n39°  "), "CPU 39°")
        self.assertLessEqual(len(clip_readout("x" * 200)), suite_link.READOUT_MAX)

    def test_four_suite_themes(self):
        self.assertEqual(SUITE_THEMES, ("amber", "phosphor", "red", "mono"))


class SuiteHooksTests(unittest.TestCase):
    """The app source keeps its suite hooks (guards against a careless merge)."""

    def setUp(self):
        self.src = (ROOT / "winslide_app" / "app.py").read_text(encoding="utf-8")

    def test_hooks_present(self):
        for needle in ("SUITE = suite_link.from_argv(sys.argv)", "def suite_readout(self)",
                       "_attach_suite(w)\n", "SUITE_LINK.bye()", "suite_link.adapt_menu(m)", "def apply_suite_theme(self, name)",
                       "if SUITE is not None:  # NOSTROMO.SUITE owns the only tray icon"):
            self.assertIn(needle, self.src)

    def test_every_suite_theme_maps_to_a_real_palette(self):
        from winslide_app.terminal_theme import THEME_CHOICES as TERMINAL_NAMES
        import ast
        start = self.src.index("SUITE_THEME_MAP = ") + len("SUITE_THEME_MAP = ")
        mapping = ast.literal_eval(self.src[start:self.src.index("}", start) + 1])
        self.assertEqual(set(mapping), set(SUITE_THEMES))
        self.assertTrue(set(mapping.values()) <= set(TERMINAL_NAMES))

    def test_entry_shim_imports_package(self):
        shim = (ROOT / "winslide.py").read_text(encoding="utf-8")
        self.assertIn("from winslide_app.app import main", shim)


if __name__ == "__main__":
    unittest.main()
