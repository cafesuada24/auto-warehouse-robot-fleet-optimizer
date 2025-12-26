import queue
import threading
from collections.abc import Iterable

from awrfo.logging.logger import get_logger

from app.application.dtos.qos_policy import QoSPolicy
from app.application.events.domain_event import DomainEvent
from app.infra.bus.event_bus import EventBus
from app.infra.mappers.mappers import convert_to_proto

from .mappers import action_command_mapper, robot_state_mapper, task_mapper

_logger = get_logger('publisher')


class EventPublisher[T]:
    def __init__(self, bus: EventBus[T], q_size: int = 10_000) -> None:
        super().__init__()

        self.__bus = bus
        self.__thread: threading.Thread | None = None
        self.__stop = threading.Event()
        self.__q = queue.Queue[DomainEvent](q_size)

    def start(self) -> None:
        """Start the publisher thread."""
        self.__stop.clear()
        self.__thread = threading.Thread(
            target=self.__run,
            name='publisher',
            daemon=True,
        )
        self.__thread.start()

    def stop(self) -> None:
        """Stop the publisher thread."""
        self.__stop.set()

        if self.__thread:
            self.__thread.join(timeout=2.0)

        self.__thread = None

    def enqueue_all(self, items: Iterable[DomainEvent]) -> None:
        for item in items:
            if item.policy is QoSPolicy.BEST_EFFORT:
                try:
                    self.__q.put_nowait(item)
                except queue.Full:
                    continue
            elif item.policy is QoSPolicy.RELIABLE:
                self.__q.put(item)

    def __run(self) -> None:
        while not self.__stop.is_set():
            try:
                item = self.__q.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                proto_type = convert_to_proto(item.payload)
                serialized: bytes = proto_type.SerializeToString()

                self.__bus.publish_event(item.topic, serialized)
            except NotImplementedError as e:
                _logger.warning(e)
                if item.policy is QoSPolicy.RELIABLE:
                    raise
            finally:
                self.__q.task_done()
