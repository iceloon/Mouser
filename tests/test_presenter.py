"""Tests for the Logitech Spotlight presenter layer (platform independent parts)."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.config import DEFAULT_CONFIG
from core.presenter import (
    PRESENTER_PRODUCT_IDS,
    is_presenter_device_name,
    is_presenter_pid,
    presenter_for_product_id,
)


class PresenterCatalogTests(unittest.TestCase):
    def test_known_product_ids(self):
        self.assertEqual(presenter_for_product_id(0xC53E), ("Logitech Spotlight", "usb"))
        self.assertEqual(presenter_for_product_id(0xB503), ("Logitech Spotlight", "bluetooth"))
        self.assertEqual(presenter_for_product_id(0xC548), ("Logitech Spotlight 2", "usb"))
        self.assertEqual(presenter_for_product_id(0xB506), ("Logitech Spotlight 2", "bluetooth"))

    def test_unknown_product_id(self):
        self.assertIsNone(presenter_for_product_id(0xB034))
        self.assertFalse(is_presenter_pid(0xB034))
        self.assertTrue(is_presenter_pid(0xC53E))

    def test_device_name_matching(self):
        usb = (r"\\?\HID#VID_046D&PID_C53E&MI_01&Col01#8&3a0c797a&0&0000"
               r"#{4d1e55b2-f16f-11cf-88cb-001111000030}")
        bt = (r"\\?\HID#{00001812-0000-1000-8000-00805f9b34fb}_Dev_VID&02046d"
              r"_PID&1b503_REV&0001#9&2f0e2b1c&0&0000")
        mouse = (r"\\?\HID#VID_046D&PID_B034&MI_02&Col01#8&1111&0&0000"
                 r"#{4d1e55b2-f16f-11cf-88cb-001111000030}")
        self.assertTrue(is_presenter_device_name(usb))
        self.assertTrue(is_presenter_device_name(bt))
        self.assertFalse(is_presenter_device_name(mouse))
        self.assertFalse(is_presenter_device_name(""))
        self.assertFalse(is_presenter_device_name(None))

    def test_all_ids_are_logitech(self):
        self.assertTrue(all(pid > 0 for pid in PRESENTER_PRODUCT_IDS))


class PresenterConfigTests(unittest.TestCase):
    def test_defaults_exist(self):
        settings = DEFAULT_CONFIG["settings"]
        self.assertIn("presenter_enabled", settings)
        self.assertIn("presenter_pointer_overlay", settings)
        self.assertIn("presenter_takeover_keys", settings)
        self.assertFalse(settings["presenter_takeover_keys"],
                         "arrow-key takeover must stay opt-in")

    def test_mapping_keys_exist(self):
        mappings = DEFAULT_CONFIG["profiles"]["default"]["mappings"]
        self.assertEqual(mappings["presenter_next"], "none")
        self.assertEqual(mappings["presenter_prev"], "none")


class _FakeMouseHook:
    def __init__(self):
        self.invert_vscroll = False
        self.invert_hscroll = False
        self.debug_mode = False
        self.connected_device = None
        self.device_connected = False
        self._hid_gesture = None
        self.wheel_native_invert_active = False
        self.wheel_divert_active = False

    def set_debug_callback(self, cb): pass
    def set_gesture_callback(self, cb): pass
    def set_status_callback(self, cb): pass
    def set_connection_change_callback(self, cb): pass
    def set_battery_notify_callback(self, cb): pass
    def configure_gestures(self, **kwargs): pass
    def configure_wheel_multipliers(self, v, h): pass
    def block(self, event_type): pass
    def register(self, event_type, callback): pass
    def reset_bindings(self): pass
    def start(self): pass
    def stop(self): pass


class _FakeAppDetector:
    def __init__(self, callback): self.callback = callback
    def start(self): pass
    def stop(self): pass


class PresenterEngineTests(unittest.TestCase):
    def _make_engine(self, mappings=None, settings=None):
        from core.engine import Engine

        cfg = copy.deepcopy(DEFAULT_CONFIG)
        if mappings:
            cfg["profiles"]["default"]["mappings"].update(mappings)
        if settings:
            cfg["settings"].update(settings)
        with (
            patch("core.engine.MouseHook", _FakeMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.load_config", return_value=cfg),
        ):
            engine = Engine()
        engine._spotlight_cb = None
        return engine

    def test_presenter_settings_defaults(self):
        engine = self._make_engine()
        self.assertEqual(engine._presenter_settings(), {
            "enabled": True,
            "pointer_overlay": True,
            "takeover_keys": False,
        })

    def test_unmapped_presenter_button_passes_through(self):
        engine = self._make_engine()
        self.assertFalse(engine._dispatch_presenter_action("presenter_next"))

    def test_mapped_presenter_button_dispatches(self):
        engine = self._make_engine(mappings={"presenter_next": "copy"})
        seen = []
        with patch("core.engine.execute_action", side_effect=seen.append):
            self.assertTrue(engine._dispatch_presenter_action("presenter_next"))
        self.assertEqual(seen, ["copy"])

    def test_pointer_emits_spotlight_show_and_hide(self):
        engine = self._make_engine()
        seen = []
        engine.set_spotlight_callback(seen.append)
        engine._on_presenter_pointer(True)
        engine._on_presenter_pointer(False)
        self.assertEqual(seen, ["show", "hide"])

    def test_pointer_respects_overlay_toggle(self):
        engine = self._make_engine(settings={"presenter_pointer_overlay": False})
        seen = []
        engine.set_spotlight_callback(seen.append)
        engine._on_presenter_pointer(True)
        self.assertEqual(seen, [])

    def test_presenter_state_callback_is_used(self):
        engine = self._make_engine()
        seen = []
        engine.set_presenter_state_callback(seen.append)
        engine._emit_presenter_state({"name": "Logitech Spotlight"})
        self.assertEqual(seen, [{"name": "Logitech Spotlight"}])

    def test_sync_without_device_stops_runtime(self):
        engine = self._make_engine()
        engine._sync_presenter_runtime(None)
        self.assertIsNone(engine._presenter_watcher)
        self.assertIsNone(engine._presenter_key_hook)


if __name__ == "__main__":
    unittest.main()
