import sys
from collections.abc import Callable
from typing import Any, TypedDict

import redis
from redis.client import PubSubWorkerThread

class Command(TypedDict):
    channel: bytes
    data: bytes
    pattern: str | None
    type: str


class RedisBusAdapter:
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
        self.__thread: PubSubWorkerThread | None = None

    def subscribe(
        self, topic: str, callback: Callable[[Command], Any] | None = None
    ) -> None:
        if callback is not None:
            self.__p.subscribe(**{topic: callback})  # pyright: ignore
        else:
            self.__p.subscribe(topic)

    async def publish_event(self, topic: str, message: str):
        await self.__redis.publish(channel=topic, message=message)

    def start(self) -> None:
        self.__thread = self.__p.run_in_thread(
            sleep_time=0.001,
            exception_handler=self.__thread_exception_handler,
        )

    def cleanup(self) -> None:
        if self.__thread:
            self.__thread.stop()
            self.__thread = None

        self.__p.close()
        self.__redis.close()

    def __thread_exception_handler(
        self, ex, pubsub, thread: PubSubWorkerThread
    ) -> None:
        print(ex, file=sys.stderr)
        thread.stop()
        self.__thread = None

    # async def read_commands(self) -> list[Command]:
    #     commands = []
    #     while (cmd:=self.__p.get_message()):
    #         commands.append(cmd)
