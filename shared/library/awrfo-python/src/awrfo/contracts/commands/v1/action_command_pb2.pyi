from buf.validate import validate_pb2 as _validate_pb2
from awrfo.contracts.schemas.common.v1 import coordinate_pb2 as _coordinate_pb2
from awrfo.contracts.commands.v1 import command_type_pb2 as _command_type_pb2
from awrfo.contracts.commands.v1 import command_policy_pb2 as _command_policy_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ActionCommand(_message.Message):
    __slots__ = ()
    ID_FIELD_NUMBER: _ClassVar[int]
    TS_MS_FIELD_NUMBER: _ClassVar[int]
    ROBOT_ID_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    POLICY_FIELD_NUMBER: _ClassVar[int]
    ASSIGN_TASK_FIELD_NUMBER: _ClassVar[int]
    CANCEL_TASK_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_FIELD_NUMBER: _ClassVar[int]
    WAIT_FIELD_NUMBER: _ClassVar[int]
    id: str
    ts_ms: int
    robot_id: str
    type: _command_type_pb2.CommandType
    policy: _command_policy_pb2.CommandPolicy
    assign_task: AssignTask
    cancel_task: CancelTask
    move_to: MoveTo
    wait: Wait
    def __init__(self, id: _Optional[str] = ..., ts_ms: _Optional[int] = ..., robot_id: _Optional[str] = ..., type: _Optional[_Union[_command_type_pb2.CommandType, str]] = ..., policy: _Optional[_Union[_command_policy_pb2.CommandPolicy, str]] = ..., assign_task: _Optional[_Union[AssignTask, _Mapping]] = ..., cancel_task: _Optional[_Union[CancelTask, _Mapping]] = ..., move_to: _Optional[_Union[MoveTo, _Mapping]] = ..., wait: _Optional[_Union[Wait, _Mapping]] = ...) -> None: ...

class AssignTask(_message.Message):
    __slots__ = ()
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class CancelTask(_message.Message):
    __slots__ = ()
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    reason: str
    def __init__(self, task_id: _Optional[str] = ..., reason: _Optional[str] = ...) -> None: ...

class MoveTo(_message.Message):
    __slots__ = ()
    TARGET_FIELD_NUMBER: _ClassVar[int]
    ARRIVE_EPS_FIELD_NUMBER: _ClassVar[int]
    target: _coordinate_pb2.Coordinate
    arrive_eps: float
    def __init__(self, target: _Optional[_Union[_coordinate_pb2.Coordinate, _Mapping]] = ..., arrive_eps: _Optional[float] = ...) -> None: ...

class Wait(_message.Message):
    __slots__ = ()
    DURATION_MS_FIELD_NUMBER: _ClassVar[int]
    duration_ms: int
    def __init__(self, duration_ms: _Optional[int] = ...) -> None: ...
