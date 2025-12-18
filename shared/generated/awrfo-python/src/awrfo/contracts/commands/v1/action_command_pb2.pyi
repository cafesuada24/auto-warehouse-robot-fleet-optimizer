import datetime

from buf.validate import validate_pb2 as _validate_pb2
from google.protobuf import duration_pb2 as _duration_pb2
from awrfo.contracts.schemas.common.v1 import coordinate_pb2 as _coordinate_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CommandType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WAIT: _ClassVar[CommandType]
    MOVE_TO: _ClassVar[CommandType]
    PICKUP: _ClassVar[CommandType]
    DROPOFF: _ClassVar[CommandType]
WAIT: CommandType
MOVE_TO: CommandType
PICKUP: CommandType
DROPOFF: CommandType

class CommandParams(_message.Message):
    __slots__ = ()
    TARGET_FIELD_NUMBER: _ClassVar[int]
    DURATION_S_FIELD_NUMBER: _ClassVar[int]
    target: _coordinate_pb2.Coordinate
    duration_s: _duration_pb2.Duration
    def __init__(self, target: _Optional[_Union[_coordinate_pb2.Coordinate, _Mapping]] = ..., duration_s: _Optional[_Union[datetime.timedelta, _duration_pb2.Duration, _Mapping]] = ...) -> None: ...

class ActionCommand(_message.Message):
    __slots__ = ()
    ID_FIELD_NUMBER: _ClassVar[int]
    ROBOT_ID_FIELD_NUMBER: _ClassVar[int]
    COMMAND_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    id: str
    robot_id: str
    command: CommandType
    params: CommandParams
    def __init__(self, id: _Optional[str] = ..., robot_id: _Optional[str] = ..., command: _Optional[_Union[CommandType, str]] = ..., params: _Optional[_Union[CommandParams, _Mapping]] = ...) -> None: ...
