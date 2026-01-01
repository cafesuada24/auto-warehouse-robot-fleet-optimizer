# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

import copy
import math
import queue
import threading
from collections.abc import Callable, Iterable
from queue import Queue
from time import monotonic, sleep

from app.application.commands.base import CommandBase
from app.application.commands.move_to import MoveToCommand
from app.application.commands.policy import CommandPolicy
from app.application.commands.task_commands import AssignTaskCommand, CancelTaskCommand
from app.application.dtos.qos_policy import QoSPolicy
from app.application.events.domain_event import DomainEvent
from app.domain.events.task_events import (
    TaskAssignedEvent,
    TaskCancelledEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskFailedEvent,
)
from app.domain.models.robot import Robot, RobotGoal, RobotGoalType, RobotState
from app.domain.models.sim_clock import SimClock
from app.domain.models.task import (
    Task,
    TaskPhase,
    TaskStatus,
)
from app.domain.models.world import World
from app.domain.types import Position
from awrfo.logging import logging_context
from awrfo.logging.logger import get_logger
from awrfo.mathx import distance
from awrfo.ttl_cache import TTLCache
from awrfo.types import IDType
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from .ports.event_publisher import EventPublisher

_logger = get_logger('simulator')


def _clear_robot_task(robot: Robot) -> None:
    robot.task_phase = None
    robot.state = RobotState.IDLE
    robot.intent = None
    robot.assigned_task_id = None


def _move_robot(
    robot: Robot, dt_s: NonNegativeFloat, obstacles: set[tuple[int, int]]
) -> None:
    assert (
        robot.intent is not None
        and robot.intent.type == RobotGoalType.MOVE
        and robot.intent.pos is not None
    )

    dist = distance(robot.intent.pos, robot.pos)
    if dist == 0.0:
        return
    dx = robot.intent.pos[0] - robot.pos[0]
    dy = robot.intent.pos[1] - robot.pos[1]
    step = robot.max_speed_mps * dt_s
    new_pos = (
        robot.pos[0] + dx / dist * step,
        robot.pos[1] + dy / dist * step,
    )
    if (
        math.floor(new_pos[0]),
        math.floor(new_pos[1]),
    ) not in obstacles:
        robot.pos = new_pos


def _update_wait_remaining(robot: Robot, dt_s: NonNegativeFloat) -> None:
    assert (
        robot.intent is not None
        and robot.intent.type == RobotGoalType.WAIT
        and robot.intent.wait_remaining_ms is not None
    )

    robot.intent.wait_remaining_ms = max(
        0,
        robot.intent.wait_remaining_ms - int(dt_s * 1000),
    )


def _is_intent_done(robot: Robot) -> bool:
    if robot.intent is None:
        return True

    if robot.intent.type == RobotGoalType.WAIT:
        return robot.intent.wait_remaining_ms == 0.0

    assert robot.intent.pos is not None

    dx = robot.intent.pos[0] - robot.pos[0]
    dy = robot.intent.pos[1] - robot.pos[1]
    return dx**2 + dy**2 <= robot.arrive_eps_m**2


def advance_phase(task: Task, robot: Robot) -> None:
    """Advance the task to the next phase.

    - Update the phase and the status for the Task
    - Update the Robot's intent and state
    """
    if robot.assigned_task_id != task.id:
        raise ValueError('Robot is not assigned to this task')

    if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED, TaskStatus.FAILED):
        raise ValueError(f'Cannot advance terminal task status: {task.status}')

    if task.status != TaskStatus.EXECUTING:
        task.status = TaskStatus.EXECUTING

    if robot.task_phase is None:
        robot.state = RobotState.MOVING
        robot.intent = RobotGoal(type=RobotGoalType.MOVE, pos=task.pickup)
        robot.task_phase = TaskPhase.TO_PICKUP
        return

    match robot.task_phase:
        case TaskPhase.TO_PICKUP:
            robot.task_phase = TaskPhase.PICKING

            robot.state = RobotState.PICKING
            robot.intent = RobotGoal(type=RobotGoalType.WAIT, wait_remaining_ms=0)
            return

        case TaskPhase.PICKING:
            robot.task_phase = TaskPhase.TO_DROPOFF

            robot.state = RobotState.MOVING
            robot.intent = RobotGoal(type=RobotGoalType.MOVE, pos=task.dropoff)
            return

        case TaskPhase.TO_DROPOFF:
            robot.task_phase = TaskPhase.DROPPING

            robot.state = RobotState.DROPPING
            robot.intent = RobotGoal(type=RobotGoalType.WAIT, wait_remaining_ms=0)
            return

        case TaskPhase.DROPPING:
            task.status = TaskStatus.COMPLETED
            _clear_robot_task(robot)
            return
        case _:
            raise ValueError(f'Unknown task phase: {robot.task_phase}')


