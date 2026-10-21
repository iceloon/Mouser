"""Tests for the presentation spotlight action wiring.

The overlay widget itself is Qt-only and is exercised in
``test_spotlight_overlay.py``; these tests stay headless and cover the
engine-side plumbing plus the action registry.
"""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core.config import DEFAULT_CONFIG
from core.key_simulator import ACTIONS
from core.mouse_hook import MouseEvent


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
        self.blocked = []
        self.registered = []

    # callback registration surface used by Engine
    def set_debug_callback(self, cb): self._debug_callback = cb
    def set_gesture_callback(self, cb): self._gesture_callback = cb
    def set_status_callback(self, cb): self._status_callback = cb
    def set_connection_change_callback(self, cb): self._connection_change_callback = cb
    def set_battery_notify_callback(self, cb): self._battery_notify_callback = cb
    def configure_gestures(self, **kwargs): self._gesture_config = kwargs
    def configure_wheel_multipliers(self, vertical, horizontal): return None

    def block(self, event_type):
        self.blocked.append(event_type)

    def register(self, event_type, callback):
        self.registered.append((event_type, callback))

    def reset_bindings(self):
        self.blocked = []
        self.registered = []

    def start(self): pass
    def stop(self): pass


class _FakeAppDetector:
    def __init__(self, callback):
        self.callback = callback

    def start(self): pass
    def stop(self): pass


class SpotlightActionTests(unittest.TestCase):
    def _make_engine(self, mappings=None):
        from core.engine import Engine

        cfg = copy.deepcopy(DEFAULT_CONFIG)
        if mappings:
            cfg["profiles"]["default"]["mappings"].update(mappings)

        with (
            patch("core.engine.MouseHook", _FakeMouseHook),
            patch("core.engine.AppDetector", _FakeAppDetector),
            patch("core.engine.load_config", return_value=cfg),
        ):
            return Engine()

    def test_actions_are_registered_for_the_pickers(self):
        for action_id in ("spotlight_hold", "spotlight_toggle"):
            self.assertIn(action_id, ACTIONS)
            self.assertEqual(ACTIONS[action_id]["category"], "Presentation")
            self.assertEqual(ACTIONS[action_id]["keys"], [])
            self.assertTrue(ACTIONS[action_id]["label"])

    def test_dispatch_toggle_emits_toggle(self):
        engine = self._make_engine()
        seen = []
        engine.set_spotlight_callback(seen.append)

        engine._dispatch_action("spotlight_toggle")

        self.assertEqual(seen, ["toggle"])

    def test_dispatch_hold_on_single_fire_control_shows(self):
        engine = self._make_engine()
        seen = []
        engine.set_spotlight_callback(seen.append)

        engine._dispatch_action("spotlight_hold")

        self.assertEqual(seen, ["show"])

    def test_hold_handlers_show_on_press_and_hide_on_release(self):
        engine = self._make_engine()
        seen = []
        engine.set_spotlight_callback(seen.append)

        down = engine._make_spotlight_down_handler()
        up = engine._make_spotlight_up_handler()
        down(SimpleNamespace(event_type=MouseEvent.XBUTTON2_DOWN, raw_data=None))
        up(SimpleNamespace(event_type=MouseEvent.XBUTTON2_UP, raw_data=None))

        self.assertEqual(seen, ["show", "hide"])

    def test_hold_mapping_registers_press_and_release(self):
        engine = self._make_engine(mappings={"xbutton2": "spotlight_hold"})
        hook = engine.hook
        hook.reset_bindings()

        engine._setup_hooks()

        down_events = [e for e, _ in hook.registered if e.endswith("_down")]
        up_events = [e for e, _ in hook.registered if e.endswith("_up")]
        self.assertTrue(down_events, "press handler was not registered")
        self.assertTrue(up_events, "release handler was not registered")
        self.assertIn(MouseEvent.XBUTTON2_DOWN, hook.blocked)
        self.assertIn(MouseEvent.XBUTTON2_UP, hook.blocked)

    def test_callback_errors_do_not_escape(self):
        engine = self._make_engine()

        def boom(_action):
            raise RuntimeError("nope")

        engine.set_spotlight_callback(boom)
        engine._dispatch_action("spotlight_toggle")  # must not raise


if __name__ == "__main__":
    unittest.main()
