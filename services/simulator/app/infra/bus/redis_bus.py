from collections.abc import Callable
from typing import Any, TypedDict

import redis
from awrfo.logging.logger import get_logger
from redis.client import PubSub, PubSubWorkerThread

from app.infra.mappers import robot_state_mapper, task_mapper

logger = get_logger('Redis')


class RedisBusMessage(TypedDict):
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
        self, topic: str, callback: Callable[[RedisBusMessage], Any] | None = None
    ) -> None:
        if callback is not None:
            self.__p.subscribe(**{topic: callback})  # pyright: ignore
        else:
            self.__p.subscribe(topic)

    def publish_event(self, topic: str, message: str | bytes):
        self.__redis.publish(channel=topic, message=message)

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
        self,
        ex: Exception,
        _: PubSub,
        thread: PubSubWorkerThread,
    ) -> None:
        logger.error(str(ex))
        thread.stop()
        self.__thread = None

    # async def read_commands(self) -> list[Command]:
    #     commands = []
    #     while (cmd:=self.__p.get_message()):
    #         commands.append(cmd)


# class RedisEventPublisher:
#     def __init__(self, bus: RedisBusAdapter) -> None:
#         self.__bus = bus
#
#     def publish_task_completed_event(self, snapshot: TaskSnapshot) -> None:
#         proto_msg = task_mapper.taskcompleted_snapshot_to_proto(
#             snapshot,
#             '',
#             snapshot.timestamp_ms,
#         )
#         self.__bus.publish_event('TASK:COMPLETED', proto_msg.SerializeToString())
#
#     def publish_task_created_event(self, snapshot: TaskSnapshot) -> None:
#         event_to_publish = task_mapper.taskcreated_snapshot_to_proto(
#             snapshot,
#             snapshot.timestamp_ms,
#         )
#         self.__bus.publish_event('TASK:CREATED', event_to_publish.SerializeToString())
#
#     def publish_robot_state(self, snapshot: RobotStateSnapshot) -> None:
#         proto_msg = robot_state_mapper.snapshot_to_proto(
#             snapshot,
#             snapshot.timestamp_ms,
#         ).SerializeToString()
#         self.__bus.publish_event('ROBOT_STATE', proto_msg)
