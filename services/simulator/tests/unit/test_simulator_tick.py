import dataclasses
from collections.abc import Callable, Iterable
from uuid import uuid4

import pytest
from app.application.dtos.qos_policy import QoSPolicy
from app.application.events.domain_event import DomainEvent
from app.application.interfaces.ports.event_publisher import EventPublisher
from app.application.simulator import Simulator
from app.domain.models.robot import Robot, RobotState

# import your Simulator, World, Robot, Task, Commands, DomainEvent, etc.

class World:
    def __init__(self, robots: Iterable[Robot]) -> None:
        self.robots = {r.id: r for r in robots}
        self.time_ms = 0

@pytest.fixture
def world_factory() -> Callable[..., World]:
    # Adjust this to your real World constructor
    def _make_world(*, robots: Iterable[Robot]) -> World:
        return World(robots)
    return _make_world

@pytest.fixture
def sim_factory() -> Callable[[World, EventPublisher], Simulator]:
    def wrapper(world: World, event_publisher: EventPublisher) -> Simulator:
        sim = Simulator(
            world=world,
            event_publisher=event_publisher,
        )
        sim._Simulator__clock.start()
        return sim

    return wrapper


# @pytest.fixture
# def simulator_factory(monkeypatch):
#     """
#     This factory assumes your Simulator takes (world, event_publisher, clock, dt_s ...)
#     If your constructor differs, adapt wiring here once, keep tests unchanged.
#     """
#     def _make_simulator(*, SimulatorCls, world, publisher, clock, dt_s=0.1):
#         sim = SimulatorCls(world=world, event_publisher=publisher, clock=clock, dt_s=dt_s)
#         return sim
#     return _make_simulator

class FakePublisher:
    def __init__(self) -> None:
        self.events: list[DomainEvent] = []

    def enqueue_all(self, items: Iterable[DomainEvent]) -> None:
        self.events.extend(items)


def run_ticks(sim: Simulator, n: int) -> None:
    for _ in range(n):
        sim.tick_once()


# @pytest.fixture
# def world_factory() -> Callable[..., World]:
#     def wrapper(num_robots: int, num_tasks: int = 0) -> World:
#         W, H = (100, 100)
#         robots = {(rid := uuid4()): Robot((0.0, i), id=rid) for i in range(num_robots)}
#         tasks = {
#             (tid := uuid4()): Task(
#                 id=tid,
#                 pickup=(random.randint(0, W - 1), random.randint(0, H - 1)),
#                 dropoff=(random.randint(0, W - 1), random.randint(0, H - 1)),
#                 deadline_ms=100000,
#             )
#             for _ in range(num_tasks)
#         }
#         return World(
#             map=Map(W, H, set()),
#             robots=robots,
#             tasks=tasks,
#         )
#
#     return wrapper
#
#
# @pytest.fixture
# def make_simulator() -> Callable[[World, EventPublisher], Simulator]:
#     def wrapper(world: World, publisher: EventPublisher) -> Simulator:
#         sim = Simulator(
#             world=world,
#             event_publisher=publisher,
#         )
#         sim._Simulator__clock.start()
#         return sim
#
#     return wrapper


# @pytest.fixture
# def make_assign_cmd() -> Callable[..., AssignTaskCommand]:
#     def wrapper(robot_id: IDType, task_id: IDType, cmd_id: IDType) -> AssignTaskCommand:
#         return AssignTaskCommand(
#             id=cmd_id,
#             robot_id=robot_id,
#             task_id=task_id,
#             issued_at_ms=0,
#             policy=CommandPolicy.MUST,
#         )
#
#     return wrapper

