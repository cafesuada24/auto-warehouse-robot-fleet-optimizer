# Copyright (C) 2025 Cafesuada - All Rights Reserved
#
# This source code is protected under international copyright law.  All rights
# reserved and protected by the copyright holders.
# This file is confidential and only available to authorized individuals with the
# permission of the copyright holders.  If you encounter this file and do not have
# permission, please contact the copyright holders and delete this file.

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, TypedDict
from uuid import uuid4

from awrfo.logging.logger import setup_logging
from dotenv import load_dotenv
from fastapi import FastAPI

from app.application.simulator import Simulator
from app.domain.models.map import Map
from app.domain.models.robot import Robot
from app.domain.models.world import World
from app.infra.bus.event_bus import EventBus
from app.infra.bus.redis_bus import (
    RedisBusAdapter,
    RedisBusMessage,
)
from app.infra.event_publisher import EventPublisher
from app.infra.mappers.action_command_mapper import serialized_proto_to_command
from app.infra.mappers.mappers import get_model_converter
from app.infra.persistence.jsonl_event_store import JSONLEventStore

load_dotenv()

setup_logging()


class Context(TypedDict, total=False):
    event_bus: EventBus[RedisBusMessage] | None
    # world: World
    simulator: Simulator


context: Context = {}


# def _attach_command_handlers(
#     simulator: Simulator,
#     event_bus: EventBus,
#     *,
#     prefix: str = 'CMD',
# ) -> None:
#     for topic_str, cmd in zip(
#         ['WAIT', 'MOVE_TO', 'PICKUP', 'DROPOFF'],
#         [
#             Simulator.Command.WAIT,
#             Simulator.Command.MOVE_TO,
#             Simulator.Command.PICKUP,
#             Simulator.Command.DROPOFF,
#         ],
#         strict=True,
#     ):
#         event_bus.subscribe(
#             f'{prefix}:{topic_str}',
#             lambda msg, cmd=cmd: simulator.register_command(cmd, msg['data'].decode()),
#         )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, Any]:
    """Declare app lifespan."""
    global context

    robots = {(rid := uuid4()): Robot((0.0, i), id=rid) for i in range(2)}
    world = World(
        map=Map.random(
            size=(30, 30),
            seed=1234,
            num_obstacles=8,
        ),
        robots=robots,
    )
    # context['world'] = world

    event_bus = RedisBusAdapter()
    context['event_bus'] = event_bus

    # store = JSONLEventStore()

    for de in JSONLEventStore.iter_file('data/events.jsonl'):
        converter = get_model_converter(de.payload_type)
        cmd = converter(JSONLEventStore.decode_payload_bytes(de), de.time_ms)
        print(cmd)

    event_publisher = EventPublisher(bus=event_bus)
    simulator = Simulator(
        world=world,
        # bus=event_bus
        event_publisher=event_publisher,
    )
    context['simulator'] = simulator

    def _command_handler(msg: Any):
        now = simulator.sim_time_ms
        simulator.register_command(
            serialized_proto_to_command(msg['data'], ts_ms=now),
        )
        # store.store(
        #     topic='COMMAND',
        #     time_ms=simulator.sim_time_ms,
        #     policy=QoSPolicy.RELIABLE.value,
        #     payload_type=ActionCommand.DESCRIPTOR.full_name,
        #     payload_bytes=msg['data'],
        # )

    event_bus.subscribe(
        'COMMAND',
        _command_handler,
    )
    event_bus.start()
    event_publisher.start()
    simulator.start()

    await asyncio.sleep(2.0)
    simulator.create_task((10, 5), (20, 29), 60)

    yield

    simulator.stop()
    event_publisher.stop()
    # store.close()
    event_bus.cleanup()
    # sim_fut.cancel()

    # loop.call_soon_threadsafe(loop.stop)
    # thread.join(5)
    # loop.close()
    context = {}


app = FastAPI(lifespan=lifespan)


@app.post('/sim/reset')
def reset_sim() -> None:
    if (sim := context.get('simulator')) is None:
        return
    sim.reset()
