# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

import math
import queue
import threading
from collections.abc import Iterable
from queue import Queue
from time import monotonic, sleep

from app.application.dtos.publish_request import PublishPolicy, PublishRequest
from app.domain.models.command import (
    AssignTaskCommand,
    CancelTaskCommand,
    CommandBase,
    MoveToCommand,
)
from app.domain.models.robot import Robot, RobotGoal, RobotGoalType, RobotState
from app.domain.models.sim_clock import SimClock
from app.domain.models.task import (
    Task,
    TaskCompletedEvent,
    TaskCreatedEvent,
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

from .interfaces.ports.event_publisher import EventPublisher

_logger = get_logger('simulator')


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
            robot.task_phase = None
            task.status = TaskStatus.COMPLETED

            robot.state = RobotState.IDLE
            robot.intent = None
            robot.assigned_task_id = None
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

        self.__tick_hz = tick_hz
        self.__tick_ms = 1000 // self.__tick_hz
        self.__dt_s = self.__tick_ms / 1000.0

        self.__world = world
        self.__world.time_ms = 0
        self.__world.tick_ms = self.__tick_ms

        self.__clock = SimClock(self.__tick_ms)

        self.__command_queue = Queue[CommandBase](q_size)

        self.__stop_ev = threading.Event()
        self.__thread: threading.Thread | None = None

        self.__cmd_ttl_cache = TTLCache[IDType](use_wall_timer=False)

    def register_command(self, command: CommandBase) -> None:
        """Register a command to be executed."""
        logging_context.clear_context()

        _logger.info('New command requested')
        if not self.__cmd_ttl_cache.try_add(value=command.id, ts_ms=self.sim_time_ms):
            _logger.warning('Duplicated command detected, discarding...')
            return

        try:
            self.__command_queue.put_nowait(command)
            _logger.info('Command queued to be executed')
        except queue.Full:
            _logger.error('Command queue is full, stopping simulator...')
            self.stop()

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
            id=task.id,
            timestamp_ms=now,
            pickup=task.pickup,
            dropoff=task.dropoff,
            deadline_ms=task.deadline_ms,
        )

        self.__event_publisher.enqueue_all(
            [
                PublishRequest(
                    topic='TASK:CREATED',
                    payload=event,
                    time_ms=now,
                    policy=PublishPolicy.RELIABLE,
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

    def stop(self) -> None:
        """Stop event loop."""
        self.__stop_ev.set()
        self.__clock.stop()
        if self.__thread is not None:
            self.__thread.join(timeout=2.0)
        self.__thread = None

        _logger.info('Simulator stopped')

    def __run_loop(self) -> None:
        tick_period_s = 1.0 / self.__tick_hz
        next_deadline = monotonic()

        try:
            while not self.__stop_ev.is_set():
                now = monotonic()
                if now < next_deadline:
                    sleep(next_deadline - now)

                self.__tick()

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
    ) -> Iterable[PublishRequest]:
        for cmd in cmds:
            self.__execute_command(cmd)

        robots = self.__world.robots.values()
        for robot in robots:
            self.__execute_robot_task(robot, dt_s)

        now = self.sim_time_ms

        return [
            PublishRequest(
                topic='ROBOT_STATE',
                payload=robot.snapshot(now),
                time_ms=now,
                policy=PublishPolicy.BEST_EFFORT,
            )
            for robot in robots
        ]

    def __tick(self) -> None:
        """Move the simulator forward an amount of 'dt' time."""
        self.__clock.tick()
        self.__world.time_ms = self.__clock.time_ms()

        commands = self.__drain_commands()

        events = self.__step(self.__dt_s, commands)
        self.__event_publisher.enqueue_all(events)

    def __cancel_current_task(self, robot: Robot) -> None:
        task_id = robot.assigned_task_id
        robot.assigned_task_id = None
        robot.intent = None
        robot.state = RobotState.IDLE
        if task_id is not None:
            self.__world.tasks[task_id].status = TaskStatus.CANCELLED
            # del self.__tasks[task_id]

    def __execute_command(self, command: CommandBase) -> None:
        logging_context.clear_context()

        logging_context.bind_context(
            {
                'command_id': command.id,
                'robot_id': command.robot_id,
            }
        )

        robot = self.__world.robots.get(command.robot_id)
        if robot is None:
            return

        try:
            match command:
                case AssignTaskCommand():
                    self.__cancel_current_task(
                        robot,
                    )  # Cancel previous task if the robot is being assigned to the new task

                    robot.assigned_task_id = command.task_id
                    self.__world.tasks[command.task_id].status = TaskStatus.ASSIGNED
                case CancelTaskCommand():
                    self.__cancel_current_task(robot)
                case MoveToCommand():
                    robot.intent = RobotGoal(type=RobotGoalType.MOVE, pos=command.pos)
                case _:
                    _logger.error(
                        f'Tried to execute unsupported command type: {command!r}'
                    )
                    raise ValueError(f'Unsupported command type: {command!r}')
        finally:
            logging_context.clear_context()

    def __is_intent_done(self, robot: Robot) -> bool:
        if robot.intent is None:
            return True

        if robot.intent.type == RobotGoalType.WAIT:
            return robot.intent.wait_remaining_ms == 0.0

        assert robot.intent.pos is not None

        dx = robot.intent.pos[0] - robot.pos[0]
        dy = robot.intent.pos[1] - robot.pos[1]
        return dx**2 + dy**2 <= robot.arrive_eps_m**2

    def __execute_robot_task(self, robot: Robot, dt_s: NonNegativeFloat) -> None:
        if robot.assigned_task_id is None and robot.intent is None:
            return

        if self.__is_intent_done(robot):
            robot.intent = None

            task_id = robot.assigned_task_id
            if task_id is None:
                return
            task = self.__world.tasks.get(task_id)
            if task is None:
                return

            advance_phase(task, robot)

            if task.status == TaskStatus.COMPLETED:
                # no more task to do, reset robot state
                robot.assigned_task_id = None
                robot.state = RobotState.IDLE

                now = self.sim_time_ms

                event = TaskCompletedEvent(
                    id=task.id,
                    timestamp_ms=now,
                    duration_ms=0,
                )
                self.__event_publisher.enqueue_all(
                    [
                        PublishRequest(
                            topic='TASK:COMPLETED',
                            payload=event,
                            time_ms=now,
                            policy=PublishPolicy.RELIABLE,
                        ),
                    ],
                )

            return

        if robot.intent.type == RobotGoalType.MOVE:
            self.__move_robot(robot, dt_s)
        else:
            self.__update_wait_remaining(robot, dt_s)

    def __move_robot(self, robot: Robot, dt_s: NonNegativeFloat) -> None:
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
        ) not in self.__world.map.obstacles:
            robot.pos = new_pos

    def __update_wait_remaining(self, robot: Robot, dt_s: NonNegativeFloat) -> None:
        assert (
            robot.intent is not None
            and robot.intent.type == RobotGoalType.WAIT
            and robot.intent.wait_remaining_ms is not None
        )

        robot.intent.wait_remaining_ms = max(
            0,
            robot.intent.wait_remaining_ms - int(dt_s * 1000),
        )
