import math

from awrfo.contracts.events.task.v1.task_assignment_accepted_pb2 import TaskAssignmentAccepted
import pytest
from app.application.allocator import Allocator
from app.application.ports.event_bus import EventMessage
from awrfo.contracts.commands.v1.action_command_pb2 import ActionCommand
from awrfo.contracts.commands.v1.command_type_pb2 import CommandType
from awrfo.contracts.events.task.v1.task_completed_pb2 import TaskCompletedEvent
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.schemas.robot.v1.robot_state_pb2 import RobotState
from awrfo.types import UUID
from pydantic import NonNegativeFloat

# -------------------------
# Fake bus
# -------------------------

R1_ID = UUID('00000000-0000-0000-0000-000000000001')
R2_ID = UUID('00000000-0000-0000-0000-000000000002')

T1_ID = UUID('00000000-0000-0000-0000-000000000101')
T2_ID = UUID('00000000-0000-0000-0000-000000000102')


class FakeBus:
    def __init__(self) -> None:
        self.inbox: list[EventMessage] = []
        self.published: list[tuple[str, bytes]] = []

    def push(self, topic: str, payload: bytes) -> None:
        self.inbox.append(EventMessage(topic=topic, payload=payload))

    def poll(self, timeout_s: NonNegativeFloat = 0.2) -> EventMessage | None:
        # ignore timeout for unit tests
        if not self.inbox:
            return None
        return self.inbox.pop(0)

    def publish(self, topic: str, payload: bytes) -> None:
        self.published.append((topic, payload))


# -------------------------
# Helpers to build protos
# -------------------------


def make_robot_state(
    *, rid: str, x: float, y: float, ts_ms: int, battery: float
) -> bytes:
    msg = RobotState(
        id=rid,
        ts_ms=ts_ms,
        battery=battery,
    )
    msg.position.x = x
    msg.position.y = y
    return msg.SerializeToString()


def make_task_created(*, tid: str, px: int, py: int, deadline_ms: int) -> bytes:
    msg = TaskCreatedEvent(
        task_id=tid,
        deadline_ms=deadline_ms,
    )
    msg.pickup.x = px
    msg.pickup.y = py
    # if your schema includes dropoff, set it too (optional)
    return msg.SerializeToString()


def drain_once(alloc: Allocator) -> None:
    """
    Execute one iteration of Allocator.start() loop without threads:
    - poll once
    - process message
    """
    msg = alloc._Allocator__bus.poll(0.0)  # access injected bus
    if msg is None:
        return
    alloc.on_message(topic=msg.topic, payload=msg.payload)  # call private


# -------------------------
# Tests
# -------------------------


def test_robot_state_projection_updates_latest_fields():
    bus = FakeBus()
    alloc = Allocator(bus=bus)

    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=1.0, y=2.0, ts_ms=10, battery=0.9),
    )
    drain_once(alloc)

    # update
    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=3.0, y=4.0, ts_ms=20, battery=0.5),
    )
    drain_once(alloc)

    robots = alloc._Allocator__robots
    assert R1_ID in robots
    rv = robots[R1_ID]
    assert rv.pos == (3.0, 4.0)
    assert rv.ts_ms == 20
    assert rv.battery == 0.5


def test_duplicate_task_created_is_ignored():
    bus = FakeBus()
    alloc = Allocator(bus=bus)

    payload = make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000)
    bus.push('TASK:CREATED', payload)
    drain_once(alloc)
    bus.push('TASK:CREATED', payload)  # duplicate
    drain_once(alloc)

    tasks = alloc._Allocator__tasks
    assert T1_ID in tasks
    assert len(tasks) == 1


def test_allocator_publishes_assign_task_to_lowest_bid_robot():
    bus = FakeBus()
    alloc = Allocator(bus=bus)

    # Two robots: r1 near pickup, r2 far
    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=1, battery=1.0),
    )
    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R2_ID), x=10.0, y=10.0, ts_ms=1, battery=1.0),
    )
    bus.push(
        'TASK:CREATED', make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000)
    )

    drain_once(alloc)
    drain_once(alloc)
    drain_once(alloc)

    assert bus.published, 'Expected a COMMAND publish'
    topic, payload = bus.published[-1]
    assert topic == 'COMMAND'

    cmd = ActionCommand.FromString(payload)
    assert cmd.type == CommandType.COMMAND_TYPE_ASSIGN_TASK
    assert cmd.assign_task.task_id == str(T1_ID)
    assert cmd.robot_id == str(R1_ID), 'Nearest robot should win in this setup'


