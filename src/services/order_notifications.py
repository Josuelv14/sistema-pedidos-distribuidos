import asyncio


class OrderNotifications:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Event]] = {}

    def subscribe(self, order_id: str) -> asyncio.Event:
        ready = asyncio.Event()
        self._subscribers.setdefault(order_id, set()).add(ready)
        return ready

    def unsubscribe(self, order_id: str, ready: asyncio.Event) -> None:
        subscribers = self._subscribers[order_id]
        subscribers.remove(ready)
        if not subscribers:
            del self._subscribers[order_id]

    def notify_ready(self, order_id: str) -> None:
        for ready in self._subscribers.get(order_id, ()):
            ready.set()