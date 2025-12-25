from datetime import timedelta
from uuid import uuid4

from awrfo.contracts.envelopes.event_envelope.v1.event_envelope_pb2 import EventEnvelope
from awrfo.contracts.events.task.v1.task_completed_pb2 import TaskCompletedEvent
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.schemas.common.v1.coordinate_pb2 import Coordinate

from app.domain.models import task
from app.infra.mappers.mappers import convert_to_proto


@convert_to_proto.register
def taskcreated_event_to_proto(event: task.TaskCreatedEvent) -> TaskCreatedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.created.v1',
        ts_ms=event.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskCreatedEvent(
        envelope=envelope,
        task_id=str(event.id),
        pickup=Coordinate(
            x=event.pickup[0],
            y=event.pickup[1],
        ),
        dropoff=Coordinate(
            x=event.dropoff[0],
            y=event.dropoff[1],
        ),
        deadline_ms=event.deadline_ms,
    )


@convert_to_proto.register
def taskcompleted_event_to_proto(event: task.TaskCompletedEvent) -> TaskCompletedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.completed.v1',
        ts_ms=event.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskCompletedEvent(
        envelope=envelope,
        task_id=str(event.id),
        robot_id='',
        duration_s=timedelta(event.duration_ms / 1000.0),
        battery_used=0.0,
    )
