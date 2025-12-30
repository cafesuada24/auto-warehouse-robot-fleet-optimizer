import queue
import threading
from collections.abc import Iterable
from time import monotonic, sleep

from awrfo.logging.logger import get_logger
from pydantic import NonNegativeFloat

from app.application.dtos.qos_policy import QoSPolicy
from app.application.events.domain_event import DomainEvent
from app.infra.bus.event_bus import EventBus
from app.infra.mappers.mappers import convert_to_proto

from .mappers import action_command_mapper, map_mapper, robot_state_mapper, task_mapper

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

    def wait_until_empty(self, timeout_s: NonNegativeFloat = 2.0) -> bool:
        """
        Block until all enqueued items are processed (q.task_done called),
        or timeout occurs. Returns True if drained.
        """

        deadline = monotonic() + timeout_s
        while monotonic() < deadline:
            if self.__q.unfinished_tasks == 0:
                return True
            sleep(0.01)
        return self.__q.unfinished_tasks == 0

    def enqueue_all(self, items: Iterable[DomainEvent]) -> None:
        for item in items:
            if item.policy == QoSPolicy.BEST_EFFORT:
                try:
                    self.__q.put_nowait(item)
                except queue.Full:
                    continue
            elif item.policy == QoSPolicy.RELIABLE:
                try:
                    self.__q.put(item, timeout=0.2)
                except queue.Full as e:
                    _logger.error('Publisher queue full; cannot enqueue RELIABLE event')
                    raise RuntimeError('Publisher queue is Full') from e

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
                _logger.exception('Mapper missing: %s', e)
                if item.policy == QoSPolicy.RELIABLE:
                    self.__stop.set()
            finally:
                self.__q.task_done()
