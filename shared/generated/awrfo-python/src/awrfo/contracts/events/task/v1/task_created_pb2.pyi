import datetime

from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import duration_pb2 as _duration_pb2
from awrfo.contracts.envelopes.event_envelope.v1 import event_envelope_pb2 as _event_envelope_pb2
from awrfo.contracts.schemas.common.v1 import coordinate_pb2 as _coordinate_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TaskCreatedPayload(_message.Message):
    __slots__ = ()
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    DURATION_S_FIELD_NUMBER: _ClassVar[int]
    PICKUP_FIELD_NUMBER: _ClassVar[int]
    DROPOFF_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_S_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    duration_s: _duration_pb2.Duration
    pickup: _coordinate_pb2.Coordinate
    dropoff: _coordinate_pb2.Coordinate
    deadline_s: int
    def __init__(self, task_id: _Optional[str] = ..., duration_s: _Optional[_Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]] = ..., pickup: _Optional[_Union[_coordinate_pb2.Coordinate, _Mapping]] = ..., dropoff: _Optional[_Union[_coordinate_pb2.Coordinate, _Mapping]] = ..., deadline_s: _Optional[int] = ...) -> None: ...

class TaskCreatedEvent(_message.Message):
    __slots__ = ()
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    envelope: _event_envelope_pb2.EventEnvelope
    payload: TaskCreatedPayload
    def __init__(self, envelope: _Optional[_Union[_event_envelope_pb2.EventEnvelope, _Mapping]] = ..., payload: _Optional[_Union[TaskCreatedPayload, _Mapping]] = ...) -> None: ...
