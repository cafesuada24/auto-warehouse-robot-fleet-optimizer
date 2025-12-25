from buf.validate import validate_pb2 as _validate_pb2
from awrfo.contracts.envelopes.event_envelope.v1 import event_envelope_pb2 as _event_envelope_pb2
from awrfo.contracts.schemas.common.v1 import coordinate_pb2 as _coordinate_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TaskCreatedEvent(_message.Message):
    __slots__ = ()
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    PICKUP_FIELD_NUMBER: _ClassVar[int]
    DROPOFF_FIELD_NUMBER: _ClassVar[int]
    DEADLINE_MS_FIELD_NUMBER: _ClassVar[int]
    envelope: _event_envelope_pb2.EventEnvelope
    task_id: str
    pickup: _coordinate_pb2.Coordinate
    dropoff: _coordinate_pb2.Coordinate
    deadline_ms: int
    def __init__(self, envelope: _Optional[_Union[_event_envelope_pb2.EventEnvelope, _Mapping]] = ..., task_id: _Optional[str] = ..., pickup: _Optional[_Union[_coordinate_pb2.Coordinate, _Mapping]] = ..., dropoff: _Optional[_Union[_coordinate_pb2.Coordinate, _Mapping]] = ..., deadline_ms: _Optional[int] = ...) -> None: ...
