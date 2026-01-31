import redis
from app.application.ports.event_bus import EventMessage
from awrfo.logging.logger import get_logger
from pydantic import NonNegativeFloat

_logger = get_logger('redis_bus')


class RedisBus:
    def __init__(self, host: str = 'localhost', port: int = 6379) -> None:
        self.__host = host
        self.__port = port
        self.__redis = redis.Redis(
            host=self.__host,
            port=self.__port,
            db=0,
            protocol=3,
        )
        self.__p = self.__redis.pubsub(ignore_subscribe_messages=True)  # pyright: ignore

    def poll(self, timeout_s: NonNegativeFloat = 0.2) -> EventMessage | None:
        msg = self.__p.get_message(timeout=timeout_s)
        if msg is None:
            return None
        if (
            'topic' not in msg
            or 'data' not in msg
            or not isinstance(msg['topic'], str)
            or not isinstance(msg['data'], bytes)
        ):
            _logger.debug(f'Ignoring invalid message: {msg}')
            return None

        return EventMessage(
            topic=msg['topic'],
            payload=msg['data'],
        )

    def publish(self, topic: str, payload: bytes) -> None:
        self.__redis.publish(channel=topic, message=payload)

    def close(self) -> None:
        self.__p.close()
        self.__redis.close()
