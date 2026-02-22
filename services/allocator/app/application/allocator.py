from __future__ import annotations

import heapq
import threading
from time import monotonic
from uuid import uuid4

from app.domain.models.robot_view import RobotView
from app.domain.models.task_view import TaskView
from awrfo.contracts.commands.v1.action_command_pb2 import ActionCommand, AssignTask
from awrfo.contracts.commands.v1.command_policy_pb2 import COMMAND_POLICY_MUST
from awrfo.contracts.commands.v1.command_type_pb2 import CommandType
from awrfo.contracts.events.task.v1.task_assigned_pb2 import TaskAssignedEvent
from awrfo.contracts.events.task.v1.task_assignment_rejected_pb2 import (
    RejectionReason,
    TaskAssignmentRejectedEvent,
)
from awrfo.contracts.events.task.v1.task_cancelled_pb2 import TaskCancelledEvent
from awrfo.contracts.events.task.v1.task_completed_pb2 import TaskCompletedEvent
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.events.task.v1.task_failed_pb2 import TaskFailedEvent
from awrfo.contracts.schemas.robot.v1.robot_state_pb2 import RobotState
from awrfo.logging.logger import get_logger
from awrfo.mathx import distance
from awrfo.types import IDType
from pydantic import NonNegativeFloat, NonNegativeInt

from .ports.event_bus import EventBus

_logger = get_logger('allocator')


def _compute_bid(robot: RobotView, task: TaskView) -> float:
    dist = distance(u=robot.pos, v=task.pickup)
    return dist + 1.0 - robot.battery


