from dataclasses import dataclass

from pydantic.types import NonNegativeInt

from app.types import IDType


@dataclass(frozen=True)
class Snapshot:
    id: IDType
    timestamp_ms: NonNegativeInt
