import asyncio
import queue
from enum import Enum
from queue import Queue
from time import monotonic

from app.infra.bus.event_bus import EventBus
from app.infra.mappers.robot_state_mapper import snapshot_to_proto

from .models.world import World


class SimulatorCommand(Enum):
    WAIT = 1
    MOVE_TO = 2
    PICKUP = 3
    DROPOFF = 4

class Simulator[T]:

    def __init__(self, world: World, bus: EventBus[T]) -> None:
        self.__world = world
        self.__tick_hz = 10
        self.__running = False
        self.__command_queue = Queue[tuple[SimulatorCommand, str]]()
        self.__bus = bus

    def register_command(self, command: SimulatorCommand, data: str) -> None:
        """Register a command to be executed."""
        self.__command_queue.put_nowait((command, data))


    async def start(self) -> None:
        """Start the simulation."""
        self.__running = True
        dt = 1.0 / self.__tick_hz
        try:
            while self.__running:
                t0 = monotonic()
                await self.__tick(dt=max(0.0, dt - 0.001))
                elapsed = monotonic() - t0
                await asyncio.sleep(max(0, dt - elapsed))
                self.__world.time += max(dt, elapsed)

        except Exception as e:
            print(f'Simulator crashed: {e!r}')

    def stop(self) -> None:
        """Stop event loop."""
        self.__running = False

    async def __tick(self, dt: float) -> None:
        """Move the simulator forward an amount of 'dt' time."""
        # t_end = monotonic() + dt
        while True:
            try:
                cmd = self.__command_queue.get_nowait()
            except queue.Empty:
                break

        for robot in self.__world.robots.values():
            proto_msg = snapshot_to_proto(robot.snapshot()).SerializeToString()
            self.__bus.publish_event("ROBOT_STATE", proto_msg)

