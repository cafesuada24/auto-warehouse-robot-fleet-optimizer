from collections.abc import Iterable
from uuid import uuid4

import pytest
from app.application.commands.policy import CommandPolicy
from app.application.commands.task_commands import AssignTaskCommand
from app.application.dtos.qos_policy import QoSPolicy
from app.application.events.domain_event import DomainEvent
from app.application.simulator import Simulator
from app.domain.models.map import Map
from app.domain.models.robot import Robot
from app.domain.models.task import Task, TaskStatus
from app.domain.models.world import World

# -----------------------
# Test doubles / helpers
# -----------------------


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def enqueue_all(self, items: Iterable[DomainEvent]) -> None:
        self.events.extend(items)


def run_ticks(sim: Simulator, n: int) -> None:
    for _ in range(n):
        sim.tick_once()


def get_task_completed_events(publisher: FakePublisher):
    return [
        e for e in publisher.events if getattr(e, 'topic', None) == 'TASK:COMPLETED'
    ]


# -----------------------
# World builder
# -----------------------


def make_min_world() -> tuple[World, Robot, Task]:
    """
    Minimal world with 1 robot + 1 task that can complete quickly.
    Assumptions:
      - Task has fields: pickup, dropoff, status, deadline_ms, id (default)
      - World has dicts: robots, tasks, time_ms
    """
    robot = Robot(pos=(0.0, 0.0), id=uuid4())

    task = Task(
        pickup=(0.0, 0.0),
        dropoff=(0.0, 0.0),
        status=TaskStatus.CREATED,
        deadline_ms=10_000,
    )

    world = World(
        map=Map(100, 100, set()),
        robots={robot.id: robot},
        tasks={task.id: task},
        time_ms=0,
    )
    return world, robot, task


# -----------------------
# Tests you requested
# -----------------------


def test_task_completed_event_emitted_once() -> None:
    world, robot, task = make_min_world()
    publisher = FakePublisher()

    sim = Simulator(
        world=world, event_publisher=publisher
    )  # adjust ctor args if needed
    sim._Simulator__clock.start()

    # Assign task (MUST policy)
    assign_cmd = AssignTaskCommand(
        id=uuid4(),
        robot_id=robot.id,
        task_id=task.id,
        policy=CommandPolicy.MUST,
        # issued_at_ms=0,
        timestamp_ms=sim.sim_time_ms,
    )
    sim.register_command(assign_cmd)

    # Run enough ticks to complete
    run_ticks(sim, 10)

    completed = get_task_completed_events(publisher)
    assert len(completed) == 1, 'TASK:COMPLETED must be emitted exactly once per task'


def test_task_completed_event_time_matches_world_time() -> None:
    world, robot, task = make_min_world()
    publisher = FakePublisher()
    sim = Simulator(world=world, event_publisher=publisher)
    sim._Simulator__clock.start()

    assign_cmd = AssignTaskCommand(
        id=uuid4(),
        robot_id=robot.id,
        task_id=task.id,
        policy=CommandPolicy.MUST,
        # issued_at_ms=0,
        timestamp_ms=sim.sim_time_ms,
    )
    sim.register_command(assign_cmd)

    # Run until completion observed
    for _ in range(20):
        sim.tick_once()
        completed = get_task_completed_events(publisher)
        if completed:
            ev = completed[0]
            payload = ev.payload
            # DomainEvent.time_ms must equal world.time_ms at emission
            assert ev.time_ms == world.time_ms
            # Payload timestamp must match too (your TaskCompletedEvent uses timestamp_ms)
            assert getattr(payload, 'timestamp_ms') == world.time_ms
            return

    pytest.fail('No TASK:COMPLETED observed within expected ticks')


def test_task_completion_clears_robot_fields() -> None:
    world, robot, task = make_min_world()
    publisher = FakePublisher()
    sim = Simulator(world=world, event_publisher=publisher)
    sim._Simulator__clock.start()

    assign_cmd = AssignTaskCommand(
        id=uuid4(),
        robot_id=robot.id,
        task_id=task.id,
        policy=CommandPolicy.MUST,
        # issued_at_ms=0,
        timestamp_ms=sim.sim_time_ms,
    )
    sim.register_command(assign_cmd)

    run_ticks(sim, 20)

    assert get_task_completed_events(publisher), 'Expected TASK:COMPLETED'
    # Robot fields must be cleared by your advance_phase completion logic
    assert robot.assigned_task_id is None
    assert robot.intent is None
    assert robot.task_phase is None
    # Usually should be IDLE after completion
    assert robot.state.name == 'IDLE'  # avoids importing enum if paths differ


def test_task_completed_is_reliable_policy() -> None:
    world, robot, task = make_min_world()
    publisher = FakePublisher()
    sim = Simulator(world=world, event_publisher=publisher)
    sim._Simulator__clock.start()

    assign_cmd = AssignTaskCommand(
        id=uuid4(),
        robot_id=robot.id,
        task_id=task.id,
        policy=CommandPolicy.MUST,
        # issued_at_ms=0,
        timestamp_ms=sim.sim_time_ms,
    )
    sim.register_command(assign_cmd)

    run_ticks(sim, 20)

    completed = get_task_completed_events(publisher)
    assert completed, 'Expected TASK:COMPLETED'
    assert completed[0].policy == QoSPolicy.RELIABLE
