from collections.abc import Callable
from pathlib import Path

from stock_trade.events.models import Event

EventSubscriber = Callable[[Event], None]


class EventBus:
    def __init__(self, raise_on_error: bool = False) -> None:
        self._subscribers: list[EventSubscriber] = []
        self.raise_on_error = raise_on_error
        self.last_errors: list[Exception] = []

    def subscribe(self, subscriber: EventSubscriber) -> None:
        self._subscribers.append(subscriber)

    def publish(self, event: Event) -> None:
        errors: list[Exception] = []
        for subscriber in self._subscribers:
            try:
                subscriber(event)
            except Exception as error:
                errors.append(error)
        self.last_errors = errors
        if errors and self.raise_on_error:
            raise ExceptionGroup("event subscriber failures", errors)


class JsonlEventSink:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def __call__(self, event: Event) -> None:
        path = self.directory / f"{event.run_id}.jsonl"
        with path.open("a", encoding="utf-8") as event_file:
            event_file.write(event.to_json() + "\n")