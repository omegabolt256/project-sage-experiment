from __future__ import annotations

from sage.events.voice_event import EventType, event_bus


class KeyboardWake:
    def __init__(self, hotkey="f8"):
        self.hotkey = hotkey
        self._hook = None
        self._running = False

    def start(self):
        if self._running:
            return

        import keyboard

        self._running = True

        self._hook = keyboard.add_hotkey(
            self.hotkey,
            self._trigger,
            trigger_on_release=True,
        )

        print(
            f"[Sage] Keyboard wake enabled: {self.hotkey!r}"
        )

    def _trigger(self):
        if not self._running:
            return

        # Let the Warden decide whether this wake is accepted.
        event_bus.emit(
            EventType.WAKE_DETECTED,
            {"source": "keyboard"},
        )

    def stop(self):
        if not self._running:
            return

        import keyboard

        if self._hook is not None:
            keyboard.remove_hotkey(self._hook)

        self._hook = None
        self._running = False
