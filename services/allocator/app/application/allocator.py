import threading

from awrfo.logging.logger import get_logger

from .ports.event_bus import EventBus

_logger = get_logger('allocator')


class Allocator:
    def __init__(self, bus: EventBus) -> None:
        self.__stop = threading.Event()
        self.__bus = bus

    def start(self) -> None:
        _logger.info('Allocator starting...')
        self.__stop.clear()

        while not self.__stop.is_set():
            msg = self.__bus.poll(0.2)
            if not msg:
                continue

            try:
                self.__on_message(topic=msg.topic, payload=msg.payload)
            except Exception as e:
                _logger.exception('Unhandled error processing message: %r', e)

        _logger.info('Allocator stopped.')

    def stop(self) -> None:
        self.__stop.set()

    def __on_message(self, topic: str, payload: bytes) -> None:
        match topic:
            case 'ROBOT_STATE':
                self.__handle_robot_state(payload)

            case 'TASK:CREATED':
                self.__handle_task_created(payload)

            case 'TASK:COMPLETED' | 'TASK:CANCELLED' | 'TASK:FAILED':
                self.__handle_task_terminate(payload)

            case _:
                _logger.debug('Ignoring topic=%s', topic)
                return

        self.__try_allocate()

    def __handle_robot_state(self, payload: bytes) -> None: ...

    def __handle_task_created(self, payload: bytes) -> None: ...

    def __handle_task_terminate(self, payload: bytes) -> None: ...

    def __try_allocate(self) -> None: ...
