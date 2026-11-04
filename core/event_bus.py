from __future__ import annotations

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Any

_LOG = logging.getLogger(__name__)
EventHandler = Callable[..., None]


class EventBus:
    """Small thread-safe in-process event bus.

    Handlers are copied while holding the lock and called outside it, so a handler
    may safely subscribe or unsubscribe while an event is being delivered.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        with self._lock:
            if handler not in self._handlers[event_name]:
                self._handlers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        with self._lock:
            handlers = self._handlers.get(event_name, [])
            if handler in handlers:
                handlers.remove(handler)

    def publish(self, event_name: str, **payload: Any) -> None:
        with self._lock:
            handlers = tuple(self._handlers.get(event_name, ()))
        for handler in handlers:
            try:
                handler(**payload)
            except Exception:
                _LOG.exception("Event handler failed for %s", event_name)

    def clear(self) -> None:
        with self._lock:
            self._handlers.clear()
