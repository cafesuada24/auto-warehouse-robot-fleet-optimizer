from buf.validate import validate_pb2 as _validate_pb2
from awrfo.contracts.envelopes.event_envelope.v1 import event_envelope_pb2 as _event_envelope_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TaskAssignmentRejectedEvent(_message.Message):
    __slots__ = ()
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    ASSIGNMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    ROBOT_ID_FIELD_NUMBER: _ClassVar[int]
    TS_MS_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    envelope: _event_envelope_pb2.EventEnvelope
    assignment_id: str
    task_id: str
    robot_id: str
    ts_ms: int
    reason: str
    def __init__(self, envelope: _Optional[_Union[_event_envelope_pb2.EventEnvelope, _Mapping]] = ..., assignment_id: _Optional[str] = ..., task_id: _Optional[str] = ..., robot_id: _Optional[str] = ..., ts_ms: _Optional[int] = ..., reason: _Optional[str] = ...) -> None: ...
