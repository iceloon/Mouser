"""Logitech Spotlight presenter support.

The Spotlight is not a HID++ mouse: it presents itself as a plain keyboard
(Left/Right arrows for previous/next) plus a plain mouse (BTN_LEFT + motion
while the pointer key is held).  It therefore cannot be driven through
Mouser's REPROG_CONTROLS diversion path -- it needs its own small input
layer, which lives here.

Two pieces:

* :class:`PresenterWatcher` -- Windows Raw Input on the mouse collections.
  Raw Input reports the *device* that produced each event, so we can light
  the spotlight overlay only when the presenter's pointer key is pressed,
  without touching normal left clicks.
* :class:`PresenterKeyHook` -- optional low-level keyboard hook that takes
  over the Left/Right arrows while enabled.  Windows' low-level hook has no
  device attribution, so this one is global and strictly opt-in.

Everything is defensive: without hidapi/Windows the module degrades to
"presenter not connected" and never raises into the app.
"""
from __future__ import annotations

import ctypes
import sys
import threading

#: USB / Bluetooth product IDs Logitech ships for the Spotlight family.
PRESENTER_PRODUCT_IDS = {
    0xC53E: ("Logitech Spotlight", "usb"),
    0xB503: ("Logitech Spotlight", "bluetooth"),
    0xC548: ("Logitech Spotlight 2", "usb"),
    0xB506: ("Logitech Spotlight 2", "bluetooth"),
}

#: Raw Input virtual-key codes the presenter sends for its two buttons.
VK_LEFT_ARROW = 0x25
VK_RIGHT_ARROW = 0x27

_PRESENTER_PID_TAGS = tuple(f"{pid:04x}" for pid in PRESENTER_PRODUCT_IDS)


def presenter_for_product_id(product_id):
    """Return ``(display_name, transport)`` for a Logitech product id."""
    return PRESENTER_PRODUCT_IDS.get(int(product_id))


def is_presenter_pid(product_id):
    return int(product_id) in PRESENTER_PRODUCT_IDS


def is_presenter_device_name(name: str) -> bool:
    """True when a Raw Input / HID device path belongs to a presenter.

    Windows writes USB paths as ``VID_046D&PID_C53E`` and Bluetooth paths as
    ``VID&02046d_PID&1b503``, so matching is done on a normalised string.
    """
    if not name:
        return False
    lowered = name.lower().replace("_", "").replace("&", "").replace("#", "")
    if "046d" not in lowered:
        return False
    return any(tag in lowered for tag in _PRESENTER_PID_TAGS)


def detect_connected_presenter():
    """Scan HID devices for a connected presenter.

    Returns ``dict`` with ``product_id``, ``name``, ``transport`` and
    ``path_count`` or ``None`` when nothing is plugged in.
    """
    try:
        import hid  # type: ignore
    except Exception:
        return None
    try:
        infos = hid.enumerate(0x046D, 0)
    except Exception:
        return None

    found = {}
    for info in infos or []:
        pid = info.get("product_id")
        meta = presenter_for_product_id(pid) if pid is not None else None
        if not meta:
            continue
        entry = found.setdefault(pid, {
            "product_id": pid,
            "name": meta[0],
            "transport": meta[1],
            "path_count": 0,
        })
        entry["path_count"] += 1
    if not found:
        return None
    # Prefer USB (direct) over Bluetooth when both are around.
    for entry in found.values():
        if entry["transport"] == "usb":
            return entry
    return next(iter(found.values()))


# ---------------------------------------------------------------------------
# Windows Raw Input watcher (pointer key)
# ---------------------------------------------------------------------------

