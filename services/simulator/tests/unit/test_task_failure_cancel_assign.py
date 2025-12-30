from collections.abc import Iterable
from uuid import UUID, uuid4

import pytest
from app.application.commands.policy import CommandPolicy
from app.application.commands.task_commands import AssignTaskCommand, CancelTaskCommand
from app.application.dtos.qos_policy import QoSPolicy
from app.application.simulator import Simulator
from app.domain.models.map import Map
from app.domain.models.robot import Robot, RobotState
from app.domain.models.task import Task, TaskStatus
from app.domain.models.world import World

from .common import FakePublisher

# -----------------------
# Test double
# -----------------------


# class FakePublisher:
#     def __init__(self) -> None:
#         self.events: list[DomainEvent] = []
#
#     def enqueue_all(self, items: Iterable[DomainEvent]) -> None:
#         self.events.extend(list(events))


def events_by_topic(pub: FakePublisher, topic: str):
    return [e for e in pub.events if getattr(e, 'topic', None) == topic]

def make_world() -> tuple[World, list[Robot], list[Task]]:
    ...


# -----------------------
# Builders
# -----------------------

ROBOT_ID_1 = UUID('00000000-0000-0000-0000-000000000001')
ROBOT_ID_2 = UUID('00000000-0000-0000-0000-000000000002')
TASK_ID_1 = UUID('00000000-0000-0000-0000-000000000101')
TASK_ID_2 = UUID('00000000-0000-0000-0000-000000000102')


def make_world_with_two_tasks() -> tuple[World, Robot, Robot, Task, Task]:
    """
    Minimal world:
      - 1 or 2 robots
      - 2 tasks
    Replace map=None with a real empty map if your World requires it.
    """
    r1 = Robot(pos=(0.0, 0.0), id=ROBOT_ID_1)
    r2 = Robot(pos=(5.0, 5.0), id=ROBOT_ID_2)

    t1 = Task(
        pickup=(0.0, 0.0),
        dropoff=(0.0, 0.0),
        status=TaskStatus.CREATED,
        deadline_ms=0,
        id=TASK_ID_1,
    )
    t2 = Task(
        pickup=(0.0, 0.0),
        dropoff=(0.0, 0.0),
        status=TaskStatus.CREATED,
        deadline_ms=0,
        id=TASK_ID_2,
    )

    world = World(
        map=Map(100, 100, set()),
        robots={r1.id: r1, r2.id: r2},
        tasks={t1.id: t1, t2.id: t2},
        time_ms=0,
    )
    return world, r1, r2, t1, t2


# -----------------------
# TASK:FAILED tests
# -----------------------


def test_task_failed_emitted_once_when_deadline_passed() -> None:
    world, r1, _, t1, _ = make_world_with_two_tasks()
    pub = FakePublisher()
    sim = Simulator(world=world, event_publisher=pub)
    sim._Simulator__clock.start()

    # Deadline in the near future; adjust for your clock tick size.
    t1.deadline_ms = 150

    # Assign task
    sim.register_command(
        AssignTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t1.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        ),
    )

    # Run enough ticks to pass deadline
    sim.tick_many(20)

    failed = events_by_topic(pub, 'TASK:FAILED')
    assert len(failed) == 1, 'TASK:FAILED must be emitted exactly once'


def test_task_failed_is_reliable_policy():
    world, r1, _, t1, _ = make_world_with_two_tasks()
    pub = FakePublisher()
    sim = Simulator(world=world, event_publisher=pub)
    sim._Simulator__clock.start()

    t1.deadline_ms = 150

    sim.register_command(
        AssignTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t1.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        ),
    )

    sim.tick_many(20)


    failed = events_by_topic(pub, 'TASK:FAILED')
    assert failed, 'Expected TASK:FAILED'
    assert failed[0].policy == QoSPolicy.RELIABLE


def test_failure_clears_robot_fields() -> None:
    world, r1, _, t1, _ = make_world_with_two_tasks()
    pub = FakePublisher()
    sim = Simulator(world=world, event_publisher=pub)
    sim._Simulator__clock.start()

    t1.deadline_ms = 150

    sim.register_command(
        AssignTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t1.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        ),
    )


    sim.tick_many(20)

    assert events_by_topic(pub, 'TASK:FAILED'), 'Expected TASK:FAILED'

    assert r1.assigned_task_id is None
    assert r1.intent is None
    assert r1.task_phase is None
    assert r1.state == RobotState.IDLE


def test_failure_stops_task_progression_no_completion_after_failed() -> None:
    world, r1, _, t1, _ = make_world_with_two_tasks()
    pub = FakePublisher()
    sim = Simulator(world=world, event_publisher=pub)
    sim._Simulator__clock.start()

    # Set deadline very early so failure occurs immediately
    t1.deadline_ms = 1

    sim.register_command(
        AssignTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t1.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        ),
    )

    sim.tick_many(20)


    assert events_by_topic(pub, 'TASK:FAILED'), 'Expected TASK:FAILED'
    assert not events_by_topic(pub, 'TASK:COMPLETED'), 'Must not complete after failure'


# -----------------------
# CANCEL / ASSIGN ordering tests
# -----------------------


def test_cancel_task_emits_cancelled_once_and_clears_robot() -> None:
    world, r1, _, t1, _ = make_world_with_two_tasks()
    pub = FakePublisher()
    sim = Simulator(world=world, event_publisher=pub)
    sim._Simulator__clock.start()

    t1.deadline_ms = 200

    # Assign
    sim.register_command(
        AssignTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t1.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        ),
    )
    sim.tick_once()

    # Cancel
    sim.register_command(
        CancelTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t1.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        ),
    )
    sim.tick_many(5)

    cancelled = events_by_topic(pub, 'TASK:CANCELLED')
    assert len(cancelled) == 1, 'TASK:CANCELLED must be emitted once'

    assert r1.assigned_task_id is None
    assert r1.intent is None
    assert r1.task_phase is None
    assert r1.state == RobotState.IDLE


def test_assign_new_task_cancels_old_first_in_event_order() -> None:
    world, r1, _, t1, t2 = make_world_with_two_tasks()
    pub = FakePublisher()
    sim = Simulator(world=world, event_publisher=pub)
    sim._Simulator__clock.start()

    t1.deadline_ms = 200
    t2.deadline_ms = 400
    # Assign old task
    sim.register_command(
        AssignTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t1.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        )
    )
    sim.tick_once()

    # Reassign to new task (should cancel old first)
    sim.register_command(
        AssignTaskCommand(
            id=uuid4(),
            robot_id=r1.id,
            task_id=t2.id,
            timestamp_ms=0,
            policy=CommandPolicy.MUST,
        ),
    )
    sim.tick_once()

    idx_cancel = next(
        i
        for i, e in enumerate(pub.events)
        if getattr(e, 'topic', None) == 'TASK:CANCELLED'
        and getattr(e.payload, 'task_id', None) == t1.id
    )
    idx_assign = next(
        i
        for i, e in enumerate(pub.events)
        if getattr(e, 'topic', None) == 'TASK:ASSIGNED'
        and getattr(e.payload, 'task_id', None) == t2.id
    )
    assert idx_cancel < idx_assign, (
        'Reassignment must cancel old task before assigning new one'
    )
