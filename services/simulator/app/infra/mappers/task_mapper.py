from datetime import timedelta
from uuid import uuid4

from awrfo.contracts.envelopes.event_envelope.v1.event_envelope_pb2 import EventEnvelope
from awrfo.contracts.events.task.v1.task_assigned_pb2 import TaskAssignedEvent
from awrfo.contracts.events.task.v1.task_cancelled_pb2 import TaskCancelledEvent
from awrfo.contracts.events.task.v1.task_completed_pb2 import TaskCompletedEvent
from awrfo.contracts.events.task.v1.task_created_pb2 import TaskCreatedEvent
from awrfo.contracts.events.task.v1.task_failed_pb2 import TaskFailedEvent
from awrfo.contracts.schemas.common.v1.coordinate_pb2 import Coordinate

from app.domain.events import task_events

from .mappers import convert_to_proto


@convert_to_proto.register
def taskcreated_event_to_proto(event: task_events.TaskCreatedEvent) -> TaskCreatedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.created.v1',
        ts_ms=event.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskCreatedEvent(
        envelope=envelope,
        task_id=str(event.task_id),
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
def taskassigned_event_to_proto(
    event: task_events.TaskAssignedEvent,
) -> TaskAssignedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.assigned.v1',
        ts_ms=event.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskAssignedEvent(
        envelope=envelope,
        task_id=str(event.task_id),
        robot_id=str(event.robot_id),
        ts_ms=event.timestamp_ms,
    )


@convert_to_proto.register
def taskcompleted_event_to_proto(
    event: task_events.TaskCompletedEvent,
) -> TaskCompletedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.completed.v1',
        ts_ms=event.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskCompletedEvent(
        envelope=envelope,
        task_id=str(event.task_id),
        robot_id=str(event.robot_id),
        duration_s=timedelta(event.duration_ms / 1000.0),
        battery_used=0.0,
    )


@convert_to_proto.register
def taskcancelled_event_to_proto(
    event: task_events.TaskCancelledEvent,
) -> TaskCancelledEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.cancelled.v1',
        ts_ms=event.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskCancelledEvent(
        envelope=envelope,
        task_id=str(event.task_id),
        robot_id=str(event.robot_id),
        ts_ms=event.timestamp_ms,
        reason=event.reason,
    )


@convert_to_proto.register
def taskfailed_event_to_proto(
    event: task_events.TaskFailedEvent,
) -> TaskFailedEvent:
    envelope = EventEnvelope(
        event_id=str(uuid4()),
        event_type='task.failed.v1',
        ts_ms=event.timestamp_ms,
        producer='simulator-service',
        envelope_version=1,
    )

    return TaskFailedEvent(
        envelope=envelope,
        task_id=str(event.task_id),
        robot_id=str(event.robot_id),
        ts_ms=event.timestamp_ms,
        reason=event.reason,
    )