if sys.platform == "win32":  # pragma: no cover - platform specific

    from ctypes import wintypes as wt

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    WM_INPUT = 0x00FF
    WM_QUIT = 0x0012
    WM_CLOSE = 0x0010
    RIDEV_INPUTSINK = 0x00000100
    RID_INPUT = 0x10000003
    RIM_TYPEMOUSE = 0
    RIDI_DEVICENAME = 0x20000007
    HWND_MESSAGE = wt.HWND(-3)

    class RAWINPUTDEVICE(ctypes.Structure):
        _fields_ = [
            ("usUsagePage", wt.USHORT),
            ("usUsage", wt.USHORT),
            ("dwFlags", wt.DWORD),
            ("hwndTarget", wt.HWND),
        ]

    class RAWINPUTHEADER(ctypes.Structure):
        _fields_ = [
            ("dwType", wt.DWORD),
            ("dwSize", wt.DWORD),
            ("hDevice", wt.HANDLE),
            ("wParam", wt.WPARAM),
        ]

    class RAWMOUSE(ctypes.Structure):
        _fields_ = [
            ("usFlags", wt.USHORT),
            ("ulButtons", wt.ULONG),
            ("usButtonFlags", wt.USHORT),
            ("usButtonData", wt.USHORT),
            ("ulRawButtons", wt.ULONG),
            ("lLastX", wt.LONG),
            ("lLastY", wt.LONG),
            ("ulExtraInformation", wt.ULONG),
        ]

    RI_MOUSE_LEFT_BUTTON_DOWN = 0x0001
    RI_MOUSE_LEFT_BUTTON_UP = 0x0002

    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class PresenterWatcher:
    """Watch Raw Input for the presenter's pointer key.

    ``on_pointer(down: bool)`` is called from the watcher thread.
    """

    def __init__(self, on_pointer=None):
        self._on_pointer = on_pointer
        self._thread = None
        self._thread_id = None
        self._ready = threading.Event()
        self._running = False
        self._hwnd = None
        self._wndproc = None
        self._names = {}
        self._last_down = False

    # -- public API ---------------------------------------------------
    def start(self, timeout=2.0):
        if sys.platform != "win32":
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._ready.clear()
        self._thread = threading.Thread(target=self._run, name="PresenterWatcher",
                                        daemon=True)
        self._thread.start()
        return self._ready.wait(timeout)

    def stop(self):
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread:
            self._thread.join(timeout=1.5)
        self._thread = None
        self._thread_id = None
        self._running = False

    def _emit(self, down):
        if down == self._last_down:
            return
        self._last_down = down
        cb = self._on_pointer
        if cb is None:
            return
        try:
            cb(down)
        except Exception:
            pass

    # -- internals ----------------------------------------------------
    def _device_name(self, hdevice):
        key = hdevice or 0
        cached = self._names.get(key)
        if cached is not None:
            return cached
        size = wt.UINT(0)
        user32.GetRawInputDeviceInfoW(hdevice, RIDI_DEVICENAME, None, ctypes.byref(size))
        name = ""
        if size.value:
            buf = ctypes.create_unicode_buffer(size.value)
            if user32.GetRawInputDeviceInfoW(hdevice, RIDI_DEVICENAME, buf,
                                             ctypes.byref(size)) > 0:
                name = buf.value or ""
        self._names[key] = name
        return name

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            try:
                self._handle_raw(lparam)
            except Exception:
                pass
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _handle_raw(self, lparam):
        size = wt.UINT(0)
        user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size),
                               ctypes.sizeof(RAWINPUTHEADER))
        if not size.value:
            return
        buf = ctypes.create_string_buffer(size.value)
        if user32.GetRawInputData(lparam, RID_INPUT, buf, ctypes.byref(size),
                                  ctypes.sizeof(RAWINPUTHEADER)) != size.value:
            return
        header = RAWINPUTHEADER.from_buffer_copy(buf)
        if header.dwType != RIM_TYPEMOUSE:
            return
        if not is_presenter_device_name(self._device_name(header.hDevice)):
            return
        mouse = RAWMOUSE.from_buffer_copy(buf, ctypes.sizeof(RAWINPUTHEADER))
        if mouse.usButtonFlags & RI_MOUSE_LEFT_BUTTON_DOWN:
            self._emit(True)
        if mouse.usButtonFlags & RI_MOUSE_LEFT_BUTTON_UP:
            self._emit(False)

    def _run(self):
        try:
            self._thread_id = kernel32.GetCurrentThreadId()
            self._wndproc = WNDPROC(self._wnd_proc)
            hinstance = kernel32.GetModuleHandleW(None)
            class_name = "MouserPresenterWatcher"
            wc = wt.WNDCLASSW()
            wc.lpfnWndProc = self._wndproc
            wc.hInstance = hinstance
            wc.lpszClassName = class_name
            user32.RegisterClassW(ctypes.byref(wc))
            self._hwnd = user32.CreateWindowExW(
                0, class_name, "MouserPresenterWatcher", 0, 0, 0, 0, 0,
                HWND_MESSAGE, None, hinstance, None)
            if not self._hwnd:
                self._ready.set()
                return
            device = RAWINPUTDEVICE()
            device.usUsagePage = 0x01
            device.usUsage = 0x02
            device.dwFlags = RIDEV_INPUTSINK
            device.hwndTarget = self._hwnd
            ok = user32.RegisterRawInputDevices(ctypes.byref(device), 1,
                                                ctypes.sizeof(RAWINPUTDEVICE))
            self._running = bool(ok)
            self._ready.set()
            if not ok:
                return
            msg = wt.MSG()
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            try:
                if self._hwnd:
                    user32.DestroyWindow(self._hwnd)
                    self._hwnd = None
            except Exception:
                pass
            self._ready.set()


