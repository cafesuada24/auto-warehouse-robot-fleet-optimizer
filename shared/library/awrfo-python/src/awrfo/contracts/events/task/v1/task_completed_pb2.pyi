import datetime

from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import duration_pb2 as _duration_pb2
from awrfo.contracts.envelopes.event_envelope.v1 import event_envelope_pb2 as _event_envelope_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TaskCompletedEvent(_message.Message):
    __slots__ = ()
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    ROBOT_ID_FIELD_NUMBER: _ClassVar[int]
    DURATION_S_FIELD_NUMBER: _ClassVar[int]
    BATTERY_USED_FIELD_NUMBER: _ClassVar[int]
    envelope: _event_envelope_pb2.EventEnvelope
    task_id: str
    robot_id: str
    duration_s: _duration_pb2.Duration
    battery_used: float
    def __init__(self, envelope: _Optional[_Union[_event_envelope_pb2.EventEnvelope, _Mapping]] = ..., task_id: _Optional[str] = ..., robot_id: _Optional[str] = ..., duration_s: _Optional[_Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]] = ..., battery_used: _Optional[float] = ...) -> None: ...