class Allocator:
    def __init__(
        self,
        bus: EventBus,
        *,
        task_batch_size: NonNegativeInt = 5,
        alloc_interval_ms: NonNegativeInt = 100,
        task_retry_s: NonNegativeInt = 5,
        max_retry_count: NonNegativeInt = 5,
    ) -> None:
        self.__stop = threading.Event()
        self.__bus = bus

        self.__robots: dict[IDType, RobotView] = {}
        self.__busy_robots: set[IDType] = set()
        self.__idle_robots: set[IDType] = set()

        self.__tasks: dict[IDType, TaskView] = {}
        self.__wait_retry_tasks: set[IDType] = set()
        self.__wait_confirm_tasks: set[IDType] = set()
        self.__executing_tasks: set[IDType] = set()
        self.__next_avail_task: list[tuple[int, IDType]] = []

        self.__alloc_interval_ms = alloc_interval_ms
        self.__prev_alloc_ms = 0

        self.__task_batch_size = task_batch_size

        self.__task_retry_s = task_retry_s
        self.__max_retry_count = max_retry_count

    def start(self) -> None:
        """Start the allocator loop."""
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

            now = monotonic()

            if self.__prev_alloc_ms + self.__alloc_interval_ms <= int(now * 1000):
                self.__flush_retrying_tasks(now)
                self.__allocate_batch()

        _logger.info('Allocator stopped.')

    def stop(self) -> None:
        """Stop the allocator."""
        self.__stop.set()

    def on_message(self, topic: str, payload: bytes) -> None:
        """Call on message and try allocate task.

        This function is used only for testing and will be removed in the future.
        """
        self.__on_message(topic, payload)
        self.__try_allocate()

    def __allocate_batch(self) -> None:
        for _ in range(min(self.__task_batch_size, len(self.__tasks))):
            self.__try_allocate()
        self.__prev_alloc_ms = int(monotonic() * 1000)

    def __on_message(self, topic: str, payload: bytes) -> None:
        match topic:
            case 'ROBOT_STATE':
                self.__handle_robot_state(payload)

            case 'TASK:CREATED':
                self.__handle_task_created(payload)

            case 'TASK:ASSIGNMENT:REJECTED':
                self.__handle_task_assignment_rejected(payload)

            case 'TASK:ASSIGNMENT:ACCEPTED':
                self.__handle_task_assignment_accepted(payload)

            case 'TASK:COMPLETED' | 'TASK:CANCELLED' | 'TASK:FAILED':
                self.__handle_task_terminate(payload, topic=topic)

            case _:
                _logger.debug('Ignoring topic=%s', topic)
                return

    def __handle_robot_state(self, payload: bytes) -> None:
        proto_msg = RobotState.FromString(payload)
        rid = IDType(proto_msg.id)
        incoming_ts_ms = proto_msg.ts_ms

        existing = self.__robots.get(rid)
        if existing is None:
            self.__robots[rid] = RobotView(
                id=rid,
                pos=(proto_msg.position.x, proto_msg.position.y),
                ts_ms=incoming_ts_ms,
                battery=proto_msg.battery,
            )
            self.__idle_robots.add(rid)
            return

        if proto_msg.ts_ms <= existing.ts_ms:
            _logger.debug(
                'Dropping stale ROBOT_STATE robot_id=%s incoming_ts=%d stored_ts=%d',
                str(rid),
                incoming_ts_ms,
                existing.ts_ms,
            )
            return

        robot = self.__robots[rid]
        robot.pos = (proto_msg.position.x, proto_msg.position.y)
        robot.ts_ms = incoming_ts_ms
        robot.battery = proto_msg.battery

    def __flush_retrying_tasks(self, now: NonNegativeFloat) -> None:
        for tid in tuple(self.__wait_retry_tasks):
            task = self.__tasks[tid]
            last_rejected = task.last_rejected_ts_s
            if last_rejected is None:
                raise RuntimeError(
                    f'Task {str(tid)} was marked as retrying without last_rejected_ts_s being set.'
                )
            if last_rejected + self.__task_retry_s <= now:
                task.last_rejected_ts_s = None
                self.__wait_retry_tasks.remove(tid)
                heapq.heappush(self.__next_avail_task, (task.ts_ms, tid))

    def __consider_retry(self, task: TaskView) -> bool:
        task.retry_count += 1
        if task.retry_count <= self.__max_retry_count:
            task.last_rejected_ts_s = monotonic()
            self.__wait_retry_tasks.add(task.id)
            return True

        self.__tasks.pop(task.id)
        return False

    def __handle_task_assignment_rejected(self, payload: bytes) -> None:
        proto_msg = TaskAssignmentRejectedEvent.FromString(payload)
        assignment_id = IDType(proto_msg.assignment_id)
        tid = IDType(proto_msg.task_id)

        try:
            self.__wait_confirm_tasks.remove(assignment_id)
        except KeyError:
            _logger.warning(
                'A duplicated/late/non-requested rejected assignment command received.',
            )
            return

        task = self.__tasks[tid]
        robot_id = IDType(proto_msg.robot_id)
        self.__idle_robots.add(robot_id)

        match proto_msg.reason:
            case RejectionReason.REJECTION_REASON_TEMPORARY_BUSY:
                if self.__consider_retry(task):
                    _logger.info(
                        f'Execution for task {str(tid)} has been rejected, reason: system is temporary busy'
                        f', retrying after {self.__task_retry_s} seconds.',
                    )
                else:
                    _logger.info(
                        f'Execution for task {str(tid)} has been rejected, reason: system is temporary busy'
                        f', removing task because retry times limit execeeded.',
                    )

            case RejectionReason.REJECTION_REASON_INSUFFICIENT_CAPABILITY:
                task.blacklist_robot_ids.add(robot_id)
                _logger.info(
                    f'Execution for task {str(tid)} has been rejection'
                    f', reason: Robot {str(robot_id)} had insufficient capability'
                    ', blocked from further consideration.',
                )

            case RejectionReason.REJECTION_REASON_LOCATION_SO_FAR:
                _logger.info(
                    f'Execution for task {str(tid)} has been rejection'
                    f', reason: robot location so far, retrying',
                )

            case RejectionReason.REJECTION_REASON_INVALID_TASK:
                _logger.info(
                    'Execution for task {str(tid)} has been rejection'
                    ', reason: invalid task. Task has been removed.',
                )

            case RejectionReason.REJECTION_REASON_SYSTEM_ERROR:
                _logger.info(
                    'Execution for task {str(tid)} has been rejection'
                    ', reason: system error, retrying with backoff.',
                )

        # heapq.heappush(self.__next_avail_task, (self.__tasks[tid].ts_ms, tid))

    def __handle_task_assignment_accepted(self, payload: bytes) -> None:
        proto_msg = TaskAssignedEvent.FromString(payload)
        assignment_id = IDType(proto_msg.assignment_id)

        try:
            self.__wait_confirm_tasks.remove(assignment_id)
        except KeyError:
            _logger.warning(
                'A duplicated/late/non-requested accepted assignement command received.',
            )
            return

        tid = IDType(proto_msg.task_id)
        robot_id = IDType(proto_msg.robot_id)
        if robot_id in self.__busy_robots:
            raise RuntimeError(
                f'A busy robot was assigned to an accepted task: {assignment_id=}, {tid=}, {robot_id=}',
            )
        self.__executing_tasks.add(tid)
        self.__busy_robots.add(robot_id)

    def __handle_task_created(self, payload: bytes) -> None:
        proto_msg = TaskCreatedEvent.FromString(payload)
        tid = IDType(proto_msg.task_id)
        if tid in self.__tasks:
            _logger.debug(f'Seen duplicated TaskCreatedEvent for task id: {str(tid)}')
            return
        heapq.heappush(self.__next_avail_task, (proto_msg.ts_ms, tid))
        self.__tasks[tid] = TaskView(
            id=tid,
            pickup=(int(proto_msg.pickup.x), int(proto_msg.pickup.y)),
            ts_ms=proto_msg.ts_ms,
            deadline_ms=proto_msg.deadline_ms,
        )

    def __handle_task_terminate(self, payload: bytes, topic: str) -> None:
        match topic:
            case 'TASK:COMPLETED':
                task = TaskCompletedEvent.FromString(payload)
                _logger.info(f'Task {task.task_id} completed.')
            case 'TASK:CANCELLED':
                task = TaskCancelledEvent.FromString(payload)
                _logger.info(f'Task {task.task_id} cancelled.')
            case 'TASK:FAILED':
                task = TaskFailedEvent.FromString(payload)
                _logger.info(f'Task {task.task_id} failed.')
            case _:
                _logger.debug('Ignoreing task teminate request for topic: %s', topic)
                return

        tid = IDType(task.task_id)
        rid = IDType(task.robot_id)
        self.__tasks.pop(tid, None)
        self.__executing_tasks.remove(tid)
        self.__busy_robots.remove(rid)
        self.__idle_robots.add(rid)

    def __try_allocate(self) -> None:
        _logger.warning('Called')
        if len(self.__idle_robots) == 0:
            return

        if len(self.__next_avail_task) == 0:
            return

        _, task_id = heapq.heappop(self.__next_avail_task)

        bids = [
            (_compute_bid(self.__robots[rid], self.__tasks[task_id]), rid)
            for rid in self.__idle_robots
        ]
        # bids.sort()

        _, winner_id = min(bids)
        self.__idle_robots.remove(winner_id)

        # self.__inflight_tasks.add(task_id)
        # self.__busy_robots.add(winner_id)

        self._log_bid_table(task_id, bids, winner_id)

        assignment_id = uuid4()
        cmd = ActionCommand(
            id=str(assignment_id),
            robot_id=str(winner_id),
            ts_ms=0,
            type=CommandType.COMMAND_TYPE_ASSIGN_TASK,
            assign_task=AssignTask(
                task_id=str(task_id),
            ),
            policy=COMMAND_POLICY_MUST,
        ).SerializeToString()
        self.__bus.publish('COMMAND', cmd)
        self.__wait_confirm_tasks.add(assignment_id)
        _logger.warning(f'assigned {task_id}')

    def _log_bid_table(
        self,
        task_id: IDType,
        bids: list[tuple[float, IDType]],
        winner: IDType,
    ) -> None:
        # Keep this in the demo: it sells "multi-agent bidding" instantly.
        lines = [f'Auction for task={str(task_id)}']
        for c, rid in bids[:10]:
            mark = ' <= WINNER' if rid == winner else ''
            lines.append(f'  robot={str(rid)} bid={c:.3f}{mark}')
        _logger.info('\n' + '\n'.join(lines))
