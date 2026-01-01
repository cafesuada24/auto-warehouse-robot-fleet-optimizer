import signal

from app.application.allocator import Allocator
from app.infra.bus.redis_bus import RedisBus
from awrfo.logging.logger import get_logger

_logger = get_logger('main')


def main() -> None:
    bus = RedisBus()
    allocator = Allocator(bus=bus)

    def _handle_sig(*_: object) -> None:
        _logger.info('Signal received, stopping...')
        allocator.stop()

    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)

    allocator.start()


if __name__ == '__main__':
    main()
