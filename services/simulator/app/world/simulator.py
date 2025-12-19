# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

import asyncio
import math
import queue
import threading
from collections.abc import Generator
from queue import Queue
from time import monotonic

from pydantic import NonNegativeFloat

from app.infra.bus.event_bus import EventBus
from app.infra.mappers import task_mapper
from app.infra.mappers.robot_state_mapper import snapshot_to_proto
from app.types import IDType

from .models.command import AssignTaskCommand, CancelTaskCommand, Command, MoveToCommand
from .models.robot import Robot, RobotGoal, RobotState
from .models.task import Task, TaskStatus
from .models.world import World
from .types import Position


def StateTransitionIter(task: Task) -> Generator[tuple[RobotState, RobotGoal | None]]:
    yield (RobotState.MOVING, RobotGoal(pos=task.pickup))
    yield (RobotState.PICKING, None)
    yield (RobotState.MOVING, RobotGoal(pos=task.dropoff))
    yield (RobotState.DROPPING, None)


def distance(a: Position, b: Position) -> float:
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.sqrt(dx**2 + dy**2)


class Simulator[T]:
    def __init__(self, world: World, bus: EventBus[T]) -> None:
        self.__world = world
        self.__tick_hz = 10
        self.__command_queue = Queue[Command]()

        self.__tasks: dict[IDType, Task] = {}
        self.__state_transition_iters: dict[
            IDType, Generator[tuple[RobotState, RobotGoal | None]]
        ] = {}

        self.__bus = bus
        self.__stop = threading.Event()
        self.__t0: float | None = None

    def register_command(self, command: Command) -> None:
        """Register a command to be executed."""
        self.__command_queue.put_nowait(command)

    def create_task(
        self,
        pickup: Position,
        dropoff: Position,
        duration_s: float,
    ) -> None:
        """Create an unassigned pickup/dropoff task."""
        task = Task(
            pickup=pickup,
            dropoff=dropoff,
            status=TaskStatus.CREATED,
            deadline_ms=int(self.sim_time + duration_s * 1000),
        )
        self.__tasks[task.id] = task
        self.__state_transition_iters[task.id] = StateTransitionIter(task)

        event_to_publish = task_mapper.taskcreated_snapshot_to_proto(
            task.snapshot(),
            self.sim_time,
        )
        self.__bus.publish_event('TASK:CREATED', event_to_publish.SerializeToString())

    @property
    def sim_time(self) -> float:
        """Return the simulator time in seconds."""
        if self.__t0 is None:
            raise ValueError('Cannot access sim_time: Invalid t0 reference')

        return monotonic() - self.__t0

    async def start(self) -> None:
        """Start the simulation."""
        self.__stop.clear()
        self.__t0 = monotonic()
        dt = 1.0 / self.__tick_hz
        try:
            while not self.__stop.is_set():
                t0 = monotonic()
                await self.__tick(dt_s=max(0.0, dt - 0.001))
                elapsed = monotonic() - t0
                await asyncio.sleep(max(0, dt - elapsed))

        except Exception as e:
            print(f'Simulator crashed: {e!r}')

    def stop(self) -> None:
        """Stop event loop."""
        self.__stop.set()
        self.__t0 = None

    async def __tick(self, dt_s: NonNegativeFloat) -> None:
        """Move the simulator forward an amount of 'dt' time."""
        # t_end = monotonic() + dt
        while True:
            try:
                cmd = self.__command_queue.get_nowait()
            except queue.Empty:
                break
            self.__execute_command(cmd)

        for robot in self.__world.robots.values():
            self.__execute_robot_task(robot, dt_s)
            self.__publish_robot_state(robot)

    # --------------------------------PUBLISHING----------------------------------- #

    def __publish_task_completed_event(self, task_id: IDType, robot_id: IDType) -> None:
        task_snapshot = self.__tasks[task_id].snapshot()
        proto_msg = task_mapper.taskcompleted_snapshot_to_proto(
            task_snapshot, str(robot_id), self.sim_time
        )
        self.__bus.publish_event('TASK:COMPLETED', proto_msg.SerializeToString())

    def __publish_robot_state(self, robot: Robot) -> None:
        proto_msg = snapshot_to_proto(robot.snapshot(), self.sim_time).SerializeToString()
        self.__bus.publish_event('ROBOT_STATE', proto_msg)

    # ----------------------------------------------------------------------------- #

    def __cancel_current_task(self, robot: Robot) -> None:
        task_id = robot.assigned_task_id
        robot.assigned_task_id = None
        robot.intent = None
        robot.state = RobotState.IDLE
        if task_id is not None:
            self.__tasks[task_id].status = TaskStatus.CANCELLED
            del self.__tasks[task_id]

    def __execute_command(self, command: Command) -> None:
        robot = self.__world.robots[command.robot_id]

        if isinstance(command, AssignTaskCommand):
            self.__cancel_current_task(
                robot
            )  # Cancel previous task if the robot is being assigned to the new task

            robot.assigned_task_id = command.task_id
            self.__tasks[command.task_id].status = TaskStatus.ASSIGNED
        elif isinstance(command, CancelTaskCommand):
            self.__cancel_current_task(robot)
        elif isinstance(command, MoveToCommand):  # pyright: ignore
            robot.intent = RobotGoal(pos=command.pos)

    def __is_intent_done(self, robot: Robot) -> bool:
        if robot.intent is None:
            return True

        if robot.intent.wait_remaining is not None:
            return robot.intent.wait_remaining == 0.0

        assert robot.intent.pos is not None

        dist = distance(robot.intent.pos, robot.pos)
        return dist <= 0.05

    # def __perform_task_state_transition(self, robot: Robot) -> None:
    #     pass

    def __clean_task(self, task_id: IDType) -> None:
        del self.__tasks[task_id]
        del self.__state_transition_iters[task_id]

    def __execute_robot_task(self, robot: Robot, dt_s: NonNegativeFloat) -> None:
        if robot.assigned_task_id is None and robot.intent is None:
            return

        task_id = robot.assigned_task_id

        if self.__is_intent_done(robot):
            robot.intent = None
            if task_id is None:
                return
            next_transition = next(self.__state_transition_iters[task_id], None)
            if next_transition is None:
                # no more task to do, reset robot state
                robot.assigned_task_id = None
                robot.state = RobotState.IDLE

                self.__tasks[task_id].status = TaskStatus.COMPLETED
                self.__publish_task_completed_event(task_id, robot.id)
                self.__clean_task(task_id)
                return

            robot.state = next_transition[0]
            robot.intent = next_transition[1]
            return

        if robot.intent is None:
            return

        if robot.intent.pos is not None:
            self.__move_robot(robot, dt_s)
        else:
            self.__update_wait_remaining(robot, dt_s)

    def __move_robot(self, robot: Robot, dt_s: NonNegativeFloat) -> None:
        assert robot.intent is not None and robot.intent.pos is not None

        dist = distance(robot.intent.pos, robot.pos)
        dx = robot.intent.pos[0] - robot.pos[0]
        dy = robot.intent.pos[1] - robot.pos[1]
        new_pos = (
            robot.pos[0] + dx / dist * dt_s,
            robot.pos[1] + dy / dist * dt_s,
        )
        if (
            math.floor(new_pos[0]),
            math.floor(new_pos[1]),
        ) not in self.__world.map.obstacles:
            robot.pos = new_pos

    def __update_wait_remaining(self, robot: Robot, dt_s: NonNegativeFloat) -> None:
        assert robot.intent is not None and robot.intent.wait_remaining is not None

        robot.intent.wait_remaining = max(0.0, robot.intent.wait_remaining - dt_s)