def test_inflight_task_not_assigned_twice():
    bus = FakeBus()
    alloc = Allocator(bus=bus)

    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=1, battery=1.0),
    )
    bus.push(
        'TASK:CREATED', make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000)
    )

    drain_once(alloc)
    drain_once(alloc)

    first_count = len(bus.published)

    # Trigger another allocate attempt (e.g., robot_state updates again)
    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=2, battery=1.0),
    )
    drain_once(alloc)

    assert len(bus.published) == first_count, 'Inflight task must not be assigned again'


def test_task_completed_frees_robot_and_allows_next_assignment():
    bus = FakeBus()
    alloc = Allocator(bus=bus)

    # r1 idle, t1 arrives -> assigned to r1
    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=1, battery=1.0),
    )
    bus.push(
        'TASK:CREATED', make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000)
    )
    drain_once(alloc)
    drain_once(alloc)

    accepted = TaskAssignmentAccepted(
        task_id=str(T1_ID), robot_id=str(R1_ID),
    ).SerializeToString()

    bus.push('TASK:ASSIGNMENT:ACCEPTED', accepted)
    drain_once(alloc)

    # Simulate completion event -> frees r1
    completed = TaskCompletedEvent(
        task_id=str(T1_ID), robot_id=str(R1_ID)
    ).SerializeToString()
    bus.push('TASK:COMPLETED', completed)
    drain_once(alloc)

    # New task should be assigned again
    bus.push(
        'TASK:CREATED', make_task_created(tid=str(T2_ID), px=1, py=1, deadline_ms=1000)
    )
    drain_once(alloc)

    # Expect another publish
    cmds = [ActionCommand.FromString(p) for (t, p) in bus.published if t == 'COMMAND']
    assigned_tasks = [
        c.assign_task.task_id
        for c in cmds
        if c.type == CommandType.COMMAND_TYPE_ASSIGN_TASK
    ]
    assert str(T2_ID) in assigned_tasks


def test_robot_state_stale_update_is_dropped():
    bus = FakeBus()
    alloc = Allocator(bus=bus)

    # Newer update first
    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=10.0, y=10.0, ts_ms=20, battery=0.9),
    )
    drain_once(alloc)

    # Older update arrives late -> must be ignored
    bus.push(
        'ROBOT_STATE',
        make_robot_state(rid=str(R1_ID), x=1.0, y=2.0, ts_ms=10, battery=0.1),
    )
    drain_once(alloc)

    rv = alloc._Allocator__robots[R1_ID]
    assert rv.ts_ms == 20
    assert rv.pos == (10.0, 10.0)
    assert math.isclose(rv.battery, 0.9, rel_tol=1e-6)


def test_deterministic_winner_on_tie_bid_is_stable_across_runs():
    def run_once() -> str:
        bus = FakeBus()
        alloc = Allocator(bus=bus)

        # Same position + same battery => identical bids for both robots
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R1_ID), x=0.0, y=0.0, ts_ms=1, battery=1.0),
        )
        bus.push(
            'ROBOT_STATE',
            make_robot_state(rid=str(R2_ID), x=0.0, y=0.0, ts_ms=1, battery=1.0),
        )
        bus.push(
            'TASK:CREATED',
            make_task_created(tid=str(T1_ID), px=1, py=1, deadline_ms=1000),
        )

        drain_once(alloc)
        drain_once(alloc)
        drain_once(alloc)

        assert bus.published, 'Expected a COMMAND publish'
        _, payload = bus.published[-1]
        cmd = ActionCommand.FromString(payload)
        assert cmd.type == CommandType.COMMAND_TYPE_ASSIGN_TASK
        return cmd.robot_id

    winner1 = run_once()
    winner2 = run_once()

    assert winner1 == winner2
    assert winner1 == str(R1_ID)
