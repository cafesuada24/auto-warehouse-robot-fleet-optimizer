import dataclasses
import hashlib
import json
from collections.abc import Callable, Iterable
from uuid import UUID, uuid4

import pytest
from app.application.commands.policy import CommandPolicy
from app.application.commands.task_commands import AssignTaskCommand
from app.application.events.domain_event import DomainEvent
from app.application.simulator import Simulator
from app.domain.models.map import Map
from app.domain.models.robot import Robot
from app.domain.models.task import Task, TaskStatus
from app.domain.models.world import World


class FakePublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def enqueue_all(self, items: Iterable[DomainEvent]) -> None:
        self.events.extend(list(items))


def canonical(obj: object | None) -> object | None:
    """Convert payloads to a deterministic JSON-serializable form."""
    if dataclasses.is_dataclass(obj):
        return canonical(dataclasses.asdict(obj))
    if isinstance(obj, str | int | float | bool) or obj is None:
        return obj
    if isinstance(obj, dict):
        return {str(k): canonical(v) for k, v in obj.items()}
    if isinstance(obj, list | tuple):
        return [canonical(x) for x in obj]
    # fallback (should be avoided in core events)
    return repr(obj)


def hash_events(events: Iterable[DomainEvent]) -> str:
    rows: list[dict[str, object]] = []
    for e in events:
        rows.append(
            {
                'topic': e.topic,
                'time_ms': e.time_ms,
                'policy': str(e.policy),
                'payload': canonical(e.payload),
            },
        )
        print(canonical(e.payload))
    blob = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(blob).hexdigest()


@pytest.fixture
def make_sim_world() -> Callable[[], tuple[World, Robot, Task]]:
    """
    Adapt this to your actual constructors if needed.
    The goal is to create a deterministic world with:
      - 1 robot
      - 1 task
      - no obstacles
    """

    def _make() -> tuple[World, Robot, Task]:
        ROBOT_ID = UUID("00000000-0000-0000-0000-000000000001")
        TASK_ID  = UUID("00000000-0000-0000-0000-000000000002")
        robot = Robot(pos=(0.0, 0.0), id=ROBOT_ID)
        task = Task(
            id=TASK_ID,
            pickup=(0.0, 0.0),
            dropoff=(0.0, 0.0),
            status=TaskStatus.CREATED,
            deadline_ms=10_000,
        )
        world = World(
            map=Map.random((100, 100)),  # replace with real empty map if required
            robots={robot.id: robot},
            tasks={task.id: task},
            time_ms=0,
        )
        return world, robot, task

    return _make


def test_golden_determinism_hash(make_sim_world: Callable[[], tuple[World, Robot, Task]]) -> None:

    world, robot, task = make_sim_world()
    pub = FakePublisher()

    # Construct simulator; adapt args if your __init__ differs
    sim = Simulator(world=world, event_publisher=pub)

    # Deterministic command IDs and timestamps
    CMD_ID   = UUID("00000000-0000-0000-0000-000000000003")
    assign = AssignTaskCommand(
        id=CMD_ID,
        robot_id=robot.id,
        task_id=task.id,
        policy=CommandPolicy.MUST,
        # issued_at_ms=0,  # avoid wall clock; or omit if you remove it
        timestamp_ms=sim.sim_time_ms,
    )

    # Schedule: assign at tick 1
    sim.tick_once()
    sim.register_command(assign)
    sim.tick_many(5)

    got = hash_events(pub.events)

    # First run: print and pin this hash; after that, keep it fixed.
    # Replace the string below with the printed hash once.
    expected = 'f01e3fd0b40a92535282669d10027b8eecc3b2151ef497f2c6bd8c1e323defa8'
    assert got == expected

def test_two_runs_produce_same_hash(make_sim_world: Callable[[], tuple[World, Robot, Task]]) -> None:

    def run():
        world, robot, task = make_sim_world()
        pub = FakePublisher()
        sim = Simulator(world=world, event_publisher=pub)
        assign = AssignTaskCommand(
            id=uuid4(),
            robot_id=robot.id,
            task_id=task.id,
            policy=CommandPolicy.MUST,
            # issued_at_ms=0,
            timestamp_ms=sim.sim_time_ms,
        )
        sim.tick_once()
        sim.register_command(assign)
        sim.tick_many(5)
        return hash_events(pub.events)

    assert run() == run()
