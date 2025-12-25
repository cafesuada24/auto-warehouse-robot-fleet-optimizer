from awrfo.contracts.envelopes.event_envelope.v1 import event_envelope_pb2 as _event_envelope_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MapUpdatedPayload(_message.Message):
    __slots__ = ()
    WIDTH_FIELD_NUMBER: _ClassVar[int]
    HEIGHT_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    width: int
    height: int
    data: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, width: _Optional[int] = ..., height: _Optional[int] = ..., data: _Optional[_Iterable[int]] = ...) -> None: ...

class MapUpdatedEvent(_message.Message):
    __slots__ = ()
    ENVELOPE_FIELD_NUMBER: _ClassVar[int]
    PAYLOAD_FIELD_NUMBER: _ClassVar[int]
    envelope: _event_envelope_pb2.EventEnvelope
    payload: MapUpdatedPayload
    def __init__(self, envelope: _Optional[_Union[_event_envelope_pb2.EventEnvelope, _Mapping]] = ..., payload: _Optional[_Union[MapUpdatedPayload, _Mapping]] = ...) -> None: ...
