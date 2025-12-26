from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class CommandType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMMAND_TYPE_UNSPECIFIED: _ClassVar[CommandType]
    COMMAND_TYPE_ASSIGN_TASK: _ClassVar[CommandType]
    COMMAND_TYPE_CANCEL_TASK: _ClassVar[CommandType]
    COMMAND_TYPE_MOVE_TO: _ClassVar[CommandType]
    COMMAND_TYPE_WAIT: _ClassVar[CommandType]
COMMAND_TYPE_UNSPECIFIED: CommandType
COMMAND_TYPE_ASSIGN_TASK: CommandType
COMMAND_TYPE_CANCEL_TASK: CommandType
COMMAND_TYPE_MOVE_TO: CommandType
COMMAND_TYPE_WAIT: CommandType
