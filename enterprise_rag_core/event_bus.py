from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[Callable]] = {}

    def on(self, event_type: str):
        def decorator(func: Callable) -> Callable:
            self._handlers.setdefault(event_type, []).append(func)
            return func
        return decorator

    def emit(self, event_type: str, **payload: Any) -> None:
        payload.setdefault("_timestamp", datetime.now(timezone.utc).isoformat())
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event_type, payload)
            except Exception as e:
                print(f"[EventBus] Handler error for '{event_type}': {e}")


_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