class Simulator:
    def __init__(
        self,
        world: World,
        # bus: EventBus[T],
        event_publisher: EventPublisher,
        tick_hz: PositiveInt = 10,
        q_size: PositiveInt = 10_000,
    ) -> None:
        # self.__bus = bus
        self.__event_publisher = event_publisher

        self.__q_size = q_size

        self.__tick_hz = tick_hz
        self.__tick_ms = 1000 // self.__tick_hz
        self.__dt_s = self.__tick_ms / 1000.0

        self.__world = world
        self.__world.time_ms = 0
        self.__world.tick_ms = self.__tick_ms
        self.__world_copy = copy.deepcopy(self.__world)

        self.__clock = SimClock(self.__tick_ms)

        self.__command_queue = Queue[CommandBase](q_size)

        self.__stop_ev = threading.Event()
        self.__thread: threading.Thread | None = None

        self.__cmd_ttl_cache = TTLCache[IDType](use_wall_timer=False)

    def register_command(self, command: CommandBase) -> None:
        logging_context.clear_context()
        try:
            cmd_id = command.id
            now_ms = self.sim_time_ms

            if not self.__cmd_ttl_cache.try_add(value=cmd_id, ts_ms=now_ms):
                _logger.info(
                    'Duplicate command; drop',
                    extra={'cmd_id': str(cmd_id), 'policy': str(command.policy)},
                )
                return

            try:
                if command.policy == CommandPolicy.BEST_EFFORT:
                    self.__command_queue.put_nowait(command)
                elif command.policy == CommandPolicy.MUST:
                    self.__command_queue.put(command, timeout=0.2)
                else:
                    _logger.error(
                        'Invalid command policy', extra={'cmd_id': str(cmd_id)}
                    )
                    self.__cmd_ttl_cache.remove(cmd_id, ts_ms=now_ms)
                    return

            except queue.Full:
                # rollback “seen” so a retry can be accepted
                self.__cmd_ttl_cache.remove(cmd_id, ts_ms=now_ms)

                if command.policy == CommandPolicy.BEST_EFFORT:
                    _logger.warning(
                        'Queue full; drop BEST_EFFORT', extra={'cmd_id': str(cmd_id)}
                    )
                    return

                _logger.error(
                    'Queue full; MUST command rejected. Stopping simulator.',
                    extra={'cmd_id': str(cmd_id)},
                )
                self.stop()
                return

        finally:
            logging_context.clear_context()

    def create_task(
        self,
        pickup: Position,
        dropoff: Position,
        duration_s: float,
    ) -> None:
        """Create an unassigned pickup/dropoff task."""
        now = self.sim_time_ms
        task = Task(
            pickup=pickup,
            dropoff=dropoff,
            status=TaskStatus.CREATED,
            deadline_ms=now + int(duration_s * 1000),
        )
        self.__world.tasks[task.id] = task

        event = TaskCreatedEvent(
            task_id=task.id,
            timestamp_ms=now,
            pickup=task.pickup,
            dropoff=task.dropoff,
            deadline_ms=task.deadline_ms,
        )

        self.__event_publisher.enqueue_all(
            [
                DomainEvent(
                    topic='TASK:CREATED',
                    payload=event,
                    time_ms=now,
                    policy=QoSPolicy.RELIABLE,
                ),
            ],
        )

        _logger.info(
            'New task published',
            extra={
                'id': task.id,
                'type': task.__class__,
            },
        )

    @property
    def sim_time_ms(self) -> NonNegativeInt:
        """Return the simulation time in milliseconds."""
        return self.__clock.time_ms()

    @property
    def sim_time_s(self) -> NonNegativeFloat:
        """Return the simulation time in seconds."""
        return self.__clock.time_s()

    def tick_many(self, n: int) -> None:
        """Tick the simulator 'n' times."""
        for _ in range(n):
            self.tick_once()

    def tick_until(
        self,
        predicate: Callable[[], bool],
        *,
        max_ticks: int = 10_000,
    ) -> bool:
        """Tick until a condition is satisfied."""
        for _ in range(max_ticks):
            self.tick_once()
            if predicate():
                return True
        return False

    def is_running(self) -> bool:
        """If the simulator is running."""
        return not self.__stop_ev.is_set()

    def tick_once(self) -> Iterable[DomainEvent]:
        """Tick the simulator once."""
        self.__clock.tick()
        self.__world.time_ms = self.__clock.time_ms()

        commands = self.__drain_commands()

        events = self.__step(self.__dt_s, commands)
        self.__event_publisher.enqueue_all(events)
        return events

    def start(self) -> None:
        """Start the simulation."""
        if self.__thread is not None and self.__thread.is_alive():
            return

        self.__stop_ev.clear()
        self.__clock.start(reset=True)

        self.__thread = threading.Thread(
            target=self.__run_loop,
            name='sim-loop',
            daemon=True,
        )
        self.__thread.start()
        _logger.info('Simulator started')

        self.__event_publisher.enqueue_all(
            [
                DomainEvent(
                    topic='MAP:UPDATED',
                    time_ms=self.__world.time_ms,
                    policy=QoSPolicy.BEST_EFFORT,
                    payload=self.__world.map.snapshot(self.__world.time_ms),
                ),
            ],
        )

    def stop(self) -> None:
        """Stop event loop."""
        self.__stop_ev.set()
        self.__clock.stop()
        if self.__thread is not None:
            self.__thread.join(timeout=2.0)
        self.__thread = None

        _logger.info('Simulator stopped')

    def reset(self) -> None:
        is_running = not self.__stop_ev.is_set()
        self.stop()
        self.__world = copy.deepcopy(self.__world_copy)
        self.__clock.reset()
        self.__event_publisher.reset()
        self.__command_queue = Queue[CommandBase](self.__q_size)
        self.__cmd_ttl_cache.reset()

        if is_running:
            self.start()

    def __run_loop(self) -> None:
        tick_period_s = 1.0 / self.__tick_hz
        next_deadline = monotonic()

        try:
            while not self.__stop_ev.is_set():
                now = monotonic()
                if now < next_deadline:
                    sleep(next_deadline - now)

                self.tick_once()

                next_deadline += tick_period_s

        except Exception as e:
            _logger.error(f'Simulator crashed, stopping...: {e!r}')
            self.stop()

    def __drain_commands(self) -> Iterable[CommandBase]:
        cmds: Iterable[CommandBase] = []

        while True:
            try:
                cmds.append(self.__command_queue.get_nowait())
            except queue.Empty:
                break

        return cmds

    def __step(
        self,
        dt_s: NonNegativeFloat,
        cmds: Iterable[CommandBase],
    ) -> list[DomainEvent]:
        events: list[DomainEvent] = []

        for cmd in cmds:
            evs = self.__execute_command(cmd)
            events.extend(evs)

        now = self.__world.time_ms

        robots = list(self.__world.robots.values())
        events.extend(
            [
                ev
                for robot in robots
                if (ev := self.__execute_robot_task(robot, dt_s)) is not None
            ],
        )

        # for robot in robots:
        #     completed_ev = self.__execute_robot_task(robot, dt_s)
        #     if completed_ev is not None:
        #         completed_tasks.append(completed_ev)

        return events + [
            DomainEvent(
                topic='ROBOT_STATE',
                payload=robot.snapshot(now),
                time_ms=now,
                policy=QoSPolicy.BEST_EFFORT,
            )
            for robot in robots
        ]

    def __cancel_current_task(
        self,
        robot: Robot,
        reason: str | None = None,
    ) -> DomainEvent | None:
        task_id = robot.assigned_task_id
        if task_id is None:
            return None
        self.__world.tasks[task_id].status = TaskStatus.CANCELLED
        _clear_robot_task(robot)

        # del self.__tasks[task_id]
        return DomainEvent(
            topic='TASK:CANCELLED',
            time_ms=self.__world.time_ms,
            policy=QoSPolicy.RELIABLE,
            payload=TaskCancelledEvent(
                task_id=task_id,
                timestamp_ms=self.__world.time_ms,
                robot_id=robot.id,
                reason=reason,
            ),
        )

    def __execute_command(
        self,
        command: CommandBase,
    ) -> list[DomainEvent]:
        logging_context.clear_context()

        logging_context.bind_context(
            {
                'command_id': command.id,
                'robot_id': command.robot_id,
            },
        )

        robot = self.__world.robots[command.robot_id]

        now_ms = self.__world.time_ms
        events: list[DomainEvent] = []

        try:
            match command:
                case AssignTaskCommand():
                    # Cancel previous task if the robot is being assigned to the new task
                    cancelled_ev = self.__cancel_current_task(robot)
                    if cancelled_ev is not None:
                        events.append(cancelled_ev)

                    robot.assigned_task_id = command.task_id
                    self.__world.tasks[command.task_id].status = TaskStatus.ASSIGNED

                    de = DomainEvent(
                        topic='TASK:ASSIGNED',
                        time_ms=now_ms,
                        policy=QoSPolicy.RELIABLE,
                        payload=TaskAssignedEvent(
                            task_id=command.task_id,
                            timestamp_ms=now_ms,
                            robot_id=robot.id,
                        ),
                    )
                    events.append(de)

                case CancelTaskCommand():
                    cancelled_ev = self.__cancel_current_task(robot)
                    if cancelled_ev is not None:
                        events.append(cancelled_ev)

                case MoveToCommand():
                    robot.intent = RobotGoal(type=RobotGoalType.MOVE, pos=command.pos)
                case _:
                    _logger.error(
                        f'Tried to execute unsupported command type: {command!r}',
                    )
                    raise ValueError(f'Unsupported command type: {command!r}')
        finally:
            logging_context.clear_context()

        return events

    def __execute_robot_task(
        self,
        robot: Robot,
        dt_s: NonNegativeFloat,
    ) -> DomainEvent | None:
        if robot.assigned_task_id is None and robot.intent is None:
            return None

        now_ms = self.__world.time_ms

        task_id = robot.assigned_task_id
        task = None
        if task_id is not None:
            task = self.__world.tasks.get(task_id)

        if task is not None and task.deadline_ms <= now_ms:
            task.status = TaskStatus.FAILED
            _clear_robot_task(robot)

            payload = TaskFailedEvent(
                task_id=task.id,
                robot_id=robot.id,
                timestamp_ms=now_ms,
                reason='Task timeout',
            )

            return DomainEvent(
                topic='TASK:FAILED',
                payload=payload,
                time_ms=now_ms,
                policy=QoSPolicy.RELIABLE,
            )

        if _is_intent_done(robot):
            if task is None:
                return None

            advance_phase(task, robot)

            if task.status == TaskStatus.COMPLETED:
                # no more task to do, reset robot state
                robot.assigned_task_id = None
                robot.state = RobotState.IDLE

                payload = TaskCompletedEvent(
                    task_id=task.id,
                    robot_id=robot.id,
                    timestamp_ms=now_ms,
                    duration_ms=0,
                )

                return DomainEvent(
                    topic='TASK:COMPLETED',
                    payload=payload,
                    time_ms=now_ms,
                    policy=QoSPolicy.RELIABLE,
                )

            return None

        if robot.intent.type == RobotGoalType.MOVE:
            _move_robot(robot, dt_s, self.__world.map.obstacles)
        else:
            _update_wait_remaining(robot, dt_s)

        return None
