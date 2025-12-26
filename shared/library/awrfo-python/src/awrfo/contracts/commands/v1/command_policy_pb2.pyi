from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from typing import ClassVar as _ClassVar

DESCRIPTOR: _descriptor.FileDescriptor

class CommandPolicy(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMMAND_POLICY_BEST_EFFORT: _ClassVar[CommandPolicy]
    COMMAND_POLICY_MUST: _ClassVar[CommandPolicy]
COMMAND_POLICY_BEST_EFFORT: CommandPolicy
COMMAND_POLICY_MUST: CommandPolicy
