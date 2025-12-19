from uuid import uuid4

from awrfo.contracts.envelopes.event_envelope.v1.event_envelope_pb2 import EventEnvelope
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.schemas.common.v1.coordinate_pb2 import Coordinate
from pydantic import NonNegativeFloat

from app.world.models.task import TaskSnapshot


def taskcreated_snapshot_to_proto(
    snapshot: TaskSnapshot, ts_s: NonNegativeFloat
) -> TaskCreatedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.created.v1',
        ts_ms=int(ts_s * 1000),
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskCreatedEvent(
        envelope=envelope,
        task_id=str(snapshot.id),
        pickup=Coordinate(
            x=snapshot.pickup[0],
            y=snapshot.pickup[1],
        ),
        dropoff=Coordinate(
            x=snapshot.dropoff[0],
            y=snapshot.dropoff[1],
        ),
        deadline_ms=snapshot.deadline_ms,
    )
