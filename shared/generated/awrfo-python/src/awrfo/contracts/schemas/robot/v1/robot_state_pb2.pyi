from buf.validate import validate_pb2 as _validate_pb2
from awrfo.contracts.schemas.common.v1 import coordinate_pb2 as _coordinate_pb2
from awrfo.contracts.envelopes.schema_envelope.v1 import schema_envelope_pb2 as _schema_envelope_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RobotStateType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[RobotStateType]
    IDLE: _ClassVar[RobotStateType]
    MOVING: _ClassVar[RobotStateType]
    WAITING: _ClassVar[RobotStateType]
    PICKING: _ClassVar[RobotStateType]
    DROPPING: _ClassVar[RobotStateType]
UNKNOWN: RobotStateType
IDLE: RobotStateType
MOVING: RobotStateType
WAITING: RobotStateType
PICKING: RobotStateType
DROPPING: RobotStateType

class RobotState(_message.Message):
    __slots__ = ()
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    TS_MS_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    BATTERY_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    envelope: _schema_envelope_pb2.SchemaEnvelope
    id: str
    ts_ms: int
    position: _coordinate_pb2.Coordinate
    battery: float
    state: RobotStateType
    def __init__(self, envelope: _Optional[_Union[_schema_envelope_pb2.SchemaEnvelope, _Mapping]] = ..., id: _Optional[str] = ..., ts_ms: _Optional[int] = ..., position: _Optional[_Union[_coordinate_pb2.Coordinate, _Mapping]] = ..., battery: _Optional[float] = ..., state: _Optional[_Union[RobotStateType, str]] = ...) -> None: ...
