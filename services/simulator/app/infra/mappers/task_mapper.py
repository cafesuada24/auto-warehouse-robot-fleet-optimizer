from datetime import timedelta
from uuid import uuid4

from awrfo.contracts.envelopes.event_envelope.v1.event_envelope_pb2 import EventEnvelope
from awrfo.contracts.events.task.v1.task_completed_pb2 import TaskCompletedEvent
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.schemas.common.v1.coordinate_pb2 import Coordinate
from pydantic import NonNegativeInt

from app.world.models.task import TaskSnapshot


def taskcreated_snapshot_to_proto(
    snapshot: TaskSnapshot,
    ts_ms: NonNegativeInt,
) -> TaskCreatedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.created.v1',
        ts_ms=ts_ms,
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


def taskcompleted_snapshot_to_proto(
    snapshot: TaskSnapshot,
    robot_id: str,
    ts_ms: NonNegativeInt,
) -> TaskCompletedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.completed.v1',
        ts_ms=ts_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskCompletedEvent(
        envelope=envelope,
        task_id=str(snapshot.id),
        robot_id=robot_id,
        duration_s=timedelta(0.0),
        battery_used=0.0,
    )
