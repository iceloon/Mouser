"""Qt smoke tests for the spotlight overlay.

Skipped when PySide6 is not importable in the current interpreter so the
headless engine suite still runs on machines without Qt installed.
"""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from ui.spotlight_overlay import MODE_LASER, MODE_SPOTLIGHT, SpotlightOverlay

    _HAS_QT = True
except Exception:  # pragma: no cover - depends on the local environment
    _HAS_QT = False


@unittest.skipUnless(_HAS_QT, "PySide6 is not available")
class SpotlightOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _overlay(self):
        overlay = SpotlightOverlay()
        self.addCleanup(overlay.deleteLater)
        return overlay

    def test_defaults(self):
        overlay = self._overlay()
        self.assertEqual(overlay.mode, MODE_SPOTLIGHT)
        self.assertGreater(overlay.radius, 0)
        self.assertFalse(overlay.active)

    def test_configure_clamps_and_filters(self):
        overlay = self._overlay()
        overlay.configure(radius=99999, dim=4.0, ring_width=99)
        self.assertLessEqual(overlay.radius, 2000)
        self.assertLessEqual(overlay.dim, 0.95)
        self.assertLessEqual(overlay.ring_width, 12)

        overlay.configure(mode="nonsense", color="not-a-colour")
        self.assertEqual(overlay.mode, MODE_SPOTLIGHT)
        self.assertNotEqual(overlay.color_name(), "")

        overlay.configure(mode=MODE_LASER, color="#ff0000")
        self.assertEqual(overlay.mode, MODE_LASER)
        self.assertEqual(overlay.color_name(), "#ff0000")

    def test_show_and_hide_emit_state(self):
        overlay = self._overlay()
        states = []
        overlay.active_changed.connect(states.append)

        overlay.show_overlay()
        self.assertTrue(overlay.active)
        overlay.show_overlay()  # idempotent
        overlay.hide_overlay()
        overlay.hide_overlay()  # idempotent

        self.assertFalse(overlay.active)
        self.assertEqual(states, [True, False])

    def test_toggle_returns_new_state(self):
        overlay = self._overlay()
        self.assertTrue(overlay.toggle())
        self.assertFalse(overlay.toggle())

    def test_paints_without_raising(self):
        overlay = self._overlay()
        overlay.configure(radius=180, dim=0.5, ring_width=4)
        overlay.show_overlay()
        self.app.processEvents()

        pixmap = overlay.grab()
        self.assertFalse(pixmap.isNull())

        overlay.configure(mode=MODE_LASER)
        self.app.processEvents()
        self.assertFalse(overlay.grab().isNull())
        overlay.hide_overlay()

    def test_paints_on_every_available_screen(self):
        from PySide6.QtGui import QGuiApplication

        overlay = self._overlay()
        overlay.show_overlay()
        self.app.processEvents()
        screens = QGuiApplication.screens() or []
        for screen in screens:
            self.assertEqual(overlay.geometry(), screen.geometry())
            break
        overlay.hide_overlay()


if __name__ == "__main__":
    unittest.main()
