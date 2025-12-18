# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

import asyncio
import threading
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any, Protocol, TypedDict

from fastapi import FastAPI

from .bus.redis_bus import Command, RedisBusAdapter
from .world.models.world import World
from .world.simulator import Simulator


class EventBus(Protocol):
    def start(self) -> None: ...

    def subscribe(
        self,
        topic: str,
        callback: Callable[[Command], Any] | None = None,
    ) -> None: ...

    async def publish_event(self, topic: str, message: str): ...

    def cleanup(self) -> None: ...


class Context(TypedDict, total=False):
    event_bus: EventBus | None
    world: World
    simulator: Simulator


context: Context = {}


def _attach_command_handlers(
    simulator: Simulator,
    event_bus: EventBus,
    *,
    prefix: str = 'CMD',
) -> None:
    for topic_str, cmd in zip(
        ['WAIT', 'MOVE_TO', 'PICKUP', 'DROPOFF'],
        [
            Simulator.Command.WAIT,
            Simulator.Command.MOVE_TO,
            Simulator.Command.PICKUP,
            Simulator.Command.DROPOFF,
        ],
        strict=True,
    ):
        event_bus.subscribe(
            f'{prefix}:{topic_str}',
            lambda msg, cmd=cmd: simulator.register_command(cmd, msg['data'].decode()),
        )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, Any]:
    """Declare app lifespan."""
    global context

    world = World()
    context['world'] = world

    simulator = Simulator(world=world)
    context['simulator'] = simulator

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    thread = threading.Thread(
        target=loop.run_forever,
        daemon=True,
    )
    thread.start()

    await asyncio.sleep(0.1)

    sim_fut = asyncio.run_coroutine_threadsafe(
        simulator.start(),
        loop=loop,
    )

    event_bus = RedisBusAdapter()
    context['event_bus'] = event_bus
    _attach_command_handlers(
        simulator=simulator,
        event_bus=event_bus,
    )
    event_bus.start()

    yield

    event_bus.cleanup()
    simulator.stop()
    sim_fut.cancel()

    loop.call_soon_threadsafe(loop.stop)
    thread.join(5)
    loop.close()
    context = {}


app = FastAPI(lifespan=lifespan)
