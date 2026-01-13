import threading
from uuid import uuid4

from app.domain.models.robot_view import RobotView
from app.domain.models.task_view import TaskStatus, TaskView
from awrfo.contracts.commands.v1.action_command_pb2 import ActionCommand, AssignTask
from awrfo.contracts.commands.v1.command_policy_pb2 import COMMAND_POLICY_MUST
from awrfo.contracts.commands.v1.command_type_pb2 import CommandType
from awrfo.contracts.events.task.v1.task_cancelled_pb2 import TaskCancelledEvent
from awrfo.contracts.events.task.v1.task_completed_pb2 import TaskCompletedEvent
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.events.task.v1.task_failed_pb2 import TaskFailedEvent
from awrfo.contracts.schemas.robot.v1.robot_state_pb2 import RobotState
from awrfo.logging.logger import get_logger
from awrfo.mathx import distance
from awrfo.types import IDType

from .ports.event_bus import EventBus

_logger = get_logger('allocator')


def _compute_bid(robot: RobotView, task: TaskView) -> float:
    dist = distance(u=robot.pos, v=task.pickup)
    return dist + 1.0 - robot.battery


class Allocator:
    def __init__(self, bus: EventBus) -> None:
        self.__stop = threading.Event()
        self.__bus = bus
        self.__robots: dict[IDType, RobotView] = {}
        self.__busy_robots: set[IDType] = set()
        self.__tasks: dict[IDType, TaskView] = {}
        self.__inflight_tasks: set[IDType] = set()

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

    def on_message(self, topic: str, payload: bytes) -> None:
        self.__on_message(topic, payload)

    def __on_message(self, topic: str, payload: bytes) -> None:
        match topic:
            case 'ROBOT_STATE':
                self.__handle_robot_state(payload)

            case 'TASK:CREATED':
                self.__handle_task_created(payload)

            case 'TASK:COMPLETED' | 'TASK:CANCELLED' | 'TASK:FAILED':
                self.__handle_task_terminate(payload, topic=topic)

            case _:
                _logger.debug('Ignoring topic=%s', topic)
                return

        self.__try_allocate()

    def __handle_robot_state(self, payload: bytes) -> None:
        proto_msg = RobotState.FromString(payload)
        rid = IDType(proto_msg.id)
        print(proto_msg)
        if rid not in self.__robots:
            self.__robots[rid] = RobotView(
                id=rid,
                pos=(proto_msg.position.x, proto_msg.position.y),
                ts_ms=proto_msg.ts_ms,
                battery=proto_msg.battery,
            )
            return

        robot = self.__robots[rid]
        robot.pos = (proto_msg.position.x, proto_msg.position.y)
        robot.ts_ms = proto_msg.ts_ms
        robot.battery = proto_msg.battery

    def __handle_task_created(self, payload: bytes) -> None:
        proto_msg = TaskCreatedEvent.FromString(payload)
        tid = IDType(proto_msg.task_id)
        if tid in self.__tasks:
            _logger.debug(f'Seen duplicated TaskCreatedEvent for task id: {str(tid)}')
            return
        self.__tasks[tid] = TaskView(
            id=tid,
            pickup=(int(proto_msg.pickup.x), int(proto_msg.pickup.y)),
            deadline_ms=proto_msg.deadline_ms,
            status=TaskStatus.CREATED,
        )

    def __handle_task_terminate(self, payload: bytes, topic: str) -> None:
        match topic:
            case 'TASK:COMPLETED':
                task = TaskCompletedEvent.FromString(payload)
            case 'TASK:CANCELLED':
                task = TaskCancelledEvent.FromString(payload)
            case 'TASK:FAILED':
                task = TaskFailedEvent.FromString(payload)
            case _:
                _logger.debug('Ignoreing task teminate request for topic: %s', topic)
                return

        tid = IDType(task.task_id)
        rid = IDType(task.robot_id)
        self.__tasks.pop(tid, None)
        self.__inflight_tasks.discard(tid)
        self.__busy_robots.discard(rid)

    def __try_allocate(self) -> None:
        idle_robots = set(self.__robots.keys()) - self.__busy_robots
        if not idle_robots:
            return

        awaiting_tasks = list(set(self.__tasks.keys()) - self.__inflight_tasks)
        if not awaiting_tasks:
            return

        task_id = awaiting_tasks[0]

        bids = [
            (_compute_bid(self.__robots[rid], self.__tasks[task_id]), rid)
            for rid in idle_robots
        ]
        bids.sort()

        _, winner_id = bids[0]
        self.__inflight_tasks.add(task_id)
        self.__busy_robots.add(winner_id)

        self._log_bid_table(task_id, bids, winner_id)

        cmd = ActionCommand(
            id=str(uuid4()),
            robot_id=str(winner_id),
            ts_ms=0,
            type=CommandType.COMMAND_TYPE_ASSIGN_TASK,
            assign_task=AssignTask(
                task_id=str(task_id),
            ),
            policy=COMMAND_POLICY_MUST,
        ).SerializeToString()
        self.__bus.publish('COMMAND', cmd)

    def _log_bid_table(
        self, task_id: IDType, bids: list[tuple[float, IDType]], winner: IDType
    ) -> None:
        # Keep this in the demo: it sells "multi-agent bidding" instantly.
        lines = [f'Auction for task={str(task_id)}']
        for c, rid in bids[:10]:
            mark = ' <= WINNER' if rid == winner else ''
            lines.append(f'  robot={str(rid)} bid={c:.3f}{mark}')
        _logger.info('\n' + '\n'.join(lines))
