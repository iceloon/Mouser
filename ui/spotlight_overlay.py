"""Screen spotlight overlay for presentations.

Draws a click-through, always-on-top shade over the screen under the cursor
with a soft circular hole (the "spotlight") or a laser dot, following the
mouse cursor.  This is the Mouser equivalent of the Logitech Spotlight
highlight effect -- it does not need Logi Options+ and works with any
pointing device, including a Spotlight presenter in its plug-and-play mode.

The widget is intentionally self-contained: :class:`ui.backend.Backend` owns
the instance and pushes style settings into it, the engine only says
"show" / "hide".
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QWidget

#: Cursor polling interval -- 16 ms keeps the spot glued to the pointer
#: without burning a core; repaints are skipped when the cursor did not move.
_TICK_MS = 16

#: Safety net: never leave a shade on screen if the UP event was lost.
_MAX_ACTIVE_MS = 30 * 60 * 1000

MODE_SPOTLIGHT = "spotlight"
MODE_LASER = "laser"
VALID_MODES = (MODE_SPOTLIGHT, MODE_LASER)


def _clamp(value, low, high):
    return max(low, min(high, value))


class SpotlightOverlay(QWidget):
    """Full-screen click-through spotlight that follows the mouse cursor."""

    active_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowTransparentForInput
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setWindowTitle("Mouser Spotlight")

        # Style -- overridden through configure().
        self._radius = 220
        self._dim = 0.55
        self._mode = MODE_SPOTLIGHT
        self._color = QColor("#ffffff")
        self._ring_width = 3
        self._hide_cursor = False

        self._active = False
        self._cursor_pos = QCursor.pos()
        self._screen = None
        self._guard = QTimer(self)
        self._guard.setSingleShot(True)
        self._guard.setInterval(_MAX_ACTIVE_MS)
        self._guard.timeout.connect(self.hide_overlay)

        self._ticker = QTimer(self)
        self._ticker.setInterval(_TICK_MS)
        self._ticker.timeout.connect(self._tick)

    # ── public API ─────────────────────────────────────────────────

    def configure(self, *, radius=None, dim=None, mode=None, color=None,
                  ring_width=None, hide_cursor=None) -> None:
        """Apply style settings; values that are ``None`` are left alone."""
        if radius is not None:
            self._radius = int(_clamp(int(radius), 20, 2000))
        if dim is not None:
            self._dim = float(_clamp(float(dim), 0.0, 0.95))
        if mode is not None and mode in VALID_MODES:
            self._mode = mode
        if color is not None:
            parsed = QColor(color)
            if parsed.isValid():
                self._color = parsed
        if ring_width is not None:
            self._ring_width = int(_clamp(int(ring_width), 0, 12))
        if hide_cursor is not None:
            self._hide_cursor = bool(hide_cursor)
        if self._active:
            self.update()

    @property
    def active(self) -> bool:
        return self._active

    @property
    def radius(self) -> int:
        return self._radius

    @property
    def dim(self) -> float:
        return self._dim

    @property
    def mode(self) -> str:
        return self._mode

    def color_name(self) -> str:
        return self._color.name()

    @property
    def ring_width(self) -> int:
        return self._ring_width

    @property
    def hide_cursor(self) -> bool:
        return self._hide_cursor

    def show_overlay(self) -> None:
        if self._active:
            return
        self._cursor_pos = QCursor.pos()
        self._sync_screen()
        self._active = True
        self.raise_()
        self.show()
        self._ticker.start()
        self._guard.start()
        self.update()
        self.active_changed.emit(True)

    def hide_overlay(self) -> None:
        if not self._active:
            return
        self._active = False
        self._ticker.stop()
        self._guard.stop()
        self.hide()
        self.active_changed.emit(False)

    def toggle(self) -> bool:
        """Flip visibility; returns the new active state."""
        if self._active:
            self.hide_overlay()
        else:
            self.show_overlay()
        return self._active

    # ── internals ──────────────────────────────────────────────────

    def _screen_at(self, pos):
        screen = QGuiApplication.screenAt(pos)
        if screen is None:
            screens = QGuiApplication.screens()
            screen = screens[0] if screens else None
        return screen

    def _sync_screen(self, pos=None) -> bool:
        """Move the overlay to the screen holding *pos*.  Returns True on change."""
        screen = self._screen_at(self._cursor_pos if pos is None else pos)
        if screen is None:
            return False
        if screen is self._screen and self.geometry() == screen.geometry():
            return False
        self._screen = screen
        self.setGeometry(screen.geometry())
        return True

    def _tick(self) -> None:
        if not self._active:
            return
        pos = QCursor.pos()
        if pos == self._cursor_pos:
            return
        self._cursor_pos = pos
        self._sync_screen(pos)
        self.update()

    def _local_pos(self) -> QPointF:
        origin = self.geometry().topLeft()
        return QPointF(self._cursor_pos.x() - origin.x(),
                       self._cursor_pos.y() - origin.y())

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        center = self._local_pos()
        radius = float(self._radius)

        if self._mode == MODE_LASER:
            self._paint_laser(painter, center)
        else:
            self._paint_spotlight(painter, center, radius)
        painter.end()

    # ── painting helpers ───────────────────────────────────────────

    def _paint_spotlight(self, painter: QPainter, center: QPointF,
                         radius: float) -> None:
        rect = QRectF(self.rect())

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, int(round(self._dim * 255))))
        painter.drawRect(rect)
        painter.restore()

        # Feather the hole so the edge reads as light falloff, not a hard
        # stencil: paint a white radial gradient in DestinationOut mode.
        painter.save()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        feather = max(6.0, radius * 0.12)
        gradient = QRadialGradient(center, radius + feather)
        gradient.setColorAt(0.0, QColor(255, 255, 255, 255))
        gradient.setColorAt(radius / (radius + feather), QColor(255, 255, 255, 255))
        gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius + feather, radius + feather)
        painter.restore()

        if self._ring_width > 0:
            ring = QColor(self._color)
            ring.setAlpha(235)
            painter.save()
            painter.setBrush(Qt.BrushStyle.NoBrush)
            pen = QPen(ring)
            pen.setWidthF(float(self._ring_width))
            painter.setPen(pen)
            painter.drawEllipse(center, radius, radius)
            painter.restore()

    def _paint_laser(self, painter: QPainter, center: QPointF) -> None:
        dot = 9.0
        halo = QRadialGradient(center, dot * 4.0)
        base = QColor(self._color)
        glow = QColor(base)
        glow.setAlpha(90)
        base.setAlpha(255)
        halo.setColorAt(0.0, base)
        halo.setColorAt(0.35, base)
        halo.setColorAt(1.0, glow)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(halo)
        painter.drawEllipse(center, dot * 4.0, dot * 4.0)
        painter.restore()

        painter.save()
        painter.setBrush(base)
        painter.setPen(QPen(QColor(255, 255, 255, 120), 1.0))
        painter.drawEllipse(center, dot, dot)
        painter.restore()