# ---------------------------------------------------------------------------
# Optional keyboard takeover
# ---------------------------------------------------------------------------

class PresenterKeyHook:
    """Swallow Left/Right arrows while enabled and report them as next/prev.

    Windows cannot attribute low-level keyboard events to a device, so this
    is global and opt-in; the caller decides when to enable it (e.g. only
    while a slideshow app is in the foreground).
    """

    def __init__(self, on_next=None, on_prev=None):
        self._on_next = on_next
        self._on_prev = on_prev
        self._hook = None
        self._thread = None
        self._thread_id = None
        self._proc = None
        self._enabled = False

    @property
    def enabled(self):
        return self._enabled

    def set_enabled(self, value):
        self._enabled = bool(value)

    def start(self):
        if sys.platform != "win32" or self._thread:
            return bool(self._thread)
        self._thread = threading.Thread(target=self._run, name="PresenterKeyHook",
                                        daemon=True)
        self._thread.start()
        return True

    def stop(self):
        if self._thread_id:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        self._thread = None
        self._thread_id = None

    def _fire(self, callback):
        """Return True when the callback handled (and wants to swallow) the key."""
        if callback is None:
            return False
        try:
            return bool(callback())
        except Exception:
            return False

    def _proc_impl(self, n_code, w_param, l_param):
        try:
            if n_code == 0 and self._enabled and w_param in (0x0100, 0x0104):
                kb = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if kb.vkCode == VK_RIGHT_ARROW and self._fire(self._on_next):
                    return 1
                if kb.vkCode == VK_LEFT_ARROW and self._fire(self._on_prev):
                    return 1
        except Exception:
            pass
        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    def _run(self):
        self._thread_id = kernel32.GetCurrentThreadId()
        self._proc = HOOKPROC(self._proc_impl)
        self._hook = user32.SetWindowsHookExW(13, self._proc, None, 0)
        msg = wt.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))


if sys.platform == "win32":  # pragma: no cover - platform specific

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", wt.DWORD),
            ("scanCode", wt.DWORD),
            ("flags", wt.DWORD),
            ("time", wt.DWORD),
            ("dwExtraInfo", ctypes.c_size_t),
        ]

    HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                                  wt.WPARAM, wt.LPARAM)