#
# def test_tick_emits_robot_state_for_each_robot(
#     make_world: Callable[..., World],
#     make_simulator: Callable[..., Simulator],
# ):
#     world = make_world(3)
#     publisher = FakePublisher()
#     sim = make_simulator(world, publisher)
#
#     sim.tick_once()
#
#     robot_events = [e for e in publisher.events if e.topic == 'ROBOT_STATE']
#     assert len(robot_events) == 3
#
#
# def test_tick_timestamp_matches_world_time(
#     make_world: Callable[..., World],
#     make_simulator: Callable[..., Simulator],
# ):
#     world = make_world(1)
#     publisher = FakePublisher()
#     sim = make_simulator(world, publisher)
#
#     sim.tick_once()
#
#     assert world.time_ms > 0
#     e = next(ev for ev in publisher.events if ev.topic == 'ROBOT_STATE')
#     assert e.time_ms == world.time_ms
#     # If your snapshot carries time, assert it too:
#     # assert e.payload.time_ms == world.time_ms
#
#
# def test_duplicate_command_is_ignored(
#     make_world: Callable[..., World],
#     make_simulator: Callable[..., Simulator],
#     make_assign_cmd: Callable[..., CommandBase],
# ):
#     world = make_world(1, 1)
#     publisher = FakePublisher()
#     sim = make_simulator(world, publisher)
#
#     robot_id = next(iter(world.robots.keys()))
#     task_id = next(iter(world.tasks.keys()))
#
#     cmd = make_assign_cmd(robot_id=robot_id, task_id=task_id, cmd_id='X')
#     sim.register_command(cmd)
#     sim.register_command(cmd)  # duplicate same id
#
#     run_ticks(sim, 1)
#
#     robot = world.robots[robot_id]
#     assert robot.assigned_task_id == task_id

def test_step_emits_robot_state_event_per_robot(world_factory: Callable[..., World], sim_factory: Callable[..., Simulator]) -> None:
    # Build world with 3 robots

    robots = [Robot(pos=(0.0, 0.0), id=uuid4()) for _ in range(3)]
    world = world_factory(robots=robots)

    publisher = FakePublisher()

    sim = sim_factory(world=world, event_publisher=publisher)

    sim.tick_once()

    robot_events = [e for e in publisher.events if e.topic == "ROBOT_STATE"]
    assert len(robot_events) == 3

    assert all(e.policy == QoSPolicy.BEST_EFFORT for e in robot_events)


def test_event_time_matches_world_time_and_snapshot_time(world_factory: Callable[..., World], sim_factory: Callable[..., Simulator]):
    robots = [Robot(pos=(1.0, 2.0), id=uuid4())]
    world = world_factory(robots=robots)


    publisher = FakePublisher()
    sim = sim_factory(world=world, event_publisher=publisher)

    sim.tick_once()

    assert world.time_ms == 100

    ev = next(e for e in publisher.events if e.topic == "ROBOT_STATE")
    snap = ev.payload

    assert ev.time_ms == world.time_ms
    assert snap.timestamp_ms == world.time_ms


def test_snapshot_is_frozen(world_factory: Callable[..., World], sim_factory: Callable[..., Simulator]):
    robots = [Robot(pos=(1.0, 2.0), id=uuid4())]
    world = world_factory(robots=robots)

    publisher = FakePublisher()
    sim = sim_factory(world=world, event_publisher=publisher)

    sim.tick_once()

    ev = next(e for e in publisher.events if e.topic == "ROBOT_STATE")
    snap = ev.payload

    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.timestamp_ms = 999  # type: ignore[misc]


def test_snapshot_fields_match_robot(world_factory: Callable[..., World], sim_factory: Callable[..., Simulator]):
    robot = Robot(pos=(3.0, 4.0), id=uuid4())
    robot.state = RobotState.IDLE
    world = world_factory(robots=[robot])


    publisher = FakePublisher()
    sim = sim_factory(world=world, event_publisher=publisher)

    sim.tick_once()

    ev = next(e for e in publisher.events if e.topic == "ROBOT_STATE")
    snap = ev.payload

    assert snap.id == robot.id
    assert snap.pos == robot.pos
    assert snap.state == robot.state
    assert snap.battery == robot.battery
    assert snap.assigned_task_id == robot.assigned_task_id
    assert snap.task_phase == robot.task_phase


def test_tick_increments_time_monotonically(world_factory: Callable[..., World], sim_factory: Callable[..., Simulator]):
    robots = [Robot(pos=(0.0, 0.0), id=uuid4())]
    world = world_factory(robots=robots)


    publisher = FakePublisher()
    sim = sim_factory(world=world, event_publisher=publisher)

    run_ticks(sim, 3)

    times = [e.time_ms for e in publisher.events if e.topic == "ROBOT_STATE"]
    # 3 ticks * 1 robot => 3 events
    assert times == [100, 200, 300]

