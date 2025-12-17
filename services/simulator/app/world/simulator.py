import asyncio
import queue
from queue import Queue
from time import monotonic
from typing import Literal

from app.world.world import World


class Simulator:
    type Command = Literal['WAIT', 'MOVE_TO', 'PICKUP', 'DROPOFF']

    def __init__(self, world: World) -> None:
        self.__world = world
        self.__tick_hz = 10
        self.__running = False
        self.__command_queue = Queue[tuple[Simulator.Command, str]]()

    def register_command(self, command: Command, data: str) -> None:
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
                await asyncio.sleep(max(0, dt - (monotonic() - t0)))

        except Exception as e:
            print(f'Simulator crashed: {e!r}')

    def stop(self) -> None:
        """Stop event loop."""
        self.__running = False

    async def __tick(self, dt: float) -> None:
        """Move the simulator forward an amount of 'dt' time."""
        t_end = monotonic() + dt
        while monotonic() < t_end:
            try:
                cmd = self.__command_queue.get_nowait()
            except queue.Empty:
                break

            print(f'Executing {cmd}')

