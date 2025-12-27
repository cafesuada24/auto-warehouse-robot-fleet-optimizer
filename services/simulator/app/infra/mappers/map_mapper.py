import uuid

from awrfo.contracts.envelopes.event_envelope.v1.event_envelope_pb2 import EventEnvelope
from awrfo.contracts.events.map.v1.map_updated_pb2 import (
    MapUpdatedEvent,
    MapUpdatedPayload,
)

from app.domain.models.map import Map, MapSnapshot

from .mappers import convert_to_proto


@convert_to_proto.register
def map_snapshot_to_proto(snapshot: MapSnapshot) -> MapUpdatedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid.uuid4()),
        event_type='map.updated.v1',
        ts_ms=snapshot.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    data = [0] * snapshot.width * snapshot.height
    for i, j in snapshot.obstacles:
        data[i * snapshot.width + j] = 1

    payload = MapUpdatedPayload(
        width=snapshot.width,
        height=snapshot.height,
        data=data,
    )

    return MapUpdatedEvent(
        envelope=envelope,
        payload=payload,
    )


def map_updated_proto_to_model(serialized: bytes) -> Map:
    mu = MapUpdatedEvent.FromString(serialized)
    payload = mu.payload
    obstacles: set[tuple[int, int]] = set()

    for index in range(len(payload.data)):
        if payload.data[index] == 1:
            obstacles.add((index // payload.width, index % payload.width))

    return Map(
        width=payload.width,
        height=payload.height,
        obstacles=obstacles,
    )
